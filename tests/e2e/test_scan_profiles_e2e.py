"""
E2E: Scan profiles quick / standard / deep — full pipeline + RBAC.

Full pipeline (slow), **all three profiles** for each role (order: guest → user → admin):

- **Guest:** ``quick`` → wait for terminal status + steps; ``standard`` / ``deep`` → expect **403**
  (policy forbids heavier profiles; no worker run).
- **User:** ``quick`` / ``standard`` → full pipeline; ``deep`` → **403**.
- **Admin:** all three → full pipeline.

Fast RBAC tests below still assert the same status codes without waiting on the worker.

**First-run bootstrap (session autouse):** if setup is incomplete, runs the wizard
(setup token **only** from ``docker compose logs backend``), creates an admin with
**cryptographically random** email/password, provisions the synthetic E2E user. Credentials
live in bootstrap session state (``setup_bootstrap._bootstrap_state``), not in shell env vars.

If setup is **already** complete: bootstrap fails — from the repo root run
``docker compose down -v`` then ``docker compose up --build`` for a fresh database.



If ``require_email_verification`` is on, admin-created users cannot log in until verified;
user-RBAC tests are skipped with a clear reason (admins are exempt).
"""
from __future__ import annotations

import asyncio
import time
from typing import Optional

import httpx
import pytest
import pytest_asyncio

from tests.e2e.e2e_constants import (
    E2E_API_BASE_URL,
    E2E_STATUS_POLL_INTERVAL_S,
    E2E_TEST_REPO_URL,
)
from tests.e2e.manifest_timeouts import max_scan_profile_timeout_seconds_all_plugins
from tests.e2e.setup_bootstrap import (
    e2e_admin_credentials,
    e2e_user_email_for_tests,
    e2e_user_password_for_tests,
    e2e_username_for_tests,
    run_session_bootstrap,
)

_MANIFEST_MAX_SCAN_PROFILE_S = max_scan_profile_timeout_seconds_all_plugins()
BASE_URL = E2E_API_BASE_URL.rstrip("/")
# httpx per-request timeout + terminal-status wait: max ``scan_profiles.*.timeout`` (manifests).
TIMEOUT = _MANIFEST_MAX_SCAN_PROFILE_S
SCAN_WAIT_TIMEOUT = _MANIFEST_MAX_SCAN_PROFILE_S
POLL_INTERVAL = E2E_STATUS_POLL_INTERVAL_S
TEST_REPO = E2E_TEST_REPO_URL

_PROFILES = ("quick", "standard", "deep")


@pytest.fixture(scope="session", autouse=True)
def _e2e_scan_profiles_bootstrap() -> None:
    """Session bootstrap: wizard on fresh DB; existing DB → see module docstring (down -v)."""
    run_session_bootstrap()
    yield


def _admin_creds() -> Optional[tuple[str, str]]:
    return e2e_admin_credentials()


def _json_headers(token: Optional[str] = None) -> dict[str, str]:
    h = {"Accept": "application/json", "Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


@pytest_asyncio.fixture
async def guest_client() -> httpx.AsyncClient:
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=TIMEOUT,
        headers=_json_headers(),
    ) as client:
        yield client


async def _login(client: httpx.AsyncClient, email: str, password: str) -> str:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    if r.status_code != 200:
        pytest.fail(f"Login failed for {email!r}: {r.status_code} {r.text}")
    data = r.json()
    token = data.get("access_token")
    assert isinstance(token, str) and token.strip(), "No access_token in login response"
    return token


async def _ensure_test_user(client: httpx.AsyncClient, admin_token: str) -> tuple[str, str]:
    """Create a normal user via admin API; bootstrap removes stale user + sets password env."""
    email = e2e_user_email_for_tests()
    password = e2e_user_password_for_tests()
    if not password:
        pytest.fail("E2E user password missing after bootstrap (check session bootstrap errors).")
    username = e2e_username_for_tests()
    r = await client.post(
        "/api/admin/users",
        headers=_json_headers(admin_token),
        json={
            "email": email,
            "username": username,
            "password": password,
            "role": "user",
        },
    )
    if r.status_code in (200, 201):
        return email, password
    if r.status_code == 400 and "already exists" in (r.text or "").lower():
        return email, password
    pytest.fail(f"Could not ensure E2E user: {r.status_code} {r.text}")


