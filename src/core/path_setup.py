"""
Central path setup for SimpleSecCheck
Sets up sys.path to include processors and core modules
"""
import os
import sys


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
    
    # Get the src/ directory (this file is in src/core/)
    SRC_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    
    # Add processors and core to path
    PROCESSORS_DIR = os.path.join(SRC_DIR, "processors")
    CORE_DIR = os.path.join(SRC_DIR, "core")
    
    sys.path.insert(0, SRC_DIR)
    sys.path.insert(0, PROCESSORS_DIR)
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
    if not scan_results_dir_container.startswith("/app/results/"):
        return scan_results_dir_container
    
    host_project_root = get_host_project_root()
    if not host_project_root:
        return scan_results_dir_container
    
    relative_path = scan_results_dir_container[len("/app/results"):]
    if relative_path.startswith("/"):
        relative_path = relative_path[1:]
    
    return os.path.join(host_project_root, "results", relative_path)


def get_target_mount_path_host(target_path: str) -> str:
    """
    Get host path for target mount.
    Returns: absolute host path
    """
    if not target_path.startswith("/app/results/"):
        return target_path
    
    host_project_root = get_host_project_root()
    if not host_project_root:
        return target_path
    
    relative_path = target_path[len("/app/results"):]
    if relative_path.startswith("/"):
        relative_path = relative_path[1:]
    
    return os.path.join(host_project_root, "results", relative_path)


def get_owasp_data_path_host() -> str:
    """
    Get host path for OWASP data directory.
    Returns host path or None if not found.
    """
    host_project_root = get_host_project_root()
    if not host_project_root:
        return None
    
    return os.path.join(host_project_root, "owasp-dependency-check-data")
