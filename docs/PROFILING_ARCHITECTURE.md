# Memory Tracing & Allocation Sampling Architecture Guide

## Interception Mechanism
Oriel intercepts `malloc`, `calloc`, `realloc`, and `free` using `LD_PRELOAD` / dynamic linker hooks without recompiling the target application.

## Sampling Strategies
- **Poisson Sampling**: High-frequency short allocations are sampled probabilistically to bound profiling overhead under 1.5%.
- **Large Allocation Trap**: Any single allocation exceeding 1MB is deterministically captured with a full stack trace.
