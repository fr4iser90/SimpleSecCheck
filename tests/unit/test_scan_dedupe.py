"""Unit tests for active-scan dedupe grouping."""
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from application.helpers import scan_dedupe as mod  # noqa: E402


def _scan(**kwargs):
    base = dict(
        id="a",
        target_url="https://github.com/org/repo.git",
        status="pending",
        created_at=datetime.utcnow(),
        config={"git_branch": "main"},
        scan_metadata={},
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_pick_winner_prefers_running_then_oldest():
    t0 = datetime.utcnow() - timedelta(hours=2)
    t1 = datetime.utcnow() - timedelta(hours=1)
    older = _scan(id="old", status="pending", created_at=t0)
    newer = _scan(id="new", status="pending", created_at=t1)
    running = _scan(id="run", status="running", created_at=t1)
    assert mod.pick_winner([newer, older]).id == "old"
    assert mod.pick_winner([newer, older, running]).id == "run"


def test_groups_match_by_commit_prefix():
    full = "abcdef0123456789abcdef0123456789abcdef01"
    a = _scan(scan_metadata={"commit_hash": full})
    b = _scan(scan_metadata={"commit_sha": full[:8]})
    assert mod.groups_match(a, b)
    c = _scan(scan_metadata={"commit_hash": "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"})
    assert not mod.groups_match(a, c)