async def _pick_scanners(client: httpx.AsyncClient) -> list[str]:
    """Enabled code scanners from the API."""
    response = await client.get("/api/scanners/?scan_type=code")
    if response.status_code != 200:
        return []
    scanners = response.json().get("scanners", [])
    selected: list[str] = []
    for scanner in scanners:
        if scanner.get("enabled"):
            name = scanner.get("name")
            if isinstance(name, str) and name.strip():
                selected.append(name.strip())
    return selected


async def _post_scan(
    client: httpx.AsyncClient, *, profile: str, scanner_names: list[str]
) -> httpx.Response:
    return await client.post(
        "/api/v1/scans/",
        json={
            "name": f"E2E profile {profile}",
            "description": f"Validate profile '{profile}'",
            "scan_type": "code",
            "target_url": TEST_REPO,
            "scanners": scanner_names,
            "config": {
                "scan_profile": profile,
                "collect_metadata": True,
            },
        },
    )


async def _start_scan_ok(
    client: httpx.AsyncClient, *, profile: str, scanner_names: list[str]
) -> str:
    response = await _post_scan(client, profile=profile, scanner_names=scanner_names)
    assert response.status_code in (200, 201), (
        f"Failed to start {profile} scan: {response.status_code} - {response.text}"
    )
    scan_id = response.json().get("id")
    assert isinstance(scan_id, str) and scan_id.strip(), "No scan id returned"
    return scan_id


async def _wait_terminal_status(
    client: httpx.AsyncClient, scan_id: str, *, wait_seconds: Optional[int] = None
) -> str:
    limit = SCAN_WAIT_TIMEOUT if wait_seconds is None else wait_seconds
    start = time.time()
    last_status = "unknown"
    while time.time() - start < limit:
        response = await client.get(f"/api/v1/scans/{scan_id}/status")
        assert response.status_code == 200, f"Status call failed: {response.text}"
        last_status = str(response.json().get("status", "unknown")).lower()
        if last_status in ("completed", "failed", "cancelled", "interrupted"):
            return last_status
        await asyncio.sleep(POLL_INTERVAL)
    pytest.fail(
        f"Scan {scan_id} did not reach terminal state within {limit}s (last status: {last_status}). "
        "If the worker uses priority queue, ensure worker image includes priority dequeue (scan_queue:priority). "
        "Raise scan_profiles.*.timeout in scanner/plugins/*/manifest.yaml if scans need more time."
    )


async def _full_pipeline_or_forbidden(
    client: httpx.AsyncClient,
    *,
    role: str,
    profile: str,
    scanner_names: list[str],
    allow_start: bool,
    guest_standard_message: bool = False,
) -> None:
    """If ``allow_start``: run scan to terminal + assert steps. Else assert HTTP 403."""
    response = await _post_scan(client, profile=profile, scanner_names=scanner_names)
    if not allow_start:
        assert response.status_code == 403, (
            f"{role} profile={profile}: expected 403, got {response.status_code} {response.text}"
        )
        if guest_standard_message:
            assert "exceeds allowed maximum" in (response.text or "").lower()
        return

    assert response.status_code in (200, 201), (
        f"{role} profile={profile}: {response.status_code} {response.text}"
    )
    scan_id = response.json().get("id")
    assert isinstance(scan_id, str) and scan_id.strip(), "No scan id returned"
    status = await _wait_terminal_status(client, scan_id)
    assert status in ("completed", "failed", "cancelled", "interrupted")
    steps_response = await client.get(f"/api/v1/scans/{scan_id}/steps")
    assert steps_response.status_code == 200, steps_response.text
    steps = steps_response.json().get("steps", [])
    step_names = {str(step.get("name", "")).strip() for step in steps}
    missing = [name for name in scanner_names if name not in step_names]
    assert not missing, (
        f"{role} profile={profile}: scanners not in steps: {missing}. "
        f"Step names: {sorted(step_names)}"
    )


