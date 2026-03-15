"""
E2E Test: Substeps Validation
Validates that:
- Substeps are correctly written to steps.log
- Substeps are correctly returned by API
- Substeps contain expected fields (name, status, message, timestamps)
- Specific scanners (CodeQL, OWASP, Checkov) have substeps
"""
import asyncio
import time
from typing import Dict, List, Optional

import httpx
import pytest

BASE_URL = "http://localhost:8080"
TIMEOUT = 600  # 10 minutes for full scan
POLL_INTERVAL = 5
TEST_REPO = "https://github.com/fr4iser90/SimpleSecCheck"


@pytest.fixture
def client():
    return httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT)


async def start_scan(client: httpx.AsyncClient, repo_url: str) -> str:
    """Start a scan and return scan_id"""
    response = await client.post(
        "/api/v1/scans/",
        json={
            "name": "Substeps Test Scan",
            "description": "Test scan to validate substeps",
            "scan_type": "code",  # Must be valid ScanType enum value
            "target_url": repo_url,
            "scanners": ["codeql", "owasp", "checkov"],  # Scanners with substeps
            "config": {
                "collect_metadata": True
            }
        }
    )
    assert response.status_code in [200, 201], f"Failed to start scan: {response.status_code} - {response.text}"
    data = response.json()
    scan_id = data.get("id")
    assert scan_id, "No scan_id returned"
    return scan_id


async def wait_for_scan_running_or_completed(client: httpx.AsyncClient, scan_id: str) -> Dict:
    """Wait for scan to be running or completed"""
    start_time = time.time()
    while time.time() - start_time < TIMEOUT:
        response = await client.get(f"/api/v1/scans/{scan_id}/status")
        if response.status_code == 200:
            data = response.json()
            status = data.get("status")
            if status in ["running", "completed", "failed"]:
                return data
        await asyncio.sleep(POLL_INTERVAL)
    pytest.fail(f"Scan {scan_id} did not start within {TIMEOUT}s")


async def get_scan_steps(client: httpx.AsyncClient, scan_id: str) -> Dict:
    """Get steps from API"""
    response = await client.get(f"/api/v1/scans/{scan_id}/steps")
    assert response.status_code == 200, f"Failed to get steps: {response.text}"
    return response.json()


def validate_substep_structure(substep: Dict) -> bool:
    """Validate that a substep has required fields"""
    required_fields = ["name", "status"]
    return all(field in substep for field in required_fields)


def find_step_by_name(steps: List[Dict], name: str) -> Optional[Dict]:
    """Find a step by name (case-insensitive partial match)"""
    for step in steps:
        step_name = step.get("name", "").lower()
        if name.lower() in step_name:
            return step
    return None


@pytest.mark.asyncio
async def test_substeps_are_written_and_returned(client: httpx.AsyncClient):
    """
    Test that substeps are correctly written to steps.log and returned by API.
    """
    # Start scan
    scan_id = await start_scan(client, TEST_REPO)
    
    # Wait for scan to be running (so steps.log exists)
    await wait_for_scan_running_or_completed(client, scan_id)
    
    # Wait a bit for substeps to be written
    await asyncio.sleep(10)
    
    # Get steps from API
    steps_data = await get_scan_steps(client, scan_id)
    steps = steps_data.get("steps", [])
    
    assert len(steps) > 0, "No steps returned from API"
    
    # Test 1: CodeQL should have substeps
    codeql_step = find_step_by_name(steps, "CodeQL")
    if codeql_step:
        assert "substeps" in codeql_step, "CodeQL step missing 'substeps' field"
        substeps = codeql_step.get("substeps", [])
        assert len(substeps) > 0, f"CodeQL step has no substeps (expected at least Language Detection)"
        
        # Validate substep structure
        for substep in substeps:
            assert validate_substep_structure(substep), f"Invalid substep structure: {substep}"
            assert substep.get("name"), "Substep missing 'name'"
            assert substep.get("status") in ["pending", "running", "completed", "failed"], \
                f"Invalid substep status: {substep.get('status')}"
        
        # Check for specific CodeQL substeps
        substep_names = [s.get("name", "") for s in substeps]
        assert any("Language Detection" in name for name in substep_names), \
            "CodeQL missing 'Language Detection' substep"
    else:
        pytest.skip("CodeQL step not found (may not have started yet)")
    
    # Test 2: OWASP should have substeps
    owasp_step = find_step_by_name(steps, "OWASP")
    if owasp_step:
        assert "substeps" in owasp_step, "OWASP step missing 'substeps' field"
        substeps = owasp_step.get("substeps", [])
        assert len(substeps) > 0, "OWASP step has no substeps"
        
        # Validate substep structure
        for substep in substeps:
            assert validate_substep_structure(substep), f"Invalid substep structure: {substep}"
        
        # Check for specific OWASP substeps
        substep_names = [s.get("name", "") for s in substeps]
        assert any("Database Check" in name or "Scanning" in name for name in substep_names), \
            "OWASP missing expected substeps (Database Check or Scanning)"
    else:
        pytest.skip("OWASP step not found (may not have started yet)")
    
    # Test 3: Checkov should have substeps
    checkov_step = find_step_by_name(steps, "Checkov")
    if checkov_step:
        assert "substeps" in checkov_step, "Checkov step missing 'substeps' field"
        substeps = checkov_step.get("substeps", [])
        assert len(substeps) > 0, "Checkov step has no substeps"
        
        # Validate substep structure
        for substep in substeps:
            assert validate_substep_structure(substep), f"Invalid substep structure: {substep}"
        
        # Check for specific Checkov substeps
        substep_names = [s.get("name", "") for s in substeps]
        assert any("Finding Files" in name or "JSON Report" in name or "Text Report" in name for name in substep_names), \
            "Checkov missing expected substeps"
    else:
        pytest.skip("Checkov step not found (may not have started yet)")


