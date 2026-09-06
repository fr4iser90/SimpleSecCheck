"""Unit tests for commit SHA helpers and commit-scan cache helpers."""
import importlib.util
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, _BACKEND / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_commits_match_exact_and_prefix():
    mod = _load("periodic_repo_scan", "application/helpers/periodic_repo_scan.py")
    full = "abcdef0123456789abcdef0123456789abcdef01"
    assert mod.commits_match(full, full)
    assert mod.commits_match(full, full[:8])
    assert mod.commits_match(full[:12].upper(), full)
    assert not mod.commits_match(full, "deadbeef" + full[8:])
    assert not mod.commits_match(full[:6], full)  # too short prefix
    assert not mod.commits_match(None, full)
    assert not mod.commits_match("", full)


def test_commit_hash_from_metadata_aliases():
    mod = _load("periodic_repo_scan", "application/helpers/periodic_repo_scan.py")
    assert mod.commit_hash_from_scan_metadata({"commit_sha": "abc1234"}) == "abc1234"
    assert mod.commit_hash_from_scan_metadata({"commit_hash": "abc1234"}) == "abc1234"
    assert mod.commit_hash_from_scan_metadata({"commit": "abc1234"}) == "abc1234"
    assert (
        mod.commit_hash_from_scan_metadata({"git_info": {"commit_sha": "deadbeef"}})
        == "deadbeef"
    )
    assert mod.commit_hash_from_scan_metadata({}) is None
    assert mod.scan_metadata_dict(type("S", (), {"scan_metadata": {"a": 1}})()) == {"a": 1}
    assert mod.scan_metadata_dict(type("S", (), {"metadata": {"b": 2}})()) == {"b": 2}


def test_normalize_commit_into_metadata():
    mod = _load("commit_scan_cache", "application/helpers/commit_scan_cache.py")
    meta = mod.normalize_commit_into_metadata({"commit_sha": "abcdef0"}, None)
    assert meta.get("commit_hash") == "abcdef0"
    assert "commit_sha" not in meta
