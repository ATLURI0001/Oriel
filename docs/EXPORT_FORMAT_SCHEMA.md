# Flame Graph JSON Schema & Trace Event Export Specification

## Supported Formats
1. **Folded Stack Format**: Standard Brendan Gregg folded stack format for SVG flame graph rendering.
2. **Chrome Trace Event (Speedscope)**: Hierarchical profile export consumable by Speedscope and Perfetto.

## JSON Trace Schema
```json
{
  "name": "malloc",
  "ph": "X",
  "ts": 1672531199000,
  "dur": 42,
  "pid": 1204,
  "tid": 1204,
  "args": {
    "bytes": 4096,
    "symbol": "std::vector<int>::push_back"
  }
}
```
