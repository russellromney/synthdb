#!/usr/bin/env python3
"""
SynthDB Performance Benchmark Suite

This benchmark suite measures the performance characteristics of SynthDB
across different database sizes and workload patterns.

Usage:
    python performance_benchmark.py [--size SIZE] [--workload WORKLOAD]
"""

import time
import random
import statistics
import json
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any
from contextlib import contextmanager
from pathlib import Path
import sys

# Try to import psutil for resource monitoring (optional)
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("Warning: psutil not found. Resource monitoring will be disabled.")
    print("To enable resource monitoring, install psutil: pip install psutil")

# Add parent directory to path to import synthdb
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import synthdb
    from synthdb.bulk import bulk_insert_rows
    from synthdb.local_config import get_local_config
except ImportError:
    print("Error: Could not import synthdb. Make sure it's installed or run from the project root.")
    sys.exit(1)


class PerformanceMonitor:
    """Monitor system resources during benchmark execution"""
    
    def __init__(self):
        self.start_time = time.time()
        if HAS_PSUTIL:
            self.process = psutil.Process()
            self.start_cpu = self.process.cpu_percent()
            self.start_memory = self.process.memory_info().rss
        else:
            self.process = None
            self.start_cpu = 0
            self.start_memory = 0
        
    def get_current_stats(self) -> Dict[str, float]:
        """Get current resource usage statistics"""
        stats = {
            'elapsed_seconds': time.time() - self.start_time
        }
        
        if HAS_PSUTIL and self.process:
            stats.update({
                'cpu_percent': self.process.cpu_percent(),
                'memory_mb': self.process.memory_info().rss / 1024 / 1024
            })
        else:
            stats.update({
                'cpu_percent': -1,  # Indicate not available
                'memory_mb': -1
            })
        
        return stats


class BenchmarkTimer:
    """High-precision timer for benchmark operations"""
    
    def __init__(self):
        self.times: List[float] = []
        
    @contextmanager
    def time_operation(self):
        """Context manager to time an operation"""
        start = time.perf_counter()
        yield
        duration = (time.perf_counter() - start) * 1000  # Convert to milliseconds
        self.times.append(duration)
    
    def get_statistics(self) -> Dict[str, float]:
        """Calculate timing statistics"""
        if not self.times:
            return {}
            
        sorted_times = sorted(self.times)
        return {
            'count': len(self.times),
            'mean_ms': statistics.mean(self.times),
            'median_ms': statistics.median(self.times),
            'min_ms': min(self.times),
            'max_ms': max(self.times),
            'p95_ms': sorted_times[int(len(sorted_times) * 0.95)],
            'p99_ms': sorted_times[int(len(sorted_times) * 0.99)],
            'stddev_ms': statistics.stdev(self.times) if len(self.times) > 1 else 0
        }


