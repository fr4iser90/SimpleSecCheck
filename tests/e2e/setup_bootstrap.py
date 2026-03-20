"""
Bootstrap a fresh SimpleSecCheck instance for E2E scan-profile tests.

Uses ``tests.e2e.e2e_constants.E2E_API_BASE_URL`` (FastAPI backend, not nginx :80).

If setup is incomplete: setup token **only** from ``docker compose logs backend`` (last
``Setup Token:`` line). Then ``/api/setup/initialize`` with generated admin credentials,
``auth_mode: free``, and provisioning of the synthetic E2E scan user.

If setup is **already** complete: raises — use ``docker compose down -v`` and a fresh stack
so the wizard can run. No admin credentials via environment variables.

Session state: ``_bootstrap_state`` (in-process), not ``os.environ``.
"""
from __future__ import annotations

import asyncio
import re
import secrets
import string
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional, Tuple

import httpx

from tests.e2e.e2e_constants import (
    E2E_API_BASE_URL,
    E2E_BOOTSTRAP_WAIT_S,
    E2E_COMPOSE_FILE,
)

# In-process credentials after successful bootstrap (tests read via helpers below).
_bootstrap_state: dict[str, str] = {}

# Short per-request timeouts so a dead host fails fast; POST verify/initialize may need longer.
_BOOTSTRAP_HTTP_TIMEOUT = httpx.Timeout(60.0, connect=5.0)
_BOOTSTRAP_POLL_TIMEOUT = httpx.Timeout(20.0, connect=5.0)


def _blog(msg: str) -> None:
    print(f"[e2e-bootstrap] {msg}", file=sys.stderr, flush=True)


