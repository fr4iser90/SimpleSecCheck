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
    
    Handles two cases:
    1. Git clones: target_path is a container path like /app/results/tmp/.../repo
       → Converts to host path in results directory
    2. Local scans: target_path is already a host path like /home/user/project
       → Returns as-is (no conversion needed)
    
    Args:
        target_path: Container path (Git clone) or host path (local scan)
    
    Returns:
        Absolute host path
    """
    # If path starts with /app/results/, it's a container path from a Git clone
    # Convert it to the corresponding host path
    if target_path.startswith("/app/results/"):
        host_project_root = get_host_project_root()
        if not host_project_root:
            return target_path
        
        relative_path = target_path[len("/app/results"):]
        if relative_path.startswith("/"):
            relative_path = relative_path[1:]
        
        return os.path.join(host_project_root, "results", relative_path)
    
    # Otherwise, it's already a host path (local scan) - return as-is
    return target_path


def get_owasp_data_path_host() -> str:
    """
    Get host path for OWASP data directory.
    Returns host path or None if not found.
    """
    host_project_root = get_host_project_root()
    if not host_project_root:
        return None
    
    return os.path.join(host_project_root, "owasp-dependency-check-data")


def get_config_path_host() -> str:
    """
    Get host path for config directory.
    Returns host path or None if not found.
    """
    host_project_root = get_host_project_root()
    if not host_project_root:
        return None
    
    return os.path.join(host_project_root, "config")


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
    app_path = Path("/app")
    if app_path.exists():
        return app_path
    
    # Try to find from current file location (dev/local)
    # This file is in src/core/, so go up 2 levels to get project root
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent
    if (project_root / "scripts" / "run-docker.sh").exists():
        return project_root
    
    return None


def get_webui_cli_script():
    """
    Get WebUI CLI script path (scripts/run-docker.sh).
    Returns: Path object or None
    """
    base_dir = get_webui_base_dir()
    if not base_dir:
        return None
    
    script_path = base_dir / "scripts" / "run-docker.sh"
    if script_path.exists():
        return script_path
    
    return None


def get_webui_results_dir():
    """
    Get WebUI results directory.
    Returns: Path object or None
    """
    base_dir = get_webui_base_dir()
    if not base_dir:
        return None
    
    return base_dir / "results"


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
    
    return base_dir / "owasp-dependency-check-data"


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
        Path("/app/static"),
    ]
    
    return paths
