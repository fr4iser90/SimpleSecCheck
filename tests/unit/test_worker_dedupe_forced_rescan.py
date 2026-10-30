"""Worker short-circuit must not swallow an explicitly forced rescan.

Driven with asyncio.run() instead of @pytest.mark.asyncio so the rules run in any
environment, including ones without the pytest-asyncio plugin.
"""
import asyncio
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
for candidate in (_ROOT, _ROOT / "backend"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from worker.domain.job_execution.services import scan_dedupe_fanout as fanout  # noqa: E402

COMMIT = "abcdef0123456789abcdef0123456789abcdef01"
USER = "11111111-1111-1111-1111-111111111111"
TARGET = "https://github.com/fr4iser90/SimpleSecCheck"


class _Mappings:
    def __init__(self, rows):
        self._rows = rows

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return list(self._rows)


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return _Mappings(self._rows)


class FakeSession:
    def __init__(self, me_row, winner_rows):
        self.me_row = me_row
        self.winner_rows = winner_rows
        self.writes = []
        self.commits = 0

    async def execute(self, statement, parameters=None):
        sql = str(statement).strip().upper()
        if sql.startswith("UPDATE"):
            self.writes.append((sql, parameters))
            return _Result([])
        if "FROM SCANS WHERE ID = :ID" in sql:
            return _Result([self.me_row] if self.me_row else [])
        return _Result(self.winner_rows)

    async def commit(self):
        self.commits += 1


class FakeAdapter:
    def __init__(self, session):
        self.session = session

    def get_session(self):
        session = self.session

        class _Ctx:
            async def __aenter__(self):
                return session

            async def __aexit__(self, *exc):
                return False

        return _Ctx()


def _me(meta):
    return {
        "id": "new-scan",
        "user_id": USER,
        "target_url": TARGET,
        "status": "pending",
        "scan_metadata": meta,
        "config": {},
        "total_vulnerabilities": 0,
        "critical_vulnerabilities": 0,
        "high_vulnerabilities": 0,
        "medium_vulnerabilities": 0,
        "low_vulnerabilities": 0,
        "info_vulnerabilities": 0,
        "duration": None,
        "results": None,
    }


def _winner():
    return {
        "id": "old-scan",
        "scan_metadata": {"commit_hash": COMMIT},
        "total_vulnerabilities": 7,
        "critical_vulnerabilities": 1,
        "high_vulnerabilities": 2,
        "medium_vulnerabilities": 3,
        "low_vulnerabilities": 1,
        "info_vulnerabilities": 0,
        "duration": 42,
        "results": None,
    }


async def _noop_publish(**kwargs):
    return None


def _short_circuit(meta):
    session = FakeSession(_me(meta), [_winner()])
    adapter = FakeAdapter(session)
    result = asyncio.run(
        fanout.try_short_circuit_duplicate_job(
            adapter, "new-scan", publish_events=_noop_publish
        )
    )
    return result, session


def test_completed_same_commit_still_short_circuits(monkeypatch):
    """Default path unchanged: same commit + completed sibling → reuse, no docker run."""
    symlink_calls = []
    monkeypatch.setattr(
        fanout, "_symlink_results", lambda winner, sibling: symlink_calls.append((winner, sibling))
    )

    result, session = _short_circuit({"commit_hash": COMMIT})
    assert result is True
    assert session.commits == 1
    assert len(session.writes) == 1
    params = session.writes[0][1]
    assert params["scan_id"] == "new-scan"
    assert symlink_calls == [("old-scan", "new-scan")]


def test_forced_rescan_is_not_short_circuited(monkeypatch):
    """metadata.forced_rescan set by the API → the job must run for real."""
    symlink_calls = []
    monkeypatch.setattr(
        fanout, "_symlink_results", lambda winner, sibling: symlink_calls.append((winner, sibling))
    )

    result, session = _short_circuit({"commit_hash": COMMIT, "forced_rescan": True})
    assert result is False
    assert session.writes == []
    assert session.commits == 0
    assert symlink_calls == []
