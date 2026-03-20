"""Scan profile resolution from manifest-backed scanner_metadata (no tool env in domain)."""
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from application.services.scan_profile_merge import merge_resolved_profile_into_overrides
from application.services.scan_profile_resolver import resolve_scan_profile_from_manifests
from domain.entities.scanner import Scanner
from domain.value_objects.scan_profile import (
    default_scan_profile_for_role,
    ResolvedScanProfile,
    ScanProfileName,
    merge_profile_tuning,
    normalize_scan_profile_name,
)


@pytest.mark.asyncio
async def test_resolve_scan_profile_from_manifests_merges_env():
    repo = AsyncMock()

    async def repo_list():
        return [
            Scanner(
                id="1",
                name="Zap",
                scan_types=["website"],
                priority=1,
                requires_condition=None,
                enabled=True,
                scanner_metadata={
                    "tools_key": "zap",
                    "scan_profiles": {
                        "quick": {
                            "hints": {"depth": "shallow", "intensity": "low", "coverage": "essential"},
                            "env": {"ZAP_USE_ACTIVE_SCAN": "0", "ZAP_OPTIONS": "-config foo=bar"},
                        },
                    },
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            Scanner(
                id="2",
                name="Nuclei",
                scan_types=["website"],
                priority=2,
                requires_condition=None,
                enabled=True,
                scanner_metadata={
                    "tools_key": "nuclei",
                    "scan_profiles": {
                        "quick": {"env": {"NUCLEI_RATE_LIMIT": "50"}},
                    },
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]

    repo.list_all = repo_list

    r = await resolve_scan_profile_from_manifests(
        profile="quick",
        profile_tuning=None,
        scanner_repository=repo,
    )
    assert r.profile == "quick"
    assert r.depth == "shallow"
    assert r.per_tool["zap"]["env"]["ZAP_USE_ACTIVE_SCAN"] == "0"
    assert r.per_tool["nuclei"]["env"]["NUCLEI_RATE_LIMIT"] == "50"


@pytest.mark.asyncio
async def test_profile_tuning_overrides_env():
    base = ResolvedScanProfile(
        profile="standard",
        depth="medium",
        intensity="medium",
        coverage="balanced",
        per_tool={"zap": {"env": {"ZAP_USE_ACTIVE_SCAN": "1"}}},
    )
    merged = merge_profile_tuning(
        base,
        {"zap": {"ZAP_USE_ACTIVE_SCAN": "0"}},
    )
    assert merged.per_tool["zap"]["env"]["ZAP_USE_ACTIVE_SCAN"] == "0"


def test_merge_resolved_profile_into_overrides_applies_profile_timeout():
    merged = {
        "zap": {
            "timeout": 600,
            "enabled": True,
            "config": {},
            "env": {},
            "tools_key": "zap",
        }
    }
    resolved = ResolvedScanProfile(
        profile="deep",
        depth="deep",
        intensity="high",
        coverage="broad",
        per_tool={"zap": {"timeout": 1800, "env": {}}},
    )
    out = merge_resolved_profile_into_overrides(merged, resolved)
    assert out["zap"]["timeout"] == 1800


def test_merge_resolved_profile_into_overrides_admin_wins():
    merged = {
        "zap": {
            "timeout": 600,
            "enabled": True,
            "config": {},
            "env": {"ZAP_OPTIONS": "admin"},
            "tools_key": "zap",
        }
    }
    resolved = ResolvedScanProfile(
        profile="quick",
        depth="shallow",
        intensity="low",
        coverage="essential",
        per_tool={"zap": {"env": {"ZAP_OPTIONS": "manifest", "ZAP_USE_ACTIVE_SCAN": "0"}}},
    )
    out = merge_resolved_profile_into_overrides(merged, resolved)
    assert out["zap"]["env"]["ZAP_USE_ACTIVE_SCAN"] == "0"
    assert out["zap"]["env"]["ZAP_OPTIONS"] == "admin"


def test_normalize_scan_profile_unknown_defaults_standard():
    assert normalize_scan_profile_name("nope") == ScanProfileName.STANDARD.value
    assert normalize_scan_profile_name("deep") == "deep"


def test_default_scan_profile_for_role():
    assert default_scan_profile_for_role("admin", is_authenticated=True) == ScanProfileName.DEEP.value
    assert default_scan_profile_for_role("user", is_authenticated=True) == ScanProfileName.STANDARD.value
    assert default_scan_profile_for_role(None, is_authenticated=False) == ScanProfileName.QUICK.value
