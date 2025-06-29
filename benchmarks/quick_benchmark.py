#!/usr/bin/env python3
"""
Quick SynthDB Performance Benchmark

A simplified benchmark to quickly test SynthDB performance at different scales.
Run this to get real performance numbers for the research paper.

Usage:
    python quick_benchmark.py
"""

import time
import random
import statistics
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import synthdb
except ImportError:
    print("Error: Could not import synthdb. Run from project root.")
    sys.exit(1)


def time_operation(func):
    """Decorator to time operations"""
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration = (time.perf_counter() - start) * 1000  # ms
        return result, duration
    return wrapper


@time_operation
def create_database(db_path: str, num_records: int):
    """Create and populate a test database"""
    print(f"Creating database with {num_records:,} records...")
    
    # Remove existing database
    if Path(db_path).exists():
        Path(db_path).unlink()
    
    db = synthdb.connect(db_path)
    db.create_table('users')
    
    # Add columns with proper types
    db.add_columns('users', {
        'name': 'text',
        'email': 'text', 
        'age': 'integer',
        'score': 'real',
        'created_at': 'timestamp'
    })
    
    # Insert data
    for i in range(num_records):
        db.insert('users', {
            'name': f'User {i}',
            'email': f'user{i}@example.com',
            'age': random.randint(18, 80),
            'score': random.uniform(0, 100),
            'created_at': datetime.now()
        })
        
        if i % 1000 == 0 and i > 0:
            print(f"  Inserted {i:,} records...")
    
    return db


@time_operation 
def benchmark_simple_query(db, table_name: str):
    """Benchmark a simple SELECT query"""
    age = random.randint(25, 50)
    return db.query(table_name, f'age > {age}')


@time_operation
def benchmark_complex_query(db):
    """Benchmark a complex aggregation query"""
    return db.execute_sql("""
        SELECT 
            age / 10 * 10 as age_group,
            COUNT(*) as count,
            AVG(score) as avg_score
        FROM users
        GROUP BY age_group
        ORDER BY age_group
    """)


@time_operation
def benchmark_insert(db):
    """Benchmark single insert operation"""
    return db.insert('users', {
        'name': f'New User {random.randint(100000, 999999)}',
        'email': f'newuser{random.randint(100000, 999999)}@example.com',
        'age': random.randint(18, 80),
        'score': random.uniform(0, 100),
        'created_at': datetime.now()
    })


def run_benchmark_suite(size_name: str, num_records: int):
    """Run benchmarks for a specific database size"""
    print(f"\n{'='*50}")
    print(f"Benchmarking {size_name} ({num_records:,} records)")
    print(f"{'='*50}")
    
    db_path = f'benchmark_{size_name}.db'
    
    # Create database
    db, creation_time = create_database(db_path, num_records)
    db_size_mb = Path(db_path).stat().st_size / 1024 / 1024
    
    print(f"Database created in {creation_time/1000:.1f}s")
    print(f"Database size: {db_size_mb:.2f}MB")
    print(f"Records per MB: {num_records/db_size_mb:.0f}")
    
    # Run query benchmarks
    print("\nRunning benchmarks...")
    
    # Simple queries
    simple_times = []
    for _ in range(20):
        _, duration = benchmark_simple_query(db, 'users')
        simple_times.append(duration)
    
    # Complex queries  
    complex_times = []
    for _ in range(10):
        _, duration = benchmark_complex_query(db)
        complex_times.append(duration)
    
    # Insert operations
    insert_times = []
    for _ in range(20):
        _, duration = benchmark_insert(db)
        insert_times.append(duration)
    
    # Calculate statistics
    def get_stats(times):
        sorted_times = sorted(times)
        return {
            'mean': statistics.mean(times),
            'median': statistics.median(times),
            'p95': sorted_times[int(len(sorted_times) * 0.95)],
            'p99': sorted_times[int(len(sorted_times) * 0.99)],
        }
    
    results = {
        'size_name': size_name,
        'num_records': num_records,
        'size_mb': db_size_mb,
        'simple_query': get_stats(simple_times),
        'complex_query': get_stats(complex_times),
        'insert': get_stats(insert_times)
    }
    
    # Print results
    print(f"\nResults for {size_name}:")
    print(f"  Simple Query (ms): mean={results['simple_query']['mean']:.1f}, "
          f"p95={results['simple_query']['p95']:.1f}, "
          f"p99={results['simple_query']['p99']:.1f}")
    print(f"  Complex Query (ms): mean={results['complex_query']['mean']:.1f}, "
          f"p95={results['complex_query']['p95']:.1f}, "
          f"p99={results['complex_query']['p99']:.1f}")
    print(f"  Insert (ms): mean={results['insert']['mean']:.1f}, "
          f"p95={results['insert']['p95']:.1f}, "
          f"p99={results['insert']['p99']:.1f}")
    
    # Cleanup
    Path(db_path).unlink()
    
    return results


def main():
    """Run benchmarks at different scales"""
    print("SynthDB Quick Performance Benchmark")
    print("===================================")
    
    # Define test sizes
    test_sizes = [
        ('tiny', 1_000),      # ~1MB
        ('small', 10_000),    # ~10MB  
        ('medium', 100_000),  # ~100MB
        # ('large', 1_000_000), # ~1GB - uncomment for full test
    ]
    
    all_results = []
    
    for size_name, num_records in test_sizes:
        results = run_benchmark_suite(size_name, num_records)
        all_results.append(results)
    
    # Print summary
    print(f"\n{'='*50}")
    print("SUMMARY - Performance vs Database Size")
    print(f"{'='*50}")
    print(f"{'Size':<10} {'Records':<10} {'DB (MB)':<10} {'Simple Query (ms)':<20} {'Complex Query (ms)':<20}")
    print(f"{'-'*80}")
    
    for r in all_results:
        print(f"{r['size_name']:<10} "
              f"{r['num_records']:<10,} "
              f"{r['size_mb']:<10.1f} "
              f"{r['simple_query']['mean']:<20.1f} "
              f"{r['complex_query']['mean']:<20.1f}")
    
    # Performance scaling analysis
    if len(all_results) > 1:
        print(f"\n{'='*50}")
        print("PERFORMANCE SCALING ANALYSIS")
        print(f"{'='*50}")
        
        base = all_results[0]
        for r in all_results[1:]:
            size_increase = r['num_records'] / base['num_records']
            simple_slowdown = r['simple_query']['mean'] / base['simple_query']['mean']
            complex_slowdown = r['complex_query']['mean'] / base['complex_query']['mean']
            
            print(f"\n{base['size_name']} -> {r['size_name']}:")
            print(f"  Size increase: {size_increase:.0f}x")
            print(f"  Simple query slowdown: {simple_slowdown:.1f}x")
            print(f"  Complex query slowdown: {complex_slowdown:.1f}x")
            
            if simple_slowdown > size_increase:
                print(f"  ⚠️  Simple queries scaling worse than linear!")
            if complex_slowdown > size_increase * 2:
                print(f"  ⚠️  Complex queries scaling poorly!")
    
    print("\n✅ Benchmark complete!")


if __name__ == '__main__':
    main()