# --- Full pipeline (slow): guest → user → admin; each parametrized over quick / standard / deep ---


@pytest.mark.asyncio
@pytest.mark.parametrize("profile", _PROFILES)
async def test_full_pipeline_1_guest_scan_profiles(
    guest_client: httpx.AsyncClient, profile: str
) -> None:
    """Guest: pipeline only for ``quick``; ``standard``/``deep`` must be rejected (403)."""
    scanner_names = await _pick_scanners(guest_client)
    if not scanner_names:
        pytest.skip("No enabled scanners available")
    await _full_pipeline_or_forbidden(
        guest_client,
        role="guest",
        profile=profile,
        scanner_names=scanner_names,
        allow_start=(profile == "quick"),
        guest_standard_message=(profile == "standard"),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("profile", _PROFILES)
async def test_full_pipeline_2_user_scan_profiles(profile: str) -> None:
    """User: pipeline for ``quick`` and ``standard``; ``deep`` → 403."""
    creds = _admin_creds()
    assert creds is not None, (
        "Bootstrap did not set admin credentials — use a fresh DB (docker compose down -v) "
        "and session bootstrap."
    )
    admin_email, admin_password = creds
    async with httpx.AsyncClient(
        base_url=BASE_URL, timeout=TIMEOUT, headers=_json_headers()
    ) as client:
        admin_token = await _login(client, admin_email, admin_password)
        user_email, user_password = await _ensure_test_user(client, admin_token)

    async with httpx.AsyncClient(
        base_url=BASE_URL, timeout=TIMEOUT, headers=_json_headers()
    ) as anon:
        scanner_names = await _pick_scanners(anon)
    if not scanner_names:
        pytest.skip("No enabled scanners available")

    async with httpx.AsyncClient(
        base_url=BASE_URL, timeout=TIMEOUT, headers=_json_headers()
    ) as login_client:
        user_r = await login_client.post(
            "/api/v1/auth/login",
            json={"email": user_email, "password": user_password},
        )
    if user_r.status_code == 403 and "verify" in (user_r.text or "").lower():
        pytest.skip(
            "E2E user cannot log in until email is verified; disable "
            "require_email_verification for this test or verify the test user."
        )
    assert user_r.status_code == 200, user_r.text
    user_token = user_r.json()["access_token"]

    async with httpx.AsyncClient(
        base_url=BASE_URL, timeout=TIMEOUT, headers=_json_headers(user_token)
    ) as user_client:
        await _full_pipeline_or_forbidden(
            user_client,
            role="user",
            profile=profile,
            scanner_names=scanner_names,
            allow_start=profile in ("quick", "standard"),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("profile", _PROFILES)
async def test_full_pipeline_3_admin_scan_profiles(profile: str) -> None:
    """Admin: full pipeline for ``quick``, ``standard``, and ``deep``."""
    creds = _admin_creds()
    assert creds is not None, (
        "Bootstrap did not set admin credentials — use a fresh DB (docker compose down -v) "
        "and session bootstrap."
    )
    admin_email, admin_password = creds
    async with httpx.AsyncClient(
        base_url=BASE_URL, timeout=TIMEOUT, headers=_json_headers()
    ) as client:
        token = await _login(client, admin_email, admin_password)
        scanner_names = await _pick_scanners(client)
    if not scanner_names:
        pytest.skip("No enabled scanners available")

    async with httpx.AsyncClient(
        base_url=BASE_URL, timeout=TIMEOUT, headers=_json_headers(token)
    ) as admin_client:
        await _full_pipeline_or_forbidden(
            admin_client,
            role="admin",
            profile=profile,
            scanner_names=scanner_names,
            allow_start=True,
        )


# --- RBAC (fast): same policy, no worker wait ---


@pytest.mark.asyncio
async def test_guest_scan_profile_rbac(guest_client: httpx.AsyncClient) -> None:
    scanner_names = await _pick_scanners(guest_client)
    if not scanner_names:
        pytest.skip("No enabled scanners available")

    r_quick = await _post_scan(guest_client, profile="quick", scanner_names=scanner_names)
    assert r_quick.status_code in (200, 201), r_quick.text

    r_std = await _post_scan(guest_client, profile="standard", scanner_names=scanner_names)
    assert r_std.status_code == 403, r_std.text
    assert "exceeds allowed maximum" in (r_std.text or "").lower()

    r_deep = await _post_scan(guest_client, profile="deep", scanner_names=scanner_names)
    assert r_deep.status_code == 403, r_deep.text


@pytest.mark.asyncio
async def test_user_scan_profile_rbac() -> None:
    creds = _admin_creds()
    assert creds is not None, (
        "Bootstrap did not set admin credentials — use a fresh DB (docker compose down -v) "
        "and session bootstrap."
    )
    admin_email, admin_password = creds
    async with httpx.AsyncClient(
        base_url=BASE_URL, timeout=TIMEOUT, headers=_json_headers()
    ) as client:
        admin_token = await _login(client, admin_email, admin_password)
        user_email, user_password = await _ensure_test_user(client, admin_token)

    async with httpx.AsyncClient(
        base_url=BASE_URL, timeout=TIMEOUT, headers=_json_headers()
    ) as anon:
        scanner_names = await _pick_scanners(anon)
    if not scanner_names:
        pytest.skip("No enabled scanners available")

    async with httpx.AsyncClient(
        base_url=BASE_URL, timeout=TIMEOUT, headers=_json_headers()
    ) as login_client:
        user_r = await login_client.post(
            "/api/v1/auth/login",
            json={"email": user_email, "password": user_password},
        )
    if user_r.status_code == 403 and "verify" in (user_r.text or "").lower():
        pytest.skip(
            "E2E user cannot log in until email is verified; disable "
            "require_email_verification for this test or verify the test user."
        )
    assert user_r.status_code == 200, user_r.text
    user_token = user_r.json()["access_token"]

    async with httpx.AsyncClient(
        base_url=BASE_URL, timeout=TIMEOUT, headers=_json_headers(user_token)
    ) as user_client:
        rq = await _post_scan(user_client, profile="quick", scanner_names=scanner_names)
        assert rq.status_code in (200, 201), rq.text
        rs = await _post_scan(user_client, profile="standard", scanner_names=scanner_names)
        assert rs.status_code in (200, 201), rs.text
        rd = await _post_scan(user_client, profile="deep", scanner_names=scanner_names)
        assert rd.status_code == 403, rd.text


@pytest.mark.asyncio
async def test_admin_scan_profile_rbac() -> None:
    creds = _admin_creds()
    assert creds is not None, (
        "Bootstrap should set admin credentials (fresh DB: docker compose down -v)."
    )
    admin_email, admin_password = creds
    async with httpx.AsyncClient(
        base_url=BASE_URL, timeout=TIMEOUT, headers=_json_headers()
    ) as client:
        token = await _login(client, admin_email, admin_password)
        scanner_names = await _pick_scanners(client)
    if not scanner_names:
        pytest.skip("No enabled scanners available")

    async with httpx.AsyncClient(
        base_url=BASE_URL, timeout=TIMEOUT, headers=_json_headers(token)
    ) as admin_client:
        for profile in _PROFILES:
            r = await _post_scan(admin_client, profile=profile, scanner_names=scanner_names)
            assert r.status_code in (200, 201), f"{profile}: {r.status_code} {r.text}"
