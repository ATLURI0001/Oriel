import sys
from pathlib import Path
import pytest

# Add tools directory to sys.path
tools_dir = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(tools_dir))

smaps_view = __import__("smaps-view")
parse_smaps = smaps_view.parse_smaps
calculate_cache_percentage = smaps_view.calculate_cache_percentage


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
