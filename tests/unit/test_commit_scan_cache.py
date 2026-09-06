"""Unit tests for commit SHA helpers and commit-scan cache helpers."""
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from application.helpers import periodic_repo_scan as periodic  # noqa: E402
from application.helpers.commit_scan_cache import normalize_commit_into_metadata  # noqa: E402


def test_commits_match_exact_and_prefix():
    full = "abcdef0123456789abcdef0123456789abcdef01"
    assert periodic.commits_match(full, full)
    assert periodic.commits_match(full, full[:8])
    assert periodic.commits_match(full[:12].upper(), full)
    assert not periodic.commits_match(full, "deadbeef" + full[8:])
    assert not periodic.commits_match(full[:6], full)  # too short prefix
    assert not periodic.commits_match(None, full)
    assert not periodic.commits_match("", full)


def test_commit_hash_from_metadata_aliases():
    assert periodic.commit_hash_from_scan_metadata({"commit_sha": "abc1234"}) == "abc1234"
    assert periodic.commit_hash_from_scan_metadata({"commit_hash": "abc1234"}) == "abc1234"
    assert periodic.commit_hash_from_scan_metadata({"commit": "abc1234"}) == "abc1234"
    assert (
        periodic.commit_hash_from_scan_metadata({"git_info": {"commit_sha": "deadbeef"}})
        == "deadbeef"
    )
    assert periodic.commit_hash_from_scan_metadata({}) is None
    assert periodic.scan_metadata_dict(type("S", (), {"scan_metadata": {"a": 1}})()) == {"a": 1}
    assert periodic.scan_metadata_dict(type("S", (), {"metadata": {"b": 2}})()) == {"b": 2}


def test_normalize_commit_into_metadata():
    meta = normalize_commit_into_metadata({"commit_sha": "abcdef0"}, None)
    assert meta.get("commit_hash") == "abcdef0"
    assert "commit_sha" not in meta
