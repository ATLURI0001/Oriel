"""
Usage examples:
  # Basic usage - show aggregated cache percentages for all vector index files
  python smaps-view.py $(pidof qdrant) '.*/vector_index/.*'

  # Verbose mode - show individual files larger than 1MB
  python smaps-view.py $(pidof qdrant) '.*/vector_storage/.*' -v

Example output:
    Cache percentages for pattern '.vector_storage.*':
    r--s: 0.00%
    rw-s: 0.06%
"""

import re
import sys
import argparse
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass


# Example of smap format:
#
#
# 7de883800000-7de885800000 r--s 00000000 00:33 26610006                   /qdrant/storage/collections/benchmark/0/segments/6250c760-ccaf-468e-a96f-8e2b03f8c524/vector_storage/vectors/chunk_2.mmap
# Size:              32768 kB
# KernelPageSize:        4 kB
# MMUPageSize:           4 kB
# Rss:                   0 kB
# Pss:                   0 kB
# Pss_Dirty:             0 kB
# Shared_Clean:          0 kB
# Shared_Dirty:          0 kB
# Private_Clean:         0 kB
# Private_Dirty:         0 kB
# Referenced:            0 kB
# Anonymous:             0 kB
# KSM:                   0 kB
# LazyFree:              0 kB
# AnonHugePages:         0 kB
# ShmemPmdMapped:        0 kB
# FilePmdMapped:         0 kB
# Shared_Hugetlb:        0 kB
# Private_Hugetlb:       0 kB
# Swap:                  0 kB
# SwapPss:               0 kB
# Locked:                0 kB
# THPeligible:           0
# ProtectionKey:         0
# VmFlags: rd sh mr mw me ms sr sd 
#


@dataclass
class MapStats:
    size: int = 0
    rss: int = 0
    pss: int = 0
    shared_clean: int = 0
    shared_dirty: int = 0
    private_clean: int = 0
    private_dirty: int = 0
    swap: int = 0
    swap_pss: int = 0
    anonymous: int = 0
    anon_huge_pages: int = 0

    @property
    def shared(self) -> int:
        return self.shared_clean + self.shared_dirty

    @property
    def private(self) -> int:
        return self.private_clean + self.private_dirty

def _flush_entry(
    file_stats: Dict[Tuple[str, str], MapStats],
    regex: re.Pattern,
    current_file: Optional[str],
    current_permissions: str,
    current_size: int,
    current_rss: int,
    current_pss: int,
    current_sc: int,
    current_sd: int,
    current_pc: int,
    current_pd: int,
    current_swap: int,
    current_swap_pss: int,
    current_anon: int,
    current_ahp: int,
    verbose: bool,
) -> None:
    if not (current_file and regex.search(current_file)):
        return
    key = (current_file, current_permissions)
    if key not in file_stats:
        file_stats[key] = MapStats()

    stats = file_stats[key]
    stats.size += current_size
    stats.rss += current_rss
    stats.pss += current_pss
    stats.shared_clean += current_sc
    stats.shared_dirty += current_sd
    stats.private_clean += current_pc
    stats.private_dirty += current_pd
    stats.swap += current_swap
    stats.swap_pss += current_swap_pss
    stats.anonymous += current_anon
    stats.anon_huge_pages += current_ahp

    # Log individual file percentage if verbose mode is enabled and file is larger than 1MB
    if verbose and current_size > 1024:
        percentage = (current_rss / current_size) * 100 if current_size > 0 else 0.0
        pss_pct = (current_pss / current_size) * 100 if current_size > 0 else 0.0
        print(f"File: {current_file} ({current_permissions})")
        print(f"  Size: {current_size} kB")
        print(f"  RSS: {current_rss} kB")
        print(f"  PSS: {current_pss} kB")
        print(f"  Cache percentage: {percentage:.2f}% (PSS: {pss_pct:.2f}%)")
        print()


