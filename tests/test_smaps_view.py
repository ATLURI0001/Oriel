import sys
from pathlib import Path
import pytest

# Add tools directory to sys.path
tools_dir = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(tools_dir))

smaps_view = __import__("smaps-view")
parse_smaps = smaps_view.parse_smaps
calculate_cache_percentage = smaps_view.calculate_cache_percentage
summarize_smaps = smaps_view.summarize_smaps
format_memory_summary = smaps_view.format_memory_summary
calculate_summary_totals = smaps_view.calculate_summary_totals
filter_mappings_by_min_rss = smaps_view.filter_mappings_by_min_rss
export_json_summary = smaps_view.export_json_summary


SAMPLE_SMAPS = """7de883800000-7de885800000 r--s 00000000 00:33 26610006                   /qdrant/storage/collections/benchmark/0/segments/chunk_1.mmap
Size:              32768 kB
KernelPageSize:        4 kB
MMUPageSize:           4 kB
Rss:                8192 kB
Pss:                8192 kB
7de885800000-7de887800000 rw-s 00000000 00:33 26610007                   /qdrant/storage/collections/benchmark/0/segments/chunk_2.mmap
Size:              16384 kB
KernelPageSize:        4 kB
MMUPageSize:           4 kB
Rss:                4096 kB
Pss:                4096 kB
7de887800000-7de889800000 r-xp 00000000 00:33 26610008                   /usr/lib/libc.so
Size:               2048 kB
Rss:                1024 kB
"""


def test_parse_smaps_matching_pattern():
    stats = parse_smaps(SAMPLE_SMAPS, r".*/benchmark/.*")
    assert len(stats) == 2
    
    key1 = ("/qdrant/storage/collections/benchmark/0/segments/chunk_1.mmap", "r--s")
    assert key1 in stats
    assert stats[key1].size == 32768
    assert stats[key1].rss == 8192

    key2 = ("/qdrant/storage/collections/benchmark/0/segments/chunk_2.mmap", "rw-s")
    assert key2 in stats
    assert stats[key2].size == 16384
    assert stats[key2].rss == 4096


def test_calculate_cache_percentage():
    percentages = calculate_cache_percentage(1, r".*/benchmark/.*", smaps_content=SAMPLE_SMAPS)
    assert "r--s" in percentages
    assert "rw-s" in percentages
    # 8192 / 32768 = 25.0%
    assert abs(percentages["r--s"] - 25.0) < 0.01
    # 4096 / 16384 = 25.0%
    assert abs(percentages["rw-s"] - 25.0) < 0.01


def test_parse_smaps_invalid_regex():
    with pytest.raises(ValueError, match="Invalid regex pattern"):
        parse_smaps(SAMPLE_SMAPS, "[unclosed")


def test_calculate_cache_percentage_invalid_pid():
    res = calculate_cache_percentage(-5, r".*")
    assert res == {}


def test_parse_smaps_empty_content():
    stats = parse_smaps("", r".*")
    assert stats == {}


def test_parse_smaps_preserves_paths_with_spaces():
    spaced_smaps = """7de883800000-7de885800000 r--s 00000000 00:33 26610006   /data/my index/vector storage/chunk 1.mmap
Size:              4096 kB
Rss:               2048 kB
"""
    stats = parse_smaps(spaced_smaps, r".*/my index/.*")
    key = ("/data/my index/vector storage/chunk 1.mmap", "r--s")
    assert key in stats
    assert stats[key].size == 4096
    assert stats[key].rss == 2048


def test_calculate_cache_percentage_missing_proc_graceful():
    # On Windows or for a non-existent PID, missing /proc/{pid}/smaps returns {} safely
    res = calculate_cache_percentage(99999999, r".*")
    assert res == {}


def test_parse_smaps_pss_and_summarize():
    stats = parse_smaps(SAMPLE_SMAPS, r".*/benchmark/.*")
    key1 = ("/qdrant/storage/collections/benchmark/0/segments/chunk_1.mmap", "r--s")
    assert stats[key1].pss == 8192

    summary = summarize_smaps(1, r".*/benchmark/.*", smaps_content=SAMPLE_SMAPS)
    assert "r--s" in summary
    assert summary["r--s"]["size_kb"] == 32768
    assert summary["r--s"]["rss_kb"] == 8192
    assert summary["r--s"]["pss_kb"] == 8192
    assert abs(summary["r--s"]["pss_pct"] - 25.0) < 0.01


