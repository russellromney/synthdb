# SynthDB Performance Benchmarks

This directory contains performance benchmarking tools for SynthDB to measure how the database scales under different workloads and data sizes.

## Quick Start

Run the quick benchmark to get immediate performance insights:

```bash
cd synthdb
python benchmarks/quick_benchmark.py
```

This will test SynthDB performance at different scales and show how performance degrades as the database grows.

## Benchmark Scripts

### quick_benchmark.py
A simplified benchmark that runs in ~1 minute and tests:
- Database creation and population
- Simple queries (WHERE clauses)
- Complex queries (GROUP BY, aggregations)
- Insert performance
- Performance scaling from 1K to 100K records

**Usage:**
```bash
python benchmarks/quick_benchmark.py
```

### performance_benchmark.py
Comprehensive benchmark suite that tests:
- Multiple workload patterns (OLTP, analytical, write-heavy)
- Concurrent operations
- Schema evolution performance
- Resource utilization
- Detailed performance statistics (p50, p95, p99)

**Usage:**
```bash
# Run with default 10MB database
python benchmarks/performance_benchmark.py

# Run with 100MB database
python benchmarks/performance_benchmark.py --size 100

# Save detailed results
python benchmarks/performance_benchmark.py --output results.json
```

## Understanding Results

### Key Metrics

1. **Query Latency**
   - Mean: Average query time
   - P95: 95% of queries complete within this time
   - P99: 99% of queries complete within this time

2. **Throughput**
   - Operations per second for bulk operations
   - Useful for understanding write capacity

3. **Scaling Factor**
   - How performance degrades as database grows
   - Linear scaling (1x) is ideal
   - Super-linear scaling indicates architectural issues

### Expected Performance

Based on SynthDB's architecture:

**Good Performance (< 100MB)**
- Simple queries: < 10ms
- Complex queries: < 100ms
- Inserts: < 5ms

**Degraded Performance (> 1GB)**
- Simple queries: 100-500ms
- Complex queries: 1-10 seconds
- Inserts: 10-50ms

## Running Real Benchmarks

To validate the theoretical analysis in the research papers:

1. **Start Small**: Run quick_benchmark.py first
2. **Scale Up**: Use performance_benchmark.py with increasing sizes
3. **Monitor Resources**: Watch CPU and memory usage
4. **Compare Results**: Check against theoretical projections

## Interpreting Results

### Warning Signs
- ⚠️ Super-linear scaling (performance degrades faster than data growth)
- ⚠️ High P99 latencies (indicates unpredictable performance)
- ⚠️ Memory usage growing faster than database size

### Optimization Opportunities
Based on benchmark results, consider:
- Adding indexes for frequently queried columns
- Implementing query result caching
- Using materialized views for complex queries
- Partitioning large tables

## Contributing

When adding new benchmarks:
1. Follow the existing pattern of time measurement
2. Include warmup runs to avoid cold-start effects
3. Run multiple iterations for statistical significance
4. Document what the benchmark measures and why

## Future Benchmarks

Planned additions:
- Vector similarity search performance
- Branching and merging overhead
- Transaction isolation impact
- Network latency effects (for remote databases)
- Saved query performance