def _bootstrap_request_headers() -> dict[str, str]:
    """Stable User-Agent + JSON; avoids looking like anonymous scripted hammering."""
    return {
        "User-Agent": "SimpleSecCheck-E2E-Bootstrap/1.0",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

# Stable synthetic identity (not secret); password is always generated per session.
_DEFAULT_E2E_USER_EMAIL = "e2e_scan_profile_user@example.com"

_TOKEN_PATTERN = re.compile(r"Setup Token:\s+([a-f0-9]{64})", re.IGNORECASE)


def _generate_strong_password(length: int = 24) -> str:
    """Meets setup-wizard rules: >=8, upper, lower, digit."""
    if length < 12:
        length = 12
    rng = secrets.SystemRandom()
    required = [
        rng.choice(string.ascii_uppercase),
        rng.choice(string.ascii_lowercase),
        rng.choice(string.digits),
    ]
    alphabet = string.ascii_letters + string.digits
    rest = [rng.choice(alphabet) for _ in range(length - len(required))]
    chars = required + rest
    rng.shuffle(chars)
    return "".join(chars)


def _generate_bootstrap_admin_email() -> str:
    return f"ssc-bootstrap-{secrets.token_hex(8)}@example.com"


def _generate_bootstrap_admin_username() -> str:
    return f"adm_{secrets.token_hex(8)}"


def _e2e_user_email() -> str:
    return (_bootstrap_state.get("user_email") or _DEFAULT_E2E_USER_EMAIL).strip()


def _username_from_email(email: str) -> str:
    local = email.split("@", 1)[0]
    u = "".join(c for c in local if c.isalnum() or c in "_-")
    if len(u) < 3:
        u = "e2e_" + secrets.token_hex(4)
    return u[:100]


def _extract_setup_token_from_logs(logs: str) -> Optional[str]:
    """Use the *last* token in the buffer — logs often contain older tokens from prior restarts."""
    matches = list(_TOKEN_PATTERN.finditer(logs))
    if not matches:
        return None
    return matches[-1].group(1).lower()


def _docker_backend_logs(
    project_dir: Path,
    compose_file: str,
    tail: int = 1500,
) -> str:
    cf = project_dir / compose_file
    cmd = [
        "docker",
        "compose",
        "-f",
        str(cf),
        "logs",
        "--tail",
        str(tail),
        "--timestamps",
        "backend",
    ]
    try:
        r = subprocess.run(
            cmd,
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=90,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    return (r.stdout or "") + (r.stderr or "")


def _poll_setup_token_from_docker(
    project_dir: Path,
    compose_file: str,
    *,
    attempts: int = 30,
    delay_s: float = 2.0,
) -> str:
    """Token source is exclusively ``docker compose logs backend`` — never process env."""
    for attempt in range(attempts):
        logs = _docker_backend_logs(project_dir, compose_file)
        tok = _extract_setup_token_from_logs(logs)
        if tok:
            return tok
        if attempt == 0 or attempt == attempts - 1:
            _blog(
                f"no Setup Token in docker logs yet ({attempt + 1}/{attempts}); "
                f"compose file={compose_file!r} cwd={project_dir!s}"
            )
        time.sleep(delay_s)
    raise RuntimeError(
        "Could not read setup token from `docker compose -f "
        f"{compose_file} logs backend` (expected a line `Setup Token: <64 hex>`). "
        "Start the stack from the repository root (same as tests), e.g. "
        "`docker compose up --build`. Compose file is `e2e_constants.E2E_COMPOSE_FILE`."
    )


async def _wait_http_ready(client: httpx.AsyncClient, *, timeout_s: float = 180.0) -> None:
    deadline = time.monotonic() + timeout_s
    last_err: Optional[str] = None
    _blog(f"waiting for GET /api/health at {client.base_url!s} …")
    while time.monotonic() < deadline:
        try:
            r = await client.get("/api/health", timeout=_BOOTSTRAP_POLL_TIMEOUT)
            if r.status_code == 200:
                _blog("API health OK")
                return
            last_err = f"health {r.status_code}"
        except Exception as e:
            last_err = str(e)
        await asyncio.sleep(2.0)
    raise RuntimeError(f"Backend not reachable at {client.base_url!s} ({last_err})")


async def _wait_dependencies_ready(client: httpx.AsyncClient, *, timeout_s: float = 180.0) -> None:
    """
    Wait until PostgreSQL and Redis report healthy. Uses GET /api/setup/health (setup
    middleware allows /api/setup/* before the wizard completes; /health/detailed does not).
    E2E_API_BASE_URL must be the FastAPI backend (e.g. :8080), not nginx :80 alone.
    """
    deadline = time.monotonic() + timeout_s
    h = _bootstrap_request_headers()
    _blog("waiting for DB + Redis (GET /api/setup/health) …")
    while time.monotonic() < deadline:
        try:
            r = await client.get("/api/setup/health", headers=h, timeout=_BOOTSTRAP_POLL_TIMEOUT)
            if r.status_code != 200:
                await asyncio.sleep(1.0)
                continue
            data = r.json()
            db_ok = data.get("database") == "connected"
            redis_ok = data.get("redis") == "connected"
            if db_ok and redis_ok:
                _blog("database and redis ready")
                return
        except Exception:
            pass
        await asyncio.sleep(1.0)
    raise RuntimeError(
        f"Timeout waiting for PostgreSQL and Redis via GET /api/setup/health at {client.base_url!s}. "
        "Use E2E_API_BASE_URL (FastAPI backend, e.g. http://localhost:8080), "
        "not the nginx frontend on :80."
    )


async def _verify_token(client: httpx.AsyncClient, token: str) -> str:
    """
    Match setup-wizard pacing: backend SetupRateLimiter allows only a few POSTs/min per IP
    before 429 + BRUTE_FORCE_ATTEMPT. Do not rapid-fire verify (old bootstrap used 12×/3s).
    """
    last: Optional[str] = None
    base_h = _bootstrap_request_headers()
    # At most 4 POSTs — limiter bans after 5 increments in the rolling minute window.
    max_attempts = 4
    for attempt in range(max_attempts):
        r = await client.post(
            "/api/setup/verify",
            headers={**base_h, "X-Setup-Token": token},
            json={},
        )
        if r.status_code == 200:
            data = r.json()
            sid = data.get("session_id")
            if isinstance(sid, str) and sid.strip():
                return sid.strip()
            raise RuntimeError("verify returned 200 but no session_id")
        last = f"{r.status_code} {r.text}"
        if r.status_code == 429:
            raise RuntimeError(
                "POST /api/setup/verify returned 429 (setup rate limit / ban). "
                "Wait ~1 minute or clear Redis keys setup:rate:* and setup:ban:* for your IP, then retry."
            )
        body = (r.text or "").lower()
        # Only retry while DB/token row is not ready — same as integration wizard.
        if (
            r.status_code == 400
            and "no setup token available" in body
            and attempt < max_attempts - 1
        ):
            _blog(
                f"setup verify: DB not ready yet ({attempt + 1}/{max_attempts}), sleeping 12s …"
            )
            await asyncio.sleep(12.0)
            continue
        raise RuntimeError(f"Setup token verify failed: {last}")


async def _initialize(
    client: httpx.AsyncClient,
    session_id: str,
    *,
    admin_username: str,
    admin_email: str,
    admin_password: str,
) -> None:
    system_config: dict[str, Any] = {
        "auth_mode": "free",
        "max_concurrent_jobs": 3,
        "require_email_verification": False,
    }
    r = await client.post(
        "/api/setup/initialize",
        headers={**_bootstrap_request_headers(), "X-Setup-Session": session_id},
        json={
            "admin_user": {
                "username": admin_username,
                "email": admin_email,
                "password": admin_password,
            },
            "system_config": system_config,
        },
    )
    if r.status_code != 200:
        raise RuntimeError(f"setup initialize failed: {r.status_code} {r.text}")
    data = r.json()
    if not data.get("success"):
        raise RuntimeError(f"setup initialize not successful: {data}")


async def _try_login(
    client: httpx.AsyncClient, email: str, password: str
) -> bool:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return r.status_code == 200


async def _admin_access_token(
    client: httpx.AsyncClient, email: str, password: str
) -> str:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    if r.status_code != 200:
        raise RuntimeError(f"Admin login failed: {r.status_code} {r.text}")
    data = r.json()
    tok = data.get("access_token")
    if not isinstance(tok, str) or not tok.strip():
        raise RuntimeError("Login response missing access_token")
    return tok.strip()


async def _provision_e2e_scan_user(
    client: httpx.AsyncClient,
    *,
    admin_email: str,
    admin_password: str,
) -> None:
    """
    Set default E2E user email and a fresh password in ``_bootstrap_state``.
    Removes an existing user with that email so tests can POST /admin/users again.
    """
    token = await _admin_access_token(client, admin_email, admin_password)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    target_email = _DEFAULT_E2E_USER_EMAIL
    _bootstrap_state["user_email"] = target_email

    r_list = await client.get("/api/admin/users", params={"limit": 1000}, headers=headers)
    if r_list.status_code != 200:
        raise RuntimeError(f"List users failed: {r_list.status_code} {r_list.text}")
    for row in r_list.json():
        if isinstance(row, dict) and row.get("email") == target_email:
            uid = row.get("id")
            if uid:
                r_del = await client.delete(f"/api/admin/users/{uid}", headers=headers)
                if r_del.status_code not in (200, 204):
                    raise RuntimeError(
                        f"Could not remove stale E2E user {target_email!r}: "
                        f"{r_del.status_code} {r_del.text}"
                    )

    user_pw = _generate_strong_password()
    _bootstrap_state["user_password"] = user_pw


def e2e_admin_credentials() -> Optional[tuple[str, str]]:
    """Admin email/password after successful ``run_session_bootstrap`` (in-process only)."""
    e = _bootstrap_state.get("admin_email", "").strip()
    p = _bootstrap_state.get("admin_password", "").strip()
    if e and p:
        return e, p
    return None


async def ensure_scan_profiles_e2e_ready(
    base_url: str,
    project_dir: Path,
    *,
    compose_file: str = E2E_COMPOSE_FILE,
) -> Tuple[str, str]:
    """
    Wizard path on fresh DB: returns (admin_email, admin_password); fills ``_bootstrap_state``.
    If ``setup_complete`` is already true: raises — run ``docker compose down -v`` and retry.
    """
    _bootstrap_state.clear()

    base = base_url.rstrip("/")
    cf = compose_file
    timeout = E2E_BOOTSTRAP_WAIT_S

    async with httpx.AsyncClient(base_url=base, timeout=_BOOTSTRAP_HTTP_TIMEOUT) as client:
        await _wait_http_ready(client, timeout_s=timeout)

        st = await client.get("/api/setup/status", timeout=_BOOTSTRAP_HTTP_TIMEOUT)
        if st.status_code != 200:
            raise RuntimeError(f"setup status failed: {st.status_code} {st.text}")
        status = st.json()
        setup_complete = bool(status.get("setup_complete"))
        _blog(f"setup_complete={setup_complete}")

        if not setup_complete:
            await _wait_dependencies_ready(client, timeout_s=min(timeout, 180.0))
            admin_email = _generate_bootstrap_admin_email()
            admin_password = _generate_strong_password()
            admin_username = _generate_bootstrap_admin_username()

            _blog("fetching setup token from docker compose logs …")
            token = _poll_setup_token_from_docker(project_dir, cf)
            _blog(
                "waiting 12s before first /api/setup/verify (setup wizard pacing, avoids rate limit) …"
            )
            await asyncio.sleep(12.0)
            _blog("verifying setup token …")
            try:
                session_id = await _verify_token(client, token)
            except RuntimeError as e:
                msg = str(e).lower()
                if "invalid" not in msg or "token" not in msg:
                    raise
                tok2 = _extract_setup_token_from_logs(
                    _docker_backend_logs(project_dir, cf, tail=2500)
                )
                if not tok2 or tok2 == token:
                    raise
                _blog(
                    "verify rejected token; retrying with latest Setup Token from docker logs …"
                )
                await asyncio.sleep(3.0)
                session_id = await _verify_token(client, tok2)
            _blog("running /api/setup/initialize …")
            await _initialize(
                client,
                session_id,
                admin_username=admin_username,
                admin_email=admin_email,
                admin_password=admin_password,
            )
            _bootstrap_state["admin_email"] = admin_email
            _bootstrap_state["admin_password"] = admin_password
            _blog("provisioning E2E scan user …")
            await _provision_e2e_scan_user(
                client, admin_email=admin_email, admin_password=admin_password
            )
            _blog("bootstrap finished (fresh setup)")
            return admin_email, admin_password

        raise RuntimeError(
            "Setup is already complete (existing database). E2E expects a fresh install. "
            "From the repository root: docker compose down -v && docker compose up --build "
            "then run pytest again."
        )


def run_session_bootstrap() -> None:
    """Sync entry for pytest session fixtures."""
    base = E2E_API_BASE_URL.rstrip("/")
    project_dir = Path(__file__).resolve().parent.parent.parent
    asyncio.run(ensure_scan_profiles_e2e_ready(base, project_dir))


def e2e_user_email_for_tests() -> str:
    """Synthetic E2E user email (after bootstrap)."""
    return (_bootstrap_state.get("user_email") or _DEFAULT_E2E_USER_EMAIL).strip()


def e2e_user_password_for_tests() -> str:
    """Password generated in bootstrap for the synthetic E2E user."""
    return _bootstrap_state.get("user_password", "").strip()


def e2e_username_for_tests() -> str:
    return _username_from_email(e2e_user_email_for_tests())
