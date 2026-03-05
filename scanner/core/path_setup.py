"""
Central path setup for SimpleSecCheck
Sets up sys.path to include processors and core modules
"""
import os
import sys
from pathlib import Path
from typing import Optional


def setup_paths():
    """
    Setup sys.path to include processors and core modules
    Works from any location in the project
    Central path management - no other file should calculate paths!
    """
    # Add Docker paths first (if exists) - needed for Docker containers
    sys.path.insert(0, "/project/src")
    sys.path.insert(0, "/SimpleSecCheck")
    sys.path.insert(0, "/SimpleSecCheck/scripts")
    sys.path.insert(0, "/scanner")
    
    # Get the src/ directory (this file is in src/core/)
    SRC_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    
    # Add scanners and core to path
    SCANNERS_DIR = os.path.join(SRC_DIR, "scanners")
    CORE_DIR = os.path.join(SRC_DIR, "core")
    
    sys.path.insert(0, SRC_DIR)
    sys.path.insert(0, SCANNERS_DIR)
    sys.path.insert(0, CORE_DIR)


def get_host_project_root():
    """
    Get host project root directory.
    Returns host path or None if not found.
    """
    host_project_root = os.environ.get("HOST_PROJECT_ROOT")
    if host_project_root:
        return host_project_root
    
    # Try to get from docker inspect
    import subprocess as sp
    try:
        result = sp.run(
            ["docker", "inspect", "--format", "{{range .Mounts}}{{if eq .Destination \"/project\"}}{{.Source}}{{end}}{{end}}", "SimpleSecCheck_webui"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    
    return None


def get_scan_results_dir_host(scan_results_dir_container: str) -> str:
    """
    Get host path for scan-specific results directory.
    """
    if not scan_results_dir_container.startswith("/webui/results/"):
        return scan_results_dir_container
    
    host_project_root = get_host_project_root()
    if not host_project_root:
        return scan_results_dir_container
    
    relative_path = scan_results_dir_container[len("/webui/results"):]
    if relative_path.startswith("/"):
        relative_path = relative_path[1:]
    
    return os.path.join(host_project_root, "results", relative_path)


def get_target_mount_path_host(target_path: str) -> str:
    """
    Get host path for target mount.
    
    Handles two cases:
    1. Git clones: target_path is a container path like /webui/results/tmp/.../repo
       → Converts to host path in results directory
    2. Local scans: target_path is already a host path like /home/user/project
       → Returns as-is (no conversion needed)
    
    Args:
        target_path: Container path (Git clone) or host path (local scan)
    
    Returns:
        Absolute host path
    """
    # If path starts with /webui/results/, it's a container path from a Git clone
    # Convert it to the corresponding host path
    if target_path.startswith("/webui/results/"):
        host_project_root = get_host_project_root()
        if not host_project_root:
            return target_path
        
        relative_path = target_path[len("/webui/results"):] 
        if relative_path.startswith("/"):
            relative_path = relative_path[1:]
        
        return os.path.join(host_project_root, "results", relative_path)
    
    # Otherwise, it's already a host path (local scan) - return as-is
    return target_path


def get_finding_policy_check_path_for_git_clone(container_path: str, policy_relative_path: str) -> Optional[str]:
    """
    Get path to check for finding policy file for Git clones.
    
    Git clones are stored in the WebUI container at /webui/results/tmp/.../repo,
    so we CAN check if the file exists in the WebUI container.
    
    Args:
        container_path: Container path where Git repo was cloned (e.g., /webui/results/tmp/.../repo)
        policy_relative_path: Relative path to policy file (e.g., config/finding-policy.json)
    
    Returns:
        Full container path to check if file exists, or None if path is invalid
    """
    if not container_path or not container_path.startswith("/webui/results/"):
        return None
    
    policy_path = os.path.join(container_path, policy_relative_path)
    return policy_path


def get_finding_policy_check_path_for_local_scan(host_path: str, policy_relative_path: str) -> Optional[str]:
    """
    Get path to check for finding policy file for local scans.
    
    IMPORTANT: For local scans, the WebUI container CANNOT access host paths.
    The target is only mounted in the scanner container at /target.
    This function returns None to indicate the file cannot be checked in WebUI container.
    The scanner container will check it after mounting the target volume.
    
    Args:
        host_path: Host path to target project (e.g., /home/user/project)
        policy_relative_path: Relative path to policy file (e.g., config/finding-policy.json)
    
    Returns:
        None - file cannot be checked in WebUI container, scanner will check it
    """
    # Local scan: WebUI container cannot access host paths
    # Return None - scanner container will check after mounting
    return None


def get_owasp_data_path_host() -> str:
    """
    Get host path for OWASP data directory.
    Returns host path or None if not found.
    """
    host_project_root = get_host_project_root()
    if not host_project_root:
        return None
    
    return os.path.join(host_project_root, "scanner", "scanners", "owasp", "data")


def get_config_path_host() -> str:
    """
    Get host path for config directory.
    Returns host path or None if not found.
    """
    host_project_root = get_host_project_root()
    if not host_project_root:
        return None
    
    return os.path.join(host_project_root, "scanner", "scanners")


def get_results_dir():
    """
    Get RESULTS_DIR from environment variable.
    MUST be set - no default!
    Returns: RESULTS_DIR path or None if not set
    """
    return os.environ.get('RESULTS_DIR')


def get_output_file():
    """
    Get OUTPUT_FILE from environment variable or calculate from RESULTS_DIR.
    Returns: OUTPUT_FILE path or None if RESULTS_DIR not set
    """
    output_file = os.environ.get('OUTPUT_FILE')
    if output_file:
        return output_file
    
    results_dir = get_results_dir()
    if not results_dir:
        return None
    
    return os.path.join(results_dir, 'security-summary.html')


def get_webui_base_dir():
    """
    Get WebUI base directory (SimpleSecCheck root).
    Returns: Path object or None
    """
    from pathlib import Path
    
    # Try from environment
    base_dir_env = os.environ.get('WEBUI_BASE_DIR')
    if base_dir_env:
        return Path(base_dir_env)
    
    # Try /app (container)
    app_path = Path("/webui")
    if app_path.exists():
        return app_path
    
    # Try to find from current file location (dev/local)
    # This file is in src/core/, so go up 2 levels to get project root
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent
    if (project_root / "scripts").exists():
        return project_root
    
    return None


def get_webui_cli_script():
    """
    Get WebUI CLI script path (legacy, unused).
    Central function - kept for backward compatibility.
    Returns: Path object
    """
    # Legacy path removed; return project root marker instead
    return Path("/project")


def get_webui_results_dir():
    """
    Get WebUI results directory.
    Returns: Path object or None
    """
    base_dir = get_webui_base_dir()
    if not base_dir:
        return None
    
    return base_dir / "results"


def get_results_dir_for_scan(project_name: str, scan_id: str) -> str:
    """
    Get results directory path for a specific scan.
    Central function - all services should use this!
    EINHEITLICH: Dev und Prod verwenden beide /webui/results/...
    
    Args:
        project_name: Name of the project being scanned
        scan_id: Unique scan identifier (timestamp format)
    
    Returns:
        str: Full path to results directory (e.g., "/webui/results/PROJECT_SCAN_ID")
    """
    # EINHEITLICH: Immer /webui/results/... (weil ./results:/webui/results in beiden gemountet)
    return f"/webui/results/{project_name}_{scan_id}"


def get_logs_dir_for_scan(results_dir: str) -> str:
    """
    Get logs directory path for a specific scan.
    Central function - all services should use this!
    
    Args:
        results_dir: Results directory path (from get_results_dir_for_scan)
    
    Returns:
        str: Full path to logs directory (e.g., "/webui/results/PROJECT_SCAN_ID/logs")
    """
    return f"{results_dir}/logs"


def get_webui_logs_dir():
    """
    Get WebUI logs directory.
    Returns: Path object or None
    """
    base_dir = get_webui_base_dir()
    if not base_dir:
        return None
    
    return base_dir / "logs"


def get_webui_owasp_data_dir():
    """
    Get WebUI OWASP data directory.
    Returns: Path object or None
    """
    base_dir = get_webui_base_dir()
    if not base_dir:
        return None
    
    return Path("/scanner/scanners/owasp/data")


def get_webui_frontend_paths():
    """
    Get WebUI frontend static paths (multiple fallbacks).
    Returns: List of Path objects
    """
    from pathlib import Path
    
    base_dir = get_webui_base_dir()
    if not base_dir:
        return []
    
    paths = [
        base_dir / "webui" / "frontend" / "dist",
        base_dir / "static",
        Path("/webui/static"),
    ]
    
    return paths


def get_docker_compose_file():
    """
    Get docker-compose file path based on environment.
    Central function - all services should use this!
    
    Returns:
        str: Path to docker-compose file (e.g., "/project/docker-compose.prod.yml" or "/project/docker-compose.yml")
    """
    # Allow explicit override (for setups that rename compose file to docker-compose.yml)
    compose_override = os.getenv("DOCKER_COMPOSE_FILE")
    if compose_override:
        return compose_override

    # Get environment (default to dev)
    environment = os.getenv("ENVIRONMENT", "dev").lower()
    
    # Determine docker-compose filename based on environment
    if environment == "prod":
        compose_filename = "docker-compose.prod.yml"
    else:
        compose_filename = "docker-compose.yml"
    
    # In containers: /project is always mounted (.:/project:ro)
    return f"/project/{compose_filename}"


def get_docker_compose_context():
    """
    Get docker-compose context directory (project root).
    Central function - all services should use this!
    
    Returns:
        str: Path to docker-compose context (always "/project" in containers)
    """
    # In containers: /project is always mounted (.:/project:ro)
    return "/project"