class DataGenerator:
    """Generate test data for benchmarks"""
    
    def __init__(self, seed: int = 42):
        random.seed(seed)
        self.words = [
            'lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consectetur',
            'adipiscing', 'elit', 'sed', 'do', 'eiusmod', 'tempor'
        ]
        
    def generate_text(self, min_length: int = 10, max_length: int = 100) -> str:
        """Generate random text of specified length"""
        num_words = random.randint(min_length // 5, max_length // 5)
        return ' '.join(random.choices(self.words, k=num_words))
    
    def generate_user_data(self, user_id: int) -> Dict[str, Any]:
        """Generate a single user record"""
        return {
            'user_id': f'user_{user_id}',
            'name': f'User {user_id}',
            'email': f'user{user_id}@example.com',
            'age': random.randint(18, 80),
            'city': random.choice(['New York', 'London', 'Tokyo', 'Paris', 'Sydney']),
            'bio': self.generate_text(20, 100),
            'created_at': datetime.now() - timedelta(days=random.randint(0, 365))
        }
    
    def generate_order_data(self, order_id: int, num_users: int) -> Dict[str, Any]:
        """Generate a single order record"""
        return {
            'order_id': f'order_{order_id}',
            'user_id': f'user_{random.randint(1, num_users)}',
            'total': round(random.uniform(10.0, 1000.0), 2),
            'status': random.choice(['pending', 'completed', 'cancelled']),
            'items': random.randint(1, 10),
            'notes': self.generate_text(10, 50),
            'created_at': datetime.now() - timedelta(hours=random.randint(0, 720))
        }
    
    def generate_event_data(self, event_id: int) -> Dict[str, Any]:
        """Generate a single event record for time-series testing"""
        return {
            'event_id': f'event_{event_id}',
            'event_type': random.choice(['click', 'view', 'purchase', 'signup']),
            'user_id': f'user_{random.randint(1, 10000)}',
            'value': random.uniform(0, 100),
            'metadata': json.dumps({'source': random.choice(['web', 'mobile', 'api'])}),
            'timestamp': datetime.now() - timedelta(seconds=random.randint(0, 86400))
        }


class SynthDBBenchmark:
    """Main benchmark suite for SynthDB"""
    
    def __init__(self, branch_name: str = 'benchmark'):
        self.branch_name = branch_name
        self.db = None
        self.db_path = None
        self.generator = DataGenerator()
        self.results = {}
        self.local_config = None
        self.original_branch = None
        
    def setup(self, size_mb: int):
        """Setup database with test data"""
        print(f"\nSetting up {size_mb}MB database on branch '{self.branch_name}'...")
        
        # Get local config and current branch
        self.local_config = get_local_config()
        
        # Initialize .synthdb if it doesn't exist
        if not self.local_config.synthdb_dir:
            print("Initializing .synthdb directory...")
            self.local_config.init_synthdb_dir()
        
        # Store original branch to restore later
        self.original_branch = self.local_config.get_active_branch()
        
        # Create benchmark branch if it doesn't exist
        branches = self.local_config.list_branches()
        if self.branch_name in branches:
            # Remove existing benchmark branch database
            db_path = self.local_config.get_database_path(self.branch_name)
            if db_path and Path(db_path).exists():
                Path(db_path).unlink()
        
        # Create fresh benchmark branch from main
        print(f"Creating branch '{self.branch_name}' from '{self.original_branch}'...")
        self.db_path = self.local_config.create_branch(self.branch_name, from_branch=None)  # Start fresh
        
        # Switch to benchmark branch
        self.local_config.set_active_branch(self.branch_name)
            
        # Connect to database on the benchmark branch
        self.db = synthdb.connect(self.db_path)
        
        # Create tables
        self.db.create_table('users')
        self.db.create_table('orders') 
        self.db.create_table('events')
        
        # Define schemas for each table
        self.db.add_columns('users', {
            'user_id': 'text',
            'name': 'text',
            'email': 'text',
            'age': 'integer',
            'city': 'text',
            'bio': 'text',
            'created_at': 'timestamp'
        })
        
        self.db.add_columns('orders', {
            'order_id': 'text',
            'user_id': 'text',
            'total': 'real',
            'status': 'text',
            'items': 'integer',
            'notes': 'text',
            'created_at': 'timestamp'
        })
        
        self.db.add_columns('events', {
            'event_id': 'text',
            'event_type': 'text',
            'user_id': 'text',
            'value': 'real',
            'metadata': 'text',
            'timestamp': 'timestamp'
        })
        
        # Calculate number of records based on target size
        # Rough estimate: 1KB per user record, 0.5KB per order, 0.3KB per event
        num_users = int(size_mb * 1024 * 0.3)  # 30% of space for users
        num_orders = int(size_mb * 1024 * 0.5)  # 50% of space for orders
        num_events = int(size_mb * 1024 * 0.7)  # 70% of space for events
        
        print(f"Creating {num_users} users, {num_orders} orders, {num_events} events...")
        
        # Insert users using bulk insert
        timer = BenchmarkTimer()
        batch_size = 5000
        with timer.time_operation():
            # Generate all user data
            print("  Generating user data...")
            users_data = []
            for i in range(1, num_users + 1):
                users_data.append(self.generator.generate_user_data(i))
                if i % 10000 == 0:
                    print(f"    Generated {i} users...")
            
            # Bulk insert in batches
            print("  Bulk inserting users...")
            for i in range(0, len(users_data), batch_size):
                batch = users_data[i:i + batch_size]
                stats = bulk_insert_rows('users', batch, self.db_path, self.db.backend_name)
                if (i + batch_size) % 5000 == 0:
                    print(f"    Inserted {min(i + batch_size, len(users_data))} users...")
                    
        self.results['setup_users'] = timer.get_statistics()
        
        # Insert orders using bulk insert
        timer = BenchmarkTimer()
        with timer.time_operation():
            # Generate all order data
            print("  Generating order data...")
            orders_data = []
            for i in range(1, num_orders + 1):
                orders_data.append(self.generator.generate_order_data(i, num_users))
                if i % 10000 == 0:
                    print(f"    Generated {i} orders...")
            
            # Bulk insert in batches
            print("  Bulk inserting orders...")
            for i in range(0, len(orders_data), batch_size):
                batch = orders_data[i:i + batch_size]
                stats = bulk_insert_rows('orders', batch, self.db_path, self.db.backend_name)
                if (i + batch_size) % 5000 == 0:
                    print(f"    Inserted {min(i + batch_size, len(orders_data))} orders...")
                    
        self.results['setup_orders'] = timer.get_statistics()
        
        # Insert events using bulk insert
        timer = BenchmarkTimer()
        with timer.time_operation():
            # Generate all event data
            print("  Generating event data...")
            events_data = []
            for i in range(1, num_events + 1):
                events_data.append(self.generator.generate_event_data(i))
                if i % 10000 == 0:
                    print(f"    Generated {i} events...")
            
            # Bulk insert in batches
            print("  Bulk inserting events...")
            for i in range(0, len(events_data), batch_size):
                batch = events_data[i:i + batch_size]
                stats = bulk_insert_rows('events', batch, self.db_path, self.db.backend_name)
                if (i + batch_size) % 5000 == 0:
                    print(f"    Inserted {min(i + batch_size, len(events_data))} events...")
                    
        self.results['setup_events'] = timer.get_statistics()
        
        # Get actual database size
        actual_size = Path(self.db_path).stat().st_size / 1024 / 1024
        print(f"Database setup complete. Actual size: {actual_size:.2f}MB")
        
        self.results['database_info'] = {
            'branch': self.branch_name,
            'target_size_mb': size_mb,
            'actual_size_mb': actual_size,
            'num_users': num_users,
            'num_orders': num_orders,
            'num_events': num_events,
            'db_path': self.db_path
        }
    
    def benchmark_simple_queries(self):
        """Benchmark simple SELECT queries"""
        print("\nRunning simple query benchmarks...")
        
        # Point query by ID
        timer = BenchmarkTimer()
        for _ in range(100):
            user_id = f"user_{random.randint(1, self.results['database_info']['num_users'])}"
            with timer.time_operation():
                self.db.query('users', f"user_id = '{user_id}'")
        self.results['point_query'] = timer.get_statistics()
        
        # Range query
        timer = BenchmarkTimer()
        for _ in range(50):
            min_age = random.randint(20, 40)
            max_age = min_age + random.randint(10, 30)
            with timer.time_operation():
                self.db.query('users', f"age BETWEEN {min_age} AND {max_age}")
        self.results['range_query'] = timer.get_statistics()
        
        # Text search
        timer = BenchmarkTimer()
        cities = ['New York', 'London', 'Tokyo', 'Paris', 'Sydney']
        for _ in range(50):
            city = random.choice(cities)
            with timer.time_operation():
                self.db.query('users', f"city = '{city}'")
        self.results['text_search'] = timer.get_statistics()
        
    def benchmark_complex_queries(self):
        """Benchmark complex queries with JOINs and aggregations"""
        print("\nRunning complex query benchmarks...")
        
        # JOIN query
        timer = BenchmarkTimer()
        for _ in range(20):
            with timer.time_operation():
                self.db.execute_sql("""
                    SELECT u.name, COUNT(o.order_id) as order_count
                    FROM users u
                    LEFT JOIN orders o ON u.user_id = o.user_id
                    GROUP BY u.user_id
                    LIMIT 100
                """)
        self.results['join_query'] = timer.get_statistics()
        
        # Aggregation query
        timer = BenchmarkTimer()
        for _ in range(20):
            with timer.time_operation():
                self.db.execute_sql("""
                    SELECT 
                        status,
                        COUNT(*) as count,
                        AVG(total) as avg_total,
                        SUM(total) as sum_total
                    FROM orders
                    GROUP BY status
                """)
        self.results['aggregation_query'] = timer.get_statistics()
        
        # Time-series query
        timer = BenchmarkTimer()
        for _ in range(20):
            with timer.time_operation():
                self.db.execute_sql("""
                    SELECT 
                        DATE(timestamp) as day,
                        event_type,
                        COUNT(*) as event_count
                    FROM events
                    WHERE timestamp > datetime('now', '-7 days')
                    GROUP BY day, event_type
                    ORDER BY day DESC
                """)
        self.results['time_series_query'] = timer.get_statistics()
        
    def benchmark_write_operations(self):
        """Benchmark INSERT, UPDATE, and DELETE operations"""
        print("\nRunning write operation benchmarks...")
        
        # Single INSERT
        timer = BenchmarkTimer()
        for i in range(100):
            user_data = self.generator.generate_user_data(9999000 + i)
            with timer.time_operation():
                self.db.insert('users', user_data)
        self.results['single_insert'] = timer.get_statistics()
        
        # Bulk INSERT
        timer = BenchmarkTimer()
        bulk_data = []
        for i in range(1000):
            bulk_data.append(self.generator.generate_order_data(
                9999000 + i, 
                self.results['database_info']['num_users']
            ))
        
        with timer.time_operation():
            stats = bulk_insert_rows('orders', bulk_data, self.db_path, self.db.backend_name)
        
        bulk_stats = timer.get_statistics()
        bulk_stats['operations_per_second'] = 1000 / (bulk_stats['mean_ms'] / 1000)
        bulk_stats['rows_inserted'] = stats['inserted']
        bulk_stats['errors'] = stats['errors']
        self.results['bulk_insert'] = bulk_stats
        
        # UPDATE operations
        timer = BenchmarkTimer()
        for _ in range(50):
            # Use the row ID (1-100) for updates
            row_id = str(random.randint(1, min(100, self.results['database_info']['num_users'])))
            new_age = random.randint(18, 80)
            with timer.time_operation():
                # SynthDB uses upsert for updates - requires id parameter
                self.db.upsert('users', {
                    'age': new_age,
                    'updated_at': datetime.now()
                }, id=row_id)
        self.results['update_operation'] = timer.get_statistics()
        
    def benchmark_schema_operations(self):
        """Benchmark schema evolution operations"""
        print("\nRunning schema operation benchmarks...")
        
        # Add column
        timer = BenchmarkTimer()
        with timer.time_operation():
            self.db.add_columns('users', {'loyalty_points': 'integer'})
        self.results['add_column'] = timer.get_statistics()
        
        # Query with new column
        timer = BenchmarkTimer()
        for _ in range(50):
            with timer.time_operation():
                self.db.query('users', 'loyalty_points >= 0')
        self.results['query_new_column'] = timer.get_statistics()
        
    def benchmark_concurrent_operations(self):
        """Benchmark concurrent read/write operations"""
        print("\nRunning concurrency benchmarks...")
        
        import threading
        import queue
        
        results_queue = queue.Queue()
        
        def concurrent_reads(num_operations):
            timer = BenchmarkTimer()
            for _ in range(num_operations):
                user_id = f"user_{random.randint(1, 100)}"
                with timer.time_operation():
                    self.db.query('users', f"user_id = '{user_id}'")
            results_queue.put(('read', timer.get_statistics()))
        
        def concurrent_writes(num_operations):
            timer = BenchmarkTimer()
            for i in range(num_operations):
                event_data = self.generator.generate_event_data(8888000 + i)
                with timer.time_operation():
                    self.db.insert('events', event_data)
            results_queue.put(('write', timer.get_statistics()))
        
        # Run concurrent operations
        threads = []
        for _ in range(3):  # 3 read threads
            t = threading.Thread(target=concurrent_reads, args=(30,))
            threads.append(t)
            t.start()
            
        for _ in range(2):  # 2 write threads  
            t = threading.Thread(target=concurrent_writes, args=(20,))
            threads.append(t)
            t.start()
            
        # Wait for completion
        for t in threads:
            t.join()
            
        # Collect results
        concurrent_results = {'reads': [], 'writes': []}
        while not results_queue.empty():
            op_type, stats = results_queue.get()
            if op_type == 'read':
                concurrent_results['reads'].append(stats)
            else:
                concurrent_results['writes'].append(stats)
                
        self.results['concurrent_operations'] = concurrent_results
        
    def run_all_benchmarks(self, size_mb: int):
        """Run complete benchmark suite"""
        monitor = PerformanceMonitor()
        
        # Setup database
        self.setup(size_mb)
        
        # Run benchmarks
        self.benchmark_simple_queries()
        self.benchmark_complex_queries()
        self.benchmark_write_operations()
        self.benchmark_schema_operations()
        self.benchmark_concurrent_operations()
        
        # Collect final resource usage
        self.results['resource_usage'] = monitor.get_current_stats()
        
        # Cleanup
        self.cleanup()
    
    def cleanup(self):
        """Clean up after benchmarking"""
        if self.db:
            # Close connection if possible
            if hasattr(self.db, 'close'):
                self.db.close()
            self.db = None
        
        # Restore original branch
        if self.local_config and self.original_branch:
            print(f"\nRestoring original branch '{self.original_branch}'...")
            self.local_config.set_active_branch(self.original_branch)
            
    def generate_report(self) -> str:
        """Generate a formatted report of benchmark results"""
        report = []
        report.append("=" * 60)
        report.append("SynthDB Performance Benchmark Report")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Database info
        if 'database_info' in self.results:
            info = self.results['database_info']
            report.append("Database Information:")
            report.append(f"  Branch: {info['branch']}")
            report.append(f"  Target Size: {info['target_size_mb']}MB")
            report.append(f"  Actual Size: {info['actual_size_mb']:.2f}MB")
            report.append(f"  Users: {info['num_users']:,}")
            report.append(f"  Orders: {info['num_orders']:,}")
            report.append(f"  Events: {info['num_events']:,}")
            report.append("")
        
        # Query benchmarks
        report.append("Query Performance:")
        for query_type in ['point_query', 'range_query', 'text_search', 
                          'join_query', 'aggregation_query', 'time_series_query']:
            if query_type in self.results:
                stats = self.results[query_type]
                report.append(f"  {query_type.replace('_', ' ').title()}:")
                report.append(f"    Mean: {stats['mean_ms']:.2f}ms")
                report.append(f"    P95: {stats['p95_ms']:.2f}ms")
                report.append(f"    P99: {stats['p99_ms']:.2f}ms")
                report.append("")
        
        # Write benchmarks
        report.append("Write Performance:")
        for write_type in ['single_insert', 'bulk_insert', 'update_operation']:
            if write_type in self.results:
                stats = self.results[write_type]
                report.append(f"  {write_type.replace('_', ' ').title()}:")
                report.append(f"    Mean: {stats['mean_ms']:.2f}ms")
                if 'operations_per_second' in stats:
                    report.append(f"    Throughput: {stats['operations_per_second']:.0f} ops/sec")
                report.append("")
        
        # Schema operations
        if 'add_column' in self.results:
            report.append("Schema Operations:")
            report.append(f"  Add Column: {self.results['add_column']['mean_ms']:.2f}ms")
            report.append("")
        
        # Resource usage
        if 'resource_usage' in self.results:
            usage = self.results['resource_usage']
            report.append("Resource Usage:")
            report.append(f"  CPU: {usage['cpu_percent']:.1f}%")
            report.append(f"  Memory: {usage['memory_mb']:.1f}MB")
            report.append(f"  Total Time: {usage['elapsed_seconds']:.1f}s")
            report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def save_results(self, filename: str):
        """Save detailed results to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"Detailed results saved to {filename}")


def main():
    """Main entry point for benchmark script"""
    parser = argparse.ArgumentParser(
        description='SynthDB Performance Benchmark Suite'
    )
    parser.add_argument(
        '--size', 
        type=int, 
        default=10,
        help='Target database size in MB (default: 10)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='benchmark_results.json',
        help='Output file for detailed results (default: benchmark_results.json)'
    )
    parser.add_argument(
        '--branch',
        type=str,
        default='benchmark',
        help='Branch name for benchmark (default: benchmark)'
    )
    
    args = parser.parse_args()
    
    print(f"Starting SynthDB Performance Benchmark")
    print(f"Target database size: {args.size}MB")
    print(f"Branch: {args.branch}")
    print("")
    
    # Run benchmarks
    benchmark = SynthDBBenchmark(args.branch)
    
    try:
        benchmark.run_all_benchmarks(args.size)
        
        # Generate and print report
        report = benchmark.generate_report()
        print("\n" + report)
        
        # Save detailed results
        benchmark.save_results(args.output)
        
    except Exception as e:
        print(f"\nError during benchmark: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())