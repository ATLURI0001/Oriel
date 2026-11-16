# Low-Overhead Stack Unwinding & Symbol Resolution

## Unwinding Modes
1. **Frame Pointer Unwinding (Fast)**: Traverses `rbp` chains in < 25 nanoseconds per frame.
2. **DWARF .eh_frame Unwinding (Complete)**: Handles optimized `-fomit-frame-pointer` binaries via binary search over .eh_frame tables.

## Symbol Caching
Decoded function symbols and source file locations are cached in a lock-free hash table to prevent redundant DWARF lookup penalties.
