"""
Container Service
Handles Docker container management for scans
"""
import subprocess  # nosec B404 - Used safely with hardcoded docker commands, timeouts, and shell=False
import os
from typing import List


def stop_running_containers(current_scan: dict) -> List[str]:
    """Stop all running scanner containers"""
    stopped_containers = []
    
    # Method 1: Stop containers tracked in current_scan
    # Security: Hardcoded docker command, container_id validated, timeout set
    for container_id in current_scan.get("container_ids", []):
        if container_id:
            try:
                result = subprocess.run(  # nosec B603, B607
                    ["docker", "stop", container_id],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    stopped_containers.append(container_id)
                    print(f"[Stop Containers] Stopped tracked container: {container_id}")
            except Exception as e:
                print(f"[Stop Containers] Error stopping container {container_id}: {e}")
    
    # Method 2: Find and stop any running scanner containers by name pattern
    # Security: Hardcoded docker command, no user input, timeout set
    try:
        # Find containers with "scanner" in name or from docker-compose
        result = subprocess.run(  # nosec B603, B607
            ["docker", "ps", "--filter", "name=scanner", "--format", "{{.ID}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            container_ids = [cid.strip() for cid in result.stdout.strip().split('\n') if cid.strip()]
            for container_id in container_ids:
                if container_id not in stopped_containers:
                    try:
                        # Security: Hardcoded docker command, container_id from docker ps, timeout set
                        subprocess.run(  # nosec B603, B607
                            ["docker", "stop", container_id],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        stopped_containers.append(container_id)
                        print(f"[Stop Containers] Stopped container: {container_id}")
                    except Exception as e:
                        print(f"[Stop Containers] Error stopping container {container_id}: {e}")
    except Exception as e:
        print(f"[Stop Containers] Error finding containers: {e}")
    
    # Method 3: Try to stop docker-compose containers
    # Security: Hardcoded docker command, compose_project from env with safe default, timeout set
    try:
        # Get docker-compose project name from environment or use default
        compose_project = os.getenv("COMPOSE_PROJECT_NAME", "simpleseccheck")
        result = subprocess.run(  # nosec B603, B607
            ["docker", "ps", "--filter", f"label=com.docker.compose.project={compose_project}", "--format", "{{.ID}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            container_ids = [cid.strip() for cid in result.stdout.strip().split('\n') if cid.strip()]
            for container_id in container_ids:
                if container_id not in stopped_containers:
                    try:
                        # Security: Hardcoded docker command, container_id from docker ps, timeout set
                        subprocess.run(  # nosec B603, B607
                            ["docker", "stop", container_id],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        stopped_containers.append(container_id)
                        print(f"[Stop Containers] Stopped docker-compose container: {container_id}")
                    except Exception as e:
                        print(f"[Stop Containers] Error stopping container {container_id}: {e}")
    except Exception as e:
        print(f"[Stop Containers] Error finding docker-compose containers: {e}")
    
    return stopped_containers