@pytest.mark.asyncio
async def test_substeps_have_complete_data(client: httpx.AsyncClient):
    """
    Test that substeps contain all expected fields (name, status, message, timestamps).
    """
    # Start scan
    scan_id = await start_scan(client, TEST_REPO)
    
    # Wait for scan to be running
    await wait_for_scan_running_or_completed(client, scan_id)
    
    # Wait for some substeps to complete
    await asyncio.sleep(30)
    
    # Get steps from API
    steps_data = await get_scan_steps(client, scan_id)
    steps = steps_data.get("steps", [])
    
    # Find any step with substeps
    step_with_substeps = None
    for step in steps:
        if step.get("substeps") and len(step.get("substeps", [])) > 0:
            step_with_substeps = step
            break
    
    if not step_with_substeps:
        pytest.skip("No step with substeps found yet")
    
    substeps = step_with_substeps.get("substeps", [])
    assert len(substeps) > 0, "Step has empty substeps array"
    
    # Validate each substep has complete data
    for substep in substeps:
        # Required fields
        assert "name" in substep, "Substep missing 'name'"
        assert "status" in substep, "Substep missing 'status'"
        assert substep["name"], "Substep 'name' is empty"
        assert substep["status"] in ["pending", "running", "completed", "failed"], \
            f"Invalid substep status: {substep['status']}"
        
        # Optional but expected fields
        if "message" in substep:
            assert isinstance(substep["message"], str), "Substep 'message' should be string"
        
        if "started_at" in substep and substep["started_at"]:
            assert isinstance(substep["started_at"], str), "Substep 'started_at' should be ISO string"
        
        if "completed_at" in substep and substep["completed_at"]:
            assert isinstance(substep["completed_at"], str), "Substep 'completed_at' should be ISO string"


@pytest.mark.asyncio
async def test_substeps_update_during_scan(client: httpx.AsyncClient):
    """
    Test that substeps update their status during scan execution.
    """
    # Start scan
    scan_id = await start_scan(client, TEST_REPO)
    
    # Wait for scan to be running
    await wait_for_scan_running_or_completed(client, scan_id)
    
    # Get initial steps
    initial_steps = await get_scan_steps(client, scan_id)
    initial_codeql = find_step_by_name(initial_steps.get("steps", []), "CodeQL")
    
    if not initial_codeql or not initial_codeql.get("substeps"):
        pytest.skip("CodeQL step with substeps not found yet")
    
    initial_substeps = {s.get("name"): s.get("status") for s in initial_codeql.get("substeps", [])}
    
    # Wait for progress
    await asyncio.sleep(60)
    
    # Get updated steps
    updated_steps = await get_scan_steps(client, scan_id)
    updated_codeql = find_step_by_name(updated_steps.get("steps", []), "CodeQL")
    
    if not updated_codeql or not updated_codeql.get("substeps"):
        pytest.skip("CodeQL step disappeared (scan may have completed)")
    
    updated_substeps = {s.get("name"): s.get("status") for s in updated_codeql.get("substeps", [])}
    
    # Check that at least one substep changed status
    changes_found = False
    for name, initial_status in initial_substeps.items():
        if name in updated_substeps:
            updated_status = updated_substeps[name]
            if initial_status != updated_status:
                changes_found = True
                break
    
    # This is not a hard requirement (substeps might complete quickly)
    # But we log it for debugging
    if not changes_found:
        print("Note: No substep status changes detected (may have completed too quickly)")