def test_parse_smaps_empty_or_none_pattern_defaults_wildcard():
    stats_none = parse_smaps(SAMPLE_SMAPS, None)
    assert len(stats_none) == 3
    stats_empty = parse_smaps(SAMPLE_SMAPS, "")
    assert len(stats_empty) == 3
    summary_empty = summarize_smaps(1, "", smaps_content=SAMPLE_SMAPS)
    assert "r-xp" in summary_empty


def test_parse_smaps_shared_private_and_format_summary():
    detailed_smaps = """7de883800000-7de885800000 r--s 00000000 00:33 26610006   /data/chunk.mmap
Size:              8192 kB
Rss:               4096 kB
Pss:               2048 kB
Shared_Clean:      1024 kB
Shared_Dirty:       512 kB
Private_Clean:     2048 kB
Private_Dirty:      512 kB
"""
    stats = parse_smaps(detailed_smaps, r".*")
    key = ("/data/chunk.mmap", "r--s")
    assert key in stats
    s = stats[key]
    assert s.shared_clean == 1024
    assert s.shared_dirty == 512
    assert s.shared == 1536
    assert s.private_clean == 2048
    assert s.private_dirty == 512
    assert s.private == 2560

    summary = summarize_smaps(1, r".*", smaps_content=detailed_smaps)
    assert summary["r--s"]["shared_kb"] == 1536
    assert summary["r--s"]["private_kb"] == 2560

    formatted = format_memory_summary(summary)
    assert "r--s" in formatted
    assert "8192" in formatted
    assert "1536" in formatted
    assert "2560" in formatted

    empty_fmt = format_memory_summary({})
    assert "No memory mapping data available" in empty_fmt


def test_parse_smaps_swap_and_summary_totals():
    swap_smaps = """7de883800000-7de885800000 rw-p 00000000 00:33 26610006   /var/log/app.log
Size:              4096 kB
Rss:               2048 kB
Pss:               1024 kB
Shared_Clean:       512 kB
Shared_Dirty:         0 kB
Private_Clean:     1024 kB
Private_Dirty:      512 kB
Swap:               256 kB
SwapPss:            128 kB
"""
    stats = parse_smaps(swap_smaps, r".*")
    key = ("/var/log/app.log", "rw-p")
    assert key in stats
    s = stats[key]
    assert s.swap == 256
    assert s.swap_pss == 128

    summary = summarize_smaps(1, r".*", smaps_content=swap_smaps)
    assert summary["rw-p"]["swap_kb"] == 256
    assert summary["rw-p"]["swap_pss_kb"] == 128

    totals = calculate_summary_totals(summary)
    assert totals["total_size_kb"] == 4096
    assert totals["total_rss_kb"] == 2048
    assert totals["total_pss_kb"] == 1024
    assert totals["total_shared_kb"] == 512
    assert totals["total_private_kb"] == 1536
    assert totals["total_swap_kb"] == 256
    assert totals["total_swap_pss_kb"] == 128
    assert totals["overall_cache_pct"] == 50.0

    empty_totals = calculate_summary_totals({})
    assert empty_totals["total_size_kb"] == 0
    assert empty_totals["overall_cache_pct"] == 0.0


def test_parse_smaps_anonymous_and_json_export():
    anon_smaps = """7de883800000-7de885800000 rw-p 00000000 00:33 26610006   /var/lib/heap.bin
Size:              8192 kB
Rss:               4096 kB
Pss:               4096 kB
Anonymous:         2048 kB
AnonHugePages:     1024 kB
"""
    stats = parse_smaps(anon_smaps, r".*")
    key = ("/var/lib/heap.bin", "rw-p")
    assert key in stats
    assert stats[key].anonymous == 2048
    assert stats[key].anon_huge_pages == 1024

    # Test filtering by min RSS
    filtered = filter_mappings_by_min_rss(stats, min_rss_kb=4000)
    assert len(filtered) == 1
    assert filter_mappings_by_min_rss(stats, min_rss_kb=5000) == {}
    assert filter_mappings_by_min_rss({}) == {}

    summary = summarize_smaps(1, r".*", smaps_content=anon_smaps)
    assert summary["rw-p"]["anonymous_kb"] == 2048
    assert summary["rw-p"]["anon_huge_pages_kb"] == 1024

    totals = calculate_summary_totals(summary)
    assert totals["total_anonymous_kb"] == 2048
    assert totals["total_anon_huge_pages_kb"] == 1024

    # Test export JSON
    json_str = export_json_summary(summary)
    assert '"rw-p"' in json_str
    assert '"total_anonymous_kb": 2048' in json_str
    assert '"total_anon_huge_pages_kb": 1024' in json_str


