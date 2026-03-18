"""Unit tests for heartbeat-based stale scan detection."""
from datetime import datetime, timedelta

from domain.services.scan_heartbeat_recovery import scan_running_is_stale


def test_fresh_heartbeat_not_stale():
    now = datetime(2025, 1, 1, 12, 0, 0)
    hb = now - timedelta(seconds=30)
    assert not scan_running_is_stale(
        last_heartbeat_at=hb, started_at=now - timedelta(hours=1), now=now
    )


def test_stale_heartbeat():
    now = datetime(2025, 1, 1, 12, 0, 0)
    hb = now - timedelta(seconds=400)
    assert scan_running_is_stale(
        last_heartbeat_at=hb, started_at=now - timedelta(hours=1), now=now
    )


def test_null_heartbeat_recent_start():
    now = datetime(2025, 1, 1, 12, 0, 0)
    assert not scan_running_is_stale(
        last_heartbeat_at=None,
        started_at=now - timedelta(minutes=5),
        now=now,
    )


def test_null_heartbeat_old_start():
    now = datetime(2025, 1, 1, 12, 0, 0)
    assert scan_running_is_stale(
        last_heartbeat_at=None,
        started_at=now - timedelta(minutes=30),
        now=now,
    )