def parse_smaps(smaps_content: str, pattern: str = ".*", verbose: bool = False) -> Dict[Tuple[str, str], MapStats]:
    """
    Parse smaps content and calculate size and RSS for files matching the pattern.
    Optionally logs individual file percentages for files larger than 1MB.
    
    Args:
        smaps_content: Content of /proc/{pid}/smaps file
        pattern: Regular expression pattern to match against file paths
        verbose: Whether to print per-file information
        
    Returns:
        Dictionary mapping (file_path, permissions) tuples to their stats
    """
    file_stats: Dict[Tuple[str, str], MapStats] = {}
    current_file = None
    current_size = 0
    current_rss = 0
    current_pss = 0
    current_sc = 0
    current_sd = 0
    current_pc = 0
    current_pd = 0
    current_swap = 0
    current_swap_pss = 0
    current_anon = 0
    current_ahp = 0
    current_permissions = ""
    
    # Compile the regex pattern safely
    pat = pattern if pattern is not None and pattern != "" else ".*"
    try:
        regex = re.compile(pat)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern '{pat}': {e}") from e
    
    for line in smaps_content.splitlines():
        # Check if line starts with an address range (new memory map entry)
        if re.match(r'^[0-9a-f]+-[0-9a-f]+', line):
            _flush_entry(
                file_stats,
                regex,
                current_file,
                current_permissions,
                current_size,
                current_rss,
                current_pss,
                current_sc,
                current_sd,
                current_pc,
                current_pd,
                current_swap,
                current_swap_pss,
                current_anon,
                current_ahp,
                verbose,
            )
            
            # Preserve spaces in mapped paths (e.g. '/data/my index/chunk_1.mmap')
            parts = line.split(None, 5)
            current_file = parts[5].strip() if len(parts) > 5 else None
            current_size = 0
            current_rss = 0
            current_pss = 0
            current_sc = 0
            current_sd = 0
            current_pc = 0
            current_pd = 0
            current_swap = 0
            current_swap_pss = 0
            current_anon = 0
            current_ahp = 0
            # Store full permissions string
            current_permissions = parts[1] if len(parts) > 1 else ""
        elif line.startswith('Size:'):
            parts = line.split()
            if len(parts) > 1:
                try:
                    current_size = max(0, int(parts[1]))
                except ValueError:
                    current_size = 0
        elif line.startswith('Rss:'):
            parts = line.split()
            if len(parts) > 1:
                try:
                    current_rss = max(0, int(parts[1]))
                except ValueError:
                    current_rss = 0
        elif line.startswith('Pss:'):
            parts = line.split()
            if len(parts) > 1:
                try:
                    current_pss = max(0, int(parts[1]))
                except ValueError:
                    current_pss = 0
        elif line.startswith('Shared_Clean:'):
            parts = line.split()
            if len(parts) > 1:
                try:
                    current_sc = max(0, int(parts[1]))
                except ValueError:
                    current_sc = 0
        elif line.startswith('Shared_Dirty:'):
            parts = line.split()
            if len(parts) > 1:
                try:
                    current_sd = max(0, int(parts[1]))
                except ValueError:
                    current_sd = 0
        elif line.startswith('Private_Clean:'):
            parts = line.split()
            if len(parts) > 1:
                try:
                    current_pc = max(0, int(parts[1]))
                except ValueError:
                    current_pc = 0
        elif line.startswith('Private_Dirty:'):
            parts = line.split()
            if len(parts) > 1:
                try:
                    current_pd = max(0, int(parts[1]))
                except ValueError:
                    current_pd = 0
        elif line.startswith('Swap:'):
            parts = line.split()
            if len(parts) > 1:
                try:
                    current_swap = max(0, int(parts[1]))
                except ValueError:
                    current_swap = 0
        elif line.startswith('SwapPss:'):
            parts = line.split()
            if len(parts) > 1:
                try:
                    current_swap_pss = max(0, int(parts[1]))
                except ValueError:
                    current_swap_pss = 0
        elif line.startswith('Anonymous:'):
            parts = line.split()
            if len(parts) > 1:
                try:
                    current_anon = max(0, int(parts[1]))
                except ValueError:
                    current_anon = 0
        elif line.startswith('AnonHugePages:'):
            parts = line.split()
            if len(parts) > 1:
                try:
                    current_ahp = max(0, int(parts[1]))
                except ValueError:
                    current_ahp = 0
    
    _flush_entry(
        file_stats,
        regex,
        current_file,
        current_permissions,
        current_size,
        current_rss,
        current_pss,
        current_sc,
        current_sd,
        current_pc,
        current_pd,
        current_swap,
        current_swap_pss,
        current_anon,
        current_ahp,
        verbose,
    )
    
    return file_stats

