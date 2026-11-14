import importlib.util
import io
import json
from pathlib import Path
from unittest.mock import patch
import pytest

CALLGRAPH_PATH = Path(__file__).resolve().parent.parent / "tools" / "callgraph" / "callgraph.py"
spec = importlib.util.spec_from_file_location("callgraph", CALLGRAPH_PATH)
callgraph = importlib.util.module_from_spec(spec)
spec.loader.exec_module(callgraph)


def _lsp_frame(obj: dict) -> bytes:
    body = json.dumps(obj).encode("utf-8")
    return f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body


def test_read_msg_parses_case_insensitive_header():
    lsp = callgraph.Lsp.__new__(callgraph.Lsp)
    lsp.proc = type("Proc", (), {"stdout": io.BytesIO(b"content-length: 13\r\n\r\n{\"id\": 12345}")})()
    assert lsp.read_msg() == {"id": 12345}


def test_read_msg_rejects_missing_content_length():
    lsp = callgraph.Lsp.__new__(callgraph.Lsp)
    lsp.proc = type("Proc", (), {"stdout": io.BytesIO(b"X-Other: 5\r\n\r\n{}")})()
    with pytest.raises(SystemExit, match="Content-Length"):
        lsp.read_msg()


def test_read_msg_rejects_truncated_body():
    lsp = callgraph.Lsp.__new__(callgraph.Lsp)
    lsp.proc = type("Proc", (), {"stdout": io.BytesIO(b"Content-Length: 50\r\n\r\n{\"partial\":1}")})()
    with pytest.raises(SystemExit, match="reading LSP message body"):
        lsp.read_msg()


def test_handle_workspace_configuration_missing_items_defaults_empty():
    lsp = callgraph.Lsp.__new__(callgraph.Lsp)
    sent = []
    lsp.send = sent.append
    consumed = lsp.handle({"jsonrpc": "2.0", "id": 7, "method": "workspace/configuration", "params": {}})
    assert consumed is True
    assert sent == [{"jsonrpc": "2.0", "id": 7, "result": []}]


def test_norm_locations_handles_location_link_fallback_and_malformed():
    resp = [
        {"targetUri": "file:///a.rs", "targetRange": {"start": {"line": 4, "character": 2}}},
        {"uri": "file:///b.rs", "range": {"start": {"line": 10, "character": 0}}},
        {"invalid": True},
        "not-a-dict",
    ]
    assert callgraph.norm_locations(resp) == [
        ("file:///a.rs", {"line": 4, "character": 2}),
        ("file:///b.rs", {"line": 10, "character": 0}),
    ]


def test_keep_normalizes_windows_backslashes(tmp_path):
    with patch.object(callgraph, "ROOT", str(tmp_path)):
        src_file = str(tmp_path / "lib" / "src" / "main.rs").replace("/", "\\")
        test_file = str(tmp_path / "lib" / "tests" / "unit.rs").replace("/", "\\")
        outside = str(tmp_path.parent / "other" / "lib.rs")
        assert callgraph.keep(src_file) is True
        assert callgraph.keep(test_file) is False
        assert callgraph.keep(outside) is False


def test_position_in_file_utf8_and_bounds(tmp_path):
    rs = tmp_path / "sample.rs"
    rs.write_text("// café — UTF-8 comment\npub fn compute_score() {}\n", encoding="utf-8")
    path, lineno, col = callgraph.position_in_file(f"{rs}:2")
    assert path == str(rs.resolve())
    assert lineno == 1
    assert col == 7

    with pytest.raises(SystemExit, match="out of range"):
        callgraph.position_in_file(f"{rs}:99")
    with pytest.raises(SystemExit, match="expected <path>:<line>"):
        callgraph.position_in_file("no_colon")


def test_uri_to_path_cross_platform_and_encoded():
    import os
    # Linux-style URI
    p_linux = callgraph.uri_to_path("file:///home/user/project/src/lib.rs")
    assert "/home/user/project/src/lib.rs" in p_linux.replace("\\", "/")

    # Windows-style URI
    p_win = callgraph.uri_to_path("file:///C:/Users/user/project/src/lib.rs")
    norm_win = p_win.replace("/", "\\")
    assert norm_win.lower().endswith("c:\\users\\user\\project\\src\\lib.rs")

    # URL encoded URI
    p_enc = callgraph.uri_to_path("file:///C%3A/Users/user%20name/project/src/lib.rs")
    norm_enc = p_enc.replace("/", "\\")
    assert "user name" in norm_enc

    # Plain paths or invalid URIs
    assert callgraph.uri_to_path("plain/path.rs") == os.path.normpath("plain/path.rs")
    assert callgraph.uri_to_path("") == ""
    assert callgraph.uri_to_path(None) == ""


def test_safe_relpath_and_cross_platform_crate_extraction():
    # safe_relpath handles empty or cross-drive errors
    assert callgraph.safe_relpath("") == ""
    assert callgraph.safe_relpath("relative/path/file.rs") != ""

    # crate_of and short_path normalize Windows backslashes
    win_rel = "lib\\segment\\src\\entry.rs"
    unix_rel = "lib/segment/src/entry.rs"
    assert callgraph.crate_of(win_rel) == "segment"
    assert callgraph.crate_of(unix_rel) == "segment"
    assert callgraph.crate_of("root/other.rs") == "qdrant"

    win_short = "lib\\segment\\src\\data\\index\\builder.rs"
    assert callgraph.short_path(win_short) == "index/builder.rs"
    assert callgraph.short_path("lib/src/main.rs") == "main.rs"
