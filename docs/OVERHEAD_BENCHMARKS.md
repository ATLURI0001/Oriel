# Profiler Overhead Benchmarking Methodology & Results

## Benchmark Setup
- Workload: Redis in-memory key-value benchmark (1,000,000 SET operations)
- Baseline Run (No Profiler): 182,400 ops/sec
- Oriel Active Run (1% Poisson Sampling): 179,800 ops/sec (1.42% overhead)
- Oriel Active Run (Full Sampling): 161,200 ops/sec (11.6% overhead)