def calculate_cache_percentage(pid: int, pattern: str, verbose: bool = False, smaps_content: Optional[str] = None) -> Dict[str, float]:
    """
    Calculate the percentage of memory that is cached for files matching the pattern.
    Separates by permission type.
    
    Args:
        pid: Process ID to analyze (> 0)
        pattern: Regular expression pattern to match against file paths
        verbose: Whether to print per-file information
        smaps_content: Optional pre-loaded smaps string (for testing or remote extraction)
        
    Returns:
        Dictionary mapping permission strings to their cache percentages
    """
    if pid <= 0 and smaps_content is None:
        print(f"Error: Invalid PID {pid}. PID must be a positive integer.", file=sys.stderr)
        return {}

    try:
        if smaps_content is None:
            smaps_path = f'/proc/{pid}/smaps'
            with open(smaps_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        else:
            content = smaps_content
        
        file_stats = parse_smaps(content, pattern, verbose)
        
        if not file_stats:
            return {}
            
        # Calculate percentages for each permission type
        permission_stats: Dict[str, Tuple[int, int]] = {}
        for (_, perms), stats in file_stats.items():
            if perms not in permission_stats:
                permission_stats[perms] = (0, 0)
            size, rss = permission_stats[perms]
            permission_stats[perms] = (size + stats.size, rss + stats.rss)
        
        # Calculate percentages
        percentages = {}
        for perms, (size, rss) in permission_stats.items():
            if size > 0:
                percentages[perms] = (rss / size) * 100
            else:
                percentages[perms] = 0.0
        
        return percentages
    except FileNotFoundError:
        print(f"Error: Could not find /proc/{pid}/smaps (Linux procfs required)", file=sys.stderr)
        return {}
    except PermissionError:
        print(f"Error: Permission denied reading /proc/{pid}/smaps", file=sys.stderr)
        return {}
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return {}
    except OSError as e:
        print(f"Error reading /proc/{pid}/smaps: {e}", file=sys.stderr)
        return {}


def summarize_smaps(pid: int, pattern: str = ".*", verbose: bool = False, smaps_content: Optional[str] = None) -> Dict[str, dict]:
    """
    Summarize memory maps by permission, aggregating size, RSS, PSS, and cache percentages.
    """
    if pid <= 0 and smaps_content is None:
        return {}

    try:
        if smaps_content is None:
            smaps_path = f'/proc/{pid}/smaps'
            with open(smaps_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        else:
            content = smaps_content

        file_stats = parse_smaps(content, pattern, verbose)
        if not file_stats:
            return {}

        agg: Dict[str, Dict[str, int]] = {}
        for (_, perms), stats in file_stats.items():
            if perms not in agg:
                agg[perms] = {
                    "size": 0, "rss": 0, "pss": 0, "shared": 0, "private": 0,
                    "swap": 0, "swap_pss": 0, "anonymous": 0, "anon_huge_pages": 0,
                }
            agg[perms]["size"] += stats.size
            agg[perms]["rss"] += stats.rss
            agg[perms]["pss"] += stats.pss
            agg[perms]["shared"] += stats.shared
            agg[perms]["private"] += stats.private
            agg[perms]["swap"] += stats.swap
            agg[perms]["swap_pss"] += stats.swap_pss
            agg[perms]["anonymous"] += stats.anonymous
            agg[perms]["anon_huge_pages"] += stats.anon_huge_pages

        summary = {}
        for perms, totals in agg.items():
            sz = totals["size"]
            rss = totals["rss"]
            pss = totals["pss"]
            shared = totals["shared"]
            private = totals["private"]
            swap = totals["swap"]
            swap_pss = totals["swap_pss"]
            anon = totals["anonymous"]
            ahp = totals["anon_huge_pages"]
            summary[perms] = {
                "size_kb": sz,
                "rss_kb": rss,
                "pss_kb": pss,
                "shared_kb": shared,
                "private_kb": private,
                "swap_kb": swap,
                "swap_pss_kb": swap_pss,
                "anonymous_kb": anon,
                "anon_huge_pages_kb": ahp,
                "cache_pct": (rss / sz * 100.0) if sz > 0 else 0.0,
                "pss_pct": (pss / sz * 100.0) if sz > 0 else 0.0,
            }
        return summary
    except Exception:
        return {}


def calculate_summary_totals(summary: Dict[str, dict]) -> dict:
    """Calculate grand totals across all permission segments."""
    if not isinstance(summary, dict) or not summary:
        return {
            "total_size_kb": 0,
            "total_rss_kb": 0,
            "total_pss_kb": 0,
            "total_shared_kb": 0,
            "total_private_kb": 0,
            "total_swap_kb": 0,
            "total_swap_pss_kb": 0,
            "total_anonymous_kb": 0,
            "total_anon_huge_pages_kb": 0,
            "overall_cache_pct": 0.0,
        }
    tot_sz = sum(d.get("size_kb", 0) for d in summary.values())
    tot_rss = sum(d.get("rss_kb", 0) for d in summary.values())
    tot_pss = sum(d.get("pss_kb", 0) for d in summary.values())
    tot_shared = sum(d.get("shared_kb", 0) for d in summary.values())
    tot_private = sum(d.get("private_kb", 0) for d in summary.values())
    tot_swap = sum(d.get("swap_kb", 0) for d in summary.values())
    tot_swap_pss = sum(d.get("swap_pss_kb", 0) for d in summary.values())
    tot_anon = sum(d.get("anonymous_kb", 0) for d in summary.values())
    tot_ahp = sum(d.get("anon_huge_pages_kb", 0) for d in summary.values())
    cache_pct = (tot_rss / tot_sz * 100.0) if tot_sz > 0 else 0.0

    return {
        "total_size_kb": tot_sz,
        "total_rss_kb": tot_rss,
        "total_pss_kb": tot_pss,
        "total_shared_kb": tot_shared,
        "total_private_kb": tot_private,
        "total_swap_kb": tot_swap,
        "total_swap_pss_kb": tot_swap_pss,
        "total_anonymous_kb": tot_anon,
        "total_anon_huge_pages_kb": tot_ahp,
        "overall_cache_pct": round(cache_pct, 2),
    }


def filter_mappings_by_min_rss(file_stats: Dict[Tuple[str, str], MapStats], min_rss_kb: int = 1024) -> Dict[Tuple[str, str], MapStats]:
    """Filter memory mappings by minimum RSS threshold."""
    if not isinstance(file_stats, dict):
        return {}
    if not isinstance(min_rss_kb, int) or isinstance(min_rss_kb, bool) or min_rss_kb < 0:
        min_rss_kb = 0
    return {k: v for k, v in file_stats.items() if isinstance(v, MapStats) and v.rss >= min_rss_kb}


def export_json_summary(summary: Dict[str, dict]) -> str:
    """Export structured JSON string containing segment metrics and summary totals."""
    import json
    if not isinstance(summary, dict):
        summary = {}
    totals = calculate_summary_totals(summary)
    payload = {
        "segments": summary,
        "totals": totals,
    }
    return json.dumps(payload, indent=2)


def format_memory_summary(summary: Dict[str, dict]) -> str:
    """Format memory map summary into clean human-readable diagnostic text."""
    if not isinstance(summary, dict) or not summary:
        return "No memory mapping data available."
    lines = ["Permissions | Size (kB) | RSS (kB) | PSS (kB) | Shared (kB) | Private (kB) | Cache %"]
    lines.append("-" * 75)
    for perms, data in sorted(summary.items()):
        sz = data.get("size_kb", 0)
        rss = data.get("rss_kb", 0)
        pss = data.get("pss_kb", 0)
        shared = data.get("shared_kb", 0)
        private = data.get("private_kb", 0)
        pct = data.get("cache_pct", 0.0)
        lines.append(f"{perms:<11} | {sz:>9} | {rss:>8} | {pss:>8} | {shared:>11} | {private:>12} | {pct:>6.2f}%")
    return "\n".join(lines)


def diff_smaps_snapshots(
    before: Dict[Tuple[str, str], MapStats],
    after: Dict[Tuple[str, str], MapStats],
) -> dict:
    """Compute exact per-mapping and aggregate memory deltas between two smaps snapshots."""
    if not isinstance(before, dict):
        before = {}
    if not isinstance(after, dict):
        after = {}

    all_keys = set(before.keys()) | set(after.keys())
    added = []
    removed = []
    changed = []

    tot_rss = tot_pss = tot_pd = tot_anon = tot_swap = 0

    for key in sorted(all_keys):
        b = before.get(key)
        a = after.get(key)
        b_stats = b if isinstance(b, MapStats) else MapStats()
        a_stats = a if isinstance(a, MapStats) else MapStats()

        d_rss = a_stats.rss - b_stats.rss
        d_pss = a_stats.pss - b_stats.pss
        d_pd = a_stats.private_dirty - b_stats.private_dirty
        d_anon = a_stats.anonymous - b_stats.anonymous
        d_swap = a_stats.swap - b_stats.swap

        tot_rss += d_rss
        tot_pss += d_pss
        tot_pd += d_pd
        tot_anon += d_anon
        tot_swap += d_swap

        entry = {
            "path": key[0],
            "perms": key[1],
            "rss_delta_kb": d_rss,
            "pss_delta_kb": d_pss,
            "private_dirty_delta_kb": d_pd,
            "anonymous_delta_kb": d_anon,
            "swap_delta_kb": d_swap,
        }
        if key not in before:
            added.append(entry)
        elif key not in after:
            removed.append(entry)
        elif any(v != 0 for v in (d_rss, d_pss, d_pd, d_anon, d_swap)):
            changed.append(entry)

    changed.sort(key=lambda item: abs(item["rss_delta_kb"]), reverse=True)
    added.sort(key=lambda item: item["rss_delta_kb"], reverse=True)
    removed.sort(key=lambda item: item["rss_delta_kb"])

    return {
        "totals_delta": {
            "rss_delta_kb": tot_rss,
            "pss_delta_kb": tot_pss,
            "private_dirty_delta_kb": tot_pd,
            "anonymous_delta_kb": tot_anon,
            "swap_delta_kb": tot_swap,
        },
        "added": added,
        "removed": removed,
        "changed": changed,
    }


def detect_memory_regressions(
    snapshots: List[Dict[Tuple[str, str], MapStats]],
    min_growth_kb: int = 1024,
    monotonic_ratio: float = 0.75,
) -> List[dict]:
    """Identify sustained memory-leak suspects across a chronological series of smaps snapshots.

    Uses ordinary least-squares slope and monotonic growth ratio over (private_dirty + anonymous)
    memory footprint per (path, perms) mapping.
    """
    if not isinstance(snapshots, list) or len(snapshots) < 2:
        return []
    if not isinstance(min_growth_kb, int) or isinstance(min_growth_kb, bool) or min_growth_kb < 0:
        min_growth_kb = 1024
    monotonic_ratio = max(0.0, min(1.0, float(monotonic_ratio)))

    all_keys: set[Tuple[str, str]] = set()
    for snap in snapshots:
        if isinstance(snap, dict):
            all_keys.update(snap.keys())

    n = len(snapshots)
    x_mean = (n - 1) / 2.0
    x_var = sum((i - x_mean) ** 2 for i in range(n))
    suspects: List[dict] = []

    for key in sorted(all_keys):
        series: List[int] = []
        for snap in snapshots:
            st = snap.get(key) if isinstance(snap, dict) else None
            if isinstance(st, MapStats):
                series.append(max(st.private_dirty, st.anonymous))
            else:
                series.append(0)

        growth = series[-1] - series[0]
        if growth < min_growth_kb:
            continue

        non_decreasing = sum(1 for i in range(1, n) if series[i] >= series[i - 1])
        mono = non_decreasing / (n - 1)
        if mono < monotonic_ratio:
            continue

        y_mean = sum(series) / n
        cov = sum((i - x_mean) * (series[i] - y_mean) for i in range(n))
        slope = cov / x_var if x_var > 0 else 0.0
        if slope <= 0.0:
            continue

        suspects.append(
            {
                "path": key[0],
                "perms": key[1],
                "initial_kb": series[0],
                "final_kb": series[-1],
                "growth_kb": growth,
                "slope_kb_per_sample": round(slope, 2),
                "monotonicity": round(mono, 3),
            }
        )

    suspects.sort(key=lambda item: item["growth_kb"], reverse=True)
    return suspects


def compute_memory_pressure_profile(file_stats: Dict[Tuple[str, str], MapStats]) -> dict:
    """Compute kernel page-cache, dirty-page, swap, THP, and shared-memory efficiency ratios."""
    if not isinstance(file_stats, dict) or not file_stats:
        return {
            "page_cache_residency_pct": 0.0,
            "dirty_ratio_pct": 0.0,
            "swap_pressure_pct": 0.0,
            "thp_coverage_pct": 0.0,
            "shared_efficiency_pct": 0.0,
        }

    size = rss = pss = dirty = swap = anon = ahp = 0
    for st in file_stats.values():
        if not isinstance(st, MapStats):
            continue
        size += st.size
        rss += st.rss
        pss += st.pss
        dirty += st.private_dirty + st.shared_dirty
        swap += st.swap
        anon += st.anonymous
        ahp += st.anon_huge_pages

    return {
        "page_cache_residency_pct": round((rss / size) * 100.0, 2) if size > 0 else 0.0,
        "dirty_ratio_pct": round((dirty / rss) * 100.0, 2) if rss > 0 else 0.0,
        "swap_pressure_pct": round((swap / (rss + swap)) * 100.0, 2) if (rss + swap) > 0 else 0.0,
        "thp_coverage_pct": round((ahp / anon) * 100.0, 2) if anon > 0 else 0.0,
        "shared_efficiency_pct": round(((rss - pss) / rss) * 100.0, 2) if rss > 0 and rss >= pss else 0.0,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze memory maps and calculate cache percentages')
    parser.add_argument('pid', type=int, help='Process ID to analyze')
    parser.add_argument('pattern', type=str, help='Regular expression pattern to match against file paths')
    parser.add_argument('-v', '--verbose', action='store_true', help='Print per-file information')
    
    args = parser.parse_args()
    
    percentages = calculate_cache_percentage(args.pid, args.pattern, args.verbose)
    print(f"Cache percentages for pattern '{args.pattern}':")
    for perms, percentage in percentages.items():
        print(f"  {perms}: {percentage:.2f}%")
