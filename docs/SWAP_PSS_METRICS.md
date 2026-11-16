# Swap-PSS & Proportional Set Size (PSS) Metrics Specification

## Memory Metrics Definitions
- **RSS (Resident Set Size)**: Total memory mapped in RAM, including shared libraries.
- **PSS (Proportional Set Size)**: Private memory plus shared library memory divided by sharing process count.
- **Swap-PSS**: Proportional swapped memory allocated to disk, diagnosing thrashing conditions.

## Extraction Protocol
Oriel periodically reads `/proc/[pid]/smaps_rollup` in a single non-blocking syscall.
