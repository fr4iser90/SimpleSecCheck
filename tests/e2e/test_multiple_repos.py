"""
E2E Test: Multiple Repository Scans
Tests the complete scan workflow with multiple repositories.
"""
import pytest
import httpx
import json
import time
import asyncio
from pathlib import Path
from typing import List, Dict

# Test configuration
BASE_URL = "http://localhost:8080"
TIMEOUT = 300  # 5 minutes per scan
POLL_INTERVAL = 5  # Check status every 5 seconds


@pytest.fixture
def test_repos() -> List[Dict]:
    """Load test repositories from fixtures"""
    fixtures_path = Path(__file__).parent.parent / "fixtures" / "repos.json"
    with open(fixtures_path) as f:
        data = json.load(f)
    return data["test_repositories"]


@pytest.fixture
def client():
    """HTTP client for API calls"""
    return httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT)


@pytest.mark.asyncio
async def test_multiple_repo_scans(client: httpx.AsyncClient, test_repos: List[Dict]):
    """
    Test scanning multiple repositories sequentially (queue → completion → results).
    """
    scan_results = []
    
    for repo in test_repos:
        print(f"\n{'='*60}")
        print(f"Testing repository: {repo['name']}")
        print(f"URL: {repo['url']}")
        print(f"{'='*60}")
        
        # Start scan
        response = await client.post(
            "/api/scan/start",
            json={
                "type": "code",
                "target": repo["url"],
                "git_branch": repo.get("branch", "main"),
                "collect_metadata": True
            }
        )
        
        assert response.status_code == 200, f"Failed to start scan: {response.text}"
        scan_data = response.json()
        scan_id = scan_data.get("scan_id")
        
        assert scan_id is not None, "No scan_id returned"
        print(f"✓ Scan started: {scan_id}")
        
        # Wait for scan to complete
        print(f"⏳ Waiting for scan to complete (max {TIMEOUT}s)...")
        start_time = time.time()
        completed = False
        actual_scan_id = None  # Will be set from queue item when scan completes
        
        while time.time() - start_time < TIMEOUT:
            # Check queue status to get actual scan_id
            queue_status_response = await client.get(f"/api/queue/{scan_id}/status")
            if queue_status_response.status_code == 200:
                queue_status = queue_status_response.json()
                if queue_status.get("status") == "completed":
                    actual_scan_id = queue_status.get("scan_id")
                    if actual_scan_id:
                        print(f"✓ Scan {scan_id} completed with scan_id: {actual_scan_id}")
                        completed = True
                        break
                elif queue_status.get("status") == "failed":
                    error_msg = queue_status.get("error", "Unknown error")
                    pytest.fail(f"Scan {scan_id} failed: {error_msg}")
            
            await asyncio.sleep(POLL_INTERVAL)
            print(f"  Still running... ({int(time.time() - start_time)}s)")
        
        if not completed:
            pytest.fail(f"Scan {scan_id} did not complete within {TIMEOUT}s")
        
        if not actual_scan_id:
            pytest.fail(f"Scan {scan_id} completed but no scan_id found in queue item")
        
        # Verify results: prefer per-scan report URL if it works, else global results list
        report_response = await client.get(f"/api/results/{actual_scan_id}/report")
        if report_response.status_code == 200:
            pass
        else:
            results_response = await client.get("/api/results")
            assert results_response.status_code == 200
            results = results_response.json()
            scans = results.get("scans", [])
            scan_found = any(actual_scan_id in scan.get("id", "") for scan in scans)
            assert scan_found, f"Scan {actual_scan_id} not found in results"
        
        print(f"✓ Results found for scan {scan_id}")
        
        scan_results.append({
            "repo": repo["name"],
            "scan_id": scan_id,
            "success": True
        })
        
        # Small delay between scans
        await asyncio.sleep(2)
    
    # Summary
    print(f"\n{'='*60}")
    print("Test Summary:")
    print(f"{'='*60}")
    for result in scan_results:
        status = "✓ PASS" if result["success"] else "✗ FAIL"
        print(f"{status} - {result['repo']} ({result['scan_id']})")
    print(f"{'='*60}")
    
    assert len(scan_results) == len(test_repos), "Not all scans completed"
    assert all(r["success"] for r in scan_results), "Some scans failed"


@pytest.mark.asyncio
async def test_queue_functionality(client: httpx.AsyncClient, test_repos: List[Dict]):
    """
    Test queue functionality (requires server with queue enabled).
    Verifies that scans are added to queue and processed correctly.
    """
    q = await client.get("/api/queue")
    if q.status_code != 200:
        pytest.skip("Queue API not available on this stack")

    # Get queue status
    queue_response = await client.get("/api/queue")
    assert queue_response.status_code == 200
    
    queue = queue_response.json()
    initial_length = len(queue.get("items", []))
    
    print(f"Initial queue length: {initial_length}")
    
    # Add multiple scans to queue
    scan_ids = []
    for repo in test_repos[:2]:  # Test with first 2 repos
        response = await client.post(
            "/api/scan/start",
            json={
                "type": "code",
                "target": repo["url"],
                "git_branch": repo.get("branch", "main"),
                "collect_metadata": True
            }
        )
        
        assert response.status_code == 200
        scan_data = response.json()
        scan_id = scan_data.get("scan_id")
        scan_ids.append(scan_id)
        print(f"✓ Added scan to queue: {scan_id}")
    
    # Check queue length increased
    queue_response = await client.get("/api/queue")
    assert queue_response.status_code == 200
    
    queue = queue_response.json()
    new_length = len(queue.get("items", []))
    
    print(f"New queue length: {new_length}")
    assert new_length >= initial_length + len(scan_ids), "Queue length did not increase"
    
    # Wait for scans to be processed
    print("⏳ Waiting for queue to process scans...")
    await asyncio.sleep(30)  # Give queue time to process
    
    # Check "My Scans" endpoint
    my_scans_response = await client.get("/api/queue/my-scans")
    assert my_scans_response.status_code == 200
    
    my_scans = my_scans_response.json()
    print(f"✓ Found {len(my_scans.get('scans', []))} scans in 'My Scans'")


if __name__ == "__main__":
    import asyncio
    pytest.main([__file__, "-v", "-s"])
