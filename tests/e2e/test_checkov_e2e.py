"""
E2E: Checkov — gleiche Pipeline wie ``test_scan_profiles_e2e`` (``scan_type=code``).

Checkov unter ``/api/scanners/?scan_type=code``. Wartezeit / httpx-Timeout wie dort: max
``scan_profiles.*.timeout`` über alle Plugins (``manifest_timeouts.py``).

Bootstrap: Modul-Docstring ``test_scan_profiles_e2e`` (frische DB: ``docker compose down -v``).
"""
from __future__ import annotations

import httpx
import pytest

from tests.e2e.setup_bootstrap import run_session_bootstrap
from tests.e2e.test_scan_profiles_e2e import (
    BASE_URL,
    TIMEOUT,
    _admin_creds,
    _json_headers,
    _login,
    _pick_scanners,
    _post_scan,
    _wait_terminal_status,
)

_PROFILES = ("quick", "standard", "deep")


@pytest.fixture(scope="session", autouse=True)
def _e2e_checkov_bootstrap() -> None:
    """Session bootstrap (shared semantics with scan-profile E2E)."""
    run_session_bootstrap()
    yield


@pytest.mark.asyncio
@pytest.mark.parametrize("profile", _PROFILES)
async def test_e2e_checkov_scan_reaches_terminal_with_checkov_step(profile: str) -> None:
    creds = _admin_creds()
    assert creds is not None, (
        "Bootstrap should set admin credentials (fresh DB: docker compose down -v)."
    )
    admin_email, admin_password = creds

    async with httpx.AsyncClient(
        base_url=BASE_URL, timeout=TIMEOUT, headers=_json_headers()
    ) as client:
        token = await _login(client, admin_email, admin_password)

    async with httpx.AsyncClient(
        base_url=BASE_URL, timeout=TIMEOUT, headers=_json_headers(token)
    ) as admin_client:
        picked = await _pick_scanners(admin_client)
        scanner_names = [n for n in picked if n.strip().lower() == "checkov"]
        if not scanner_names:
            pytest.skip(
                "Checkov not enabled for code scans — see GET /api/scanners/?scan_type=code"
            )

        response = await _post_scan(
            admin_client, profile=profile, scanner_names=scanner_names
        )
        assert response.status_code in (200, 201), (
            f"Start scan failed: {response.status_code} {response.text}"
        )
        scan_id = response.json().get("id")
        assert isinstance(scan_id, str) and scan_id.strip(), "No scan id"

        status = await _wait_terminal_status(admin_client, scan_id)
        assert status in ("completed", "failed", "cancelled", "interrupted")

        steps_response = await admin_client.get(f"/api/v1/scans/{scan_id}/steps")
        assert steps_response.status_code == 200, steps_response.text
        steps = steps_response.json().get("steps", [])
        step_names = {str(s.get("name", "")).strip() for s in steps}
        assert "Checkov" in step_names, (
            f"Expected Checkov step; got: {sorted(step_names)}"
        )
        checkov_step = next(
            (s for s in steps if str(s.get("name", "")).strip() == "Checkov"), None
        )
        assert checkov_step is not None
        st = str(checkov_step.get("status", "")).lower()
        assert st in ("completed", "failed", "skipped"), (
            f"Checkov step terminal expected; got {checkov_step.get('status')!r}"
        )
