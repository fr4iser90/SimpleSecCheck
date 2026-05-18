"""Unit tests for periodic repo scan eligibility."""
from datetime import datetime, timedelta

import pytest

from application.helpers.periodic_repo_scan import (
    commit_hash_from_scan_metadata,
    cooldown_blocks_scan,
    evaluate_periodic_repo_scan,
    frequency_interval_elapsed,
    periodic_frequency_supports_scheduler,
)
from domain.entities.github_repo import GitHubRepo
from domain.entities.repo_scan_history_entry import RepoScanHistoryEntry


def _repo(**kwargs) -> GitHubRepo:
    defaults = dict(
        id="repo-1",
        user_id="user-1",
        repo_url="https://github.com/o/r.git",
        repo_owner="o",
        repo_name="r",
        branch="main",
        auto_scan_enabled=True,
        scan_on_push=True,
        scan_frequency="daily",
        scanners=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    defaults.update(kwargs)
    return GitHubRepo(**defaults)


def _entry(**kwargs) -> RepoScanHistoryEntry:
    defaults = dict(
        id="h1",
        repo_id="repo-1",
        scan_id="scan-1",
        branch="main",
        commit_hash="abc123",
        score=80,
        vulnerabilities={},
        created_at=datetime.utcnow() - timedelta(days=2),
    )
    defaults.update(kwargs)
    return RepoScanHistoryEntry(**defaults)


def test_periodic_frequency_supports_scheduler():
    assert periodic_frequency_supports_scheduler("daily")
    assert periodic_frequency_supports_scheduler("weekly")
    assert not periodic_frequency_supports_scheduler("on_push")
    assert not periodic_frequency_supports_scheduler("manual")


def test_frequency_interval_elapsed():
    old = datetime.utcnow() - timedelta(days=2)
    assert frequency_interval_elapsed("daily", old)
    recent = datetime.utcnow() - timedelta(hours=2)
    assert not frequency_interval_elapsed("daily", recent)


def test_evaluate_on_push_skipped():
    repo = _repo(scan_frequency="on_push")
    entry = _entry()
    should, reason, _ = evaluate_periodic_repo_scan(
        repo, entry, cooldown_seconds=0
    )
    assert not should
    assert reason == "on_push_webhook_only"


def test_evaluate_daily_due(monkeypatch):
    repo = _repo(scan_frequency="daily")
    entry = _entry(created_at=datetime.utcnow() - timedelta(days=2))
    monkeypatch.setattr(
        "application.helpers.periodic_repo_scan.resolve_branch_head_sha",
        lambda url, branch: "newsha999",
    )
    should, reason, head = evaluate_periodic_repo_scan(
        repo, entry, cooldown_seconds=0
    )
    assert should
    assert reason == "due:daily"
    assert head == "newsha999"


def test_evaluate_skips_unchanged_commit(monkeypatch):
    repo = _repo(scan_frequency="daily")
    entry = _entry(
        commit_hash="sameSHA",
        created_at=datetime.utcnow() - timedelta(days=2),
    )
    monkeypatch.setattr(
        "application.helpers.periodic_repo_scan.resolve_branch_head_sha",
        lambda url, branch: "sameSHA",
    )
    should, reason, _ = evaluate_periodic_repo_scan(
        repo, entry, cooldown_seconds=0
    )
    assert not should
    assert reason == "no_new_commit"


def test_commit_hash_from_scan_metadata():
    assert commit_hash_from_scan_metadata({"commit_hash": "deadbeef"}) == "deadbeef"
    assert (
        commit_hash_from_scan_metadata({"git_info": {"commit_hash": "cafe"}})
        == "cafe"
    )


def test_cooldown_blocks_recent():
    recent = datetime.utcnow() - timedelta(minutes=30)
    assert cooldown_blocks_scan(recent, cooldown_seconds=7200)
