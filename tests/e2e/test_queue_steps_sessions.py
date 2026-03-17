"""
E2E Test: Queue, Steps, and Session Isolation
Validates that:
- queue_id transitions to scan_id
- steps are written beyond Git Clone
- session isolation hides scans from other sessions
"""
import asyncio
import time
from typing import Dict, Optional

import httpx
import pytest

BASE_URL = "http://localhost:8080"
TIMEOUT = 300
POLL_INTERVAL = 5


@pytest.fixture
def client():
    return httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT)


@pytest.fixture
def client_two():
    return httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT)


async def get_session_id(client: httpx.AsyncClient) -> Optional[str]:
    response = await client.get("/api/session")
    if response.status_code != 200:
        return None
    data = response.json()
    return data.get("session_id")


async def start_scan(client: httpx.AsyncClient, repo_url: str, branch: str = "main") -> str:
    response = await client.post(
        "/api/scan/start",
        json={
            "type": "code",
            "target": repo_url,
            "git_branch": branch,
            "collect_metadata": True,
        },
    )
    assert response.status_code == 200, f"Failed to start scan: {response.text}"
    scan_id = response.json().get("scan_id")
    assert scan_id, "No scan_id returned"
    return scan_id


async def wait_for_scan_completion(client: httpx.AsyncClient, queue_id: str) -> Dict:
    start_time = time.time()
    while time.time() - start_time < TIMEOUT:
        response = await client.get(f"/api/queue/{queue_id}/status")
        if response.status_code == 200:
            data = response.json()
            status = data.get("status")
            if status == "completed":
                return data
            if status == "failed":
                pytest.fail(f"Scan failed: {data}")
        await asyncio.sleep(POLL_INTERVAL)
    pytest.fail(f"Scan {queue_id} did not complete within {TIMEOUT}s")


@pytest.mark.asyncio
async def test_queue_steps_and_session_isolation(client: httpx.AsyncClient, client_two: httpx.AsyncClient):
    """
    End-to-end validation of queue -> scan_id transition, steps logging, and session isolation.
    """
    repo_url = "https://github.com/fr4iser90/PIDEA"

    # Ensure both clients have sessions
    session_one = await get_session_id(client)
    session_two = await get_session_id(client_two)
    if not session_one or not session_two:
        pytest.skip("Session endpoint did not return session IDs; run with session support")
    assert session_one != session_two, "Expected separate sessions for isolation test"

    # Start scan (client one)
    queue_id = await start_scan(client, repo_url)

    # Wait for completion and retrieve scan_id/results_dir
    queue_item = await wait_for_scan_completion(client, queue_id)
    scan_id = queue_item.get("scan_id")
    assert scan_id, "Queue item completed but scan_id missing"

    # Verify steps are present (beyond Git Clone)
    steps_response = await client.get("/api/scan/logs")
    assert steps_response.status_code == 200
    steps_lines = steps_response.json().get("lines", [])
    assert steps_lines, "No steps log entries returned"
    # Validate that we have more than just Git Clone in steps
    assert any("Semgrep" in line or "Trivy" in line or "CodeQL" in line for line in steps_lines), (
        "Steps log does not show scanner steps beyond Git Clone"
    )

    # Verify report access for session one
    report_response = await client.get(f"/api/my-results/{scan_id}/report")
    if report_response.status_code == 403:
        pytest.skip("Report access requires production session access")
    assert report_response.status_code == 200, "Session owner should access report"

    # Verify report access is denied for session two (isolation)
    report_response_two = await client_two.get(f"/api/my-results/{scan_id}/report")
    assert report_response_two.status_code in (401, 403), "Other session should not access report"
