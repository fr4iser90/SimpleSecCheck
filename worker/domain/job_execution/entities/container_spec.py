"""
Container specification entity for the worker domain.

Defines the specifications for container execution including image, volumes, and environment.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum


class ContainerNetworkMode(Enum):
    """Network modes for containers."""
    BRIDGE = "bridge"
    HOST = "host"
    NONE = "none"
    CONTAINER = "container"


@dataclass
class VolumeMount:
    """Represents a volume mount for a container."""
    
    host_path: str
    container_path: str
    read_only: bool = False
    
    def to_docker_mount(self) -> Dict[str, str]:
        """Convert to Docker mount format."""
        mount_type = "ro" if self.read_only else "rw"
        return {
            "type": "bind",
            "source": self.host_path,
            "target": self.container_path,
            "consistency": mount_type
        }


@dataclass
class ContainerSpec:
    """Represents container specifications for execution."""
    
    image: str
    command: List[str]
    environment: Dict[str, str] = field(default_factory=dict)
    volumes: List[VolumeMount] = field(default_factory=list)
    network_mode: ContainerNetworkMode = ContainerNetworkMode.BRIDGE
    container_name: Optional[str] = None
    privileged: bool = False
    read_only: bool = False
    tmpfs: List[str] = field(default_factory=list)
    cpu_limit: Optional[str] = None
    memory_limit: Optional[str] = None
    restart_policy: Optional[str] = None
    labels: Dict[str, str] = field(default_factory=dict)
    ports: Dict[str, int] = field(default_factory=dict)
    working_dir: Optional[str] = None
    user: Optional[str] = None
    entrypoint: Optional[List[str]] = None
    
    def add_volume(self, host_path: str, container_path: str, read_only: bool = False) -> None:
        """Add a volume mount."""
        # Validate host_path is a string
        if not isinstance(host_path, str):
            raise TypeError(f"host_path must be a string, got {type(host_path)}: {host_path}")
        if not isinstance(container_path, str):
            raise TypeError(f"container_path must be a string, got {type(container_path)}: {container_path}")
        self.volumes.append(VolumeMount(host_path, container_path, read_only))
    
    def add_environment(self, key: str, value: str) -> None:
        """Add an environment variable."""
        self.environment[key] = value
    
    def add_label(self, key: str, value: str) -> None:
        """Add a container label."""
        self.labels[key] = value
    
    def add_port(self, container_port: str, host_port: int) -> None:
        """Add a port mapping."""
        self.ports[container_port] = host_port
    
    def to_docker_config(self) -> Dict[str, Any]:
        """Convert to Docker container configuration."""
        # Docker Python API expects 'host_config' with 'binds' for volumes
        # Format: {"binds": ["/host/path:/container/path:rw"]}
        binds = []
        for volume in self.volumes:
            mode = "ro" if volume.read_only else "rw"
            binds.append(f"{volume.host_path}:{volume.container_path}:{mode}")
        
        # Build host_config dict
        host_config = {
            "binds": binds,
        }
        
        if self.privileged:
            host_config["privileged"] = True
        
        if self.read_only:
            host_config["read_only"] = True
        
        if self.tmpfs:
            # tmpfs can be either a list of paths or a dict with path:options
            # If list items contain ":", parse as "path:options", otherwise use default
            tmpfs_dict = {}
            for item in self.tmpfs:
                if ":" in item:
                    # Format: "/tmp:size=500m" -> path: "/tmp", options: "size=500m"
                    path, options = item.split(":", 1)
                    tmpfs_dict[path] = f"rw,noexec,nosuid,{options}"
                else:
                    # Just a path, use default size
                    tmpfs_dict[item] = "rw,noexec,nosuid,size=100m"
            host_config["tmpfs"] = tmpfs_dict
        
        if self.cpu_limit:
            # CPU quota in microseconds (2000m = 2 cores = 2000000 microseconds)
            cpu_quota = int(self.cpu_limit.replace("m", "")) * 1000
            host_config["cpu_quota"] = cpu_quota
            host_config["cpu_period"] = 100000  # Default period
        
        if self.memory_limit:
            host_config["mem_limit"] = self.memory_limit
        
        if self.restart_policy:
            host_config["restart_policy"] = {"Name": self.restart_policy}
        
        # Port bindings format: {"container_port": ("host_ip", host_port)}
        if self.ports:
            port_bindings = {}
            for container_port, host_port in self.ports.items():
                port_bindings[container_port] = host_port
            host_config["port_bindings"] = port_bindings
        
        # Main container config
        config = {
            "image": self.image,
            "command": self.command,
            "environment": self.environment,
            "network_mode": self.network_mode.value,
            "labels": self.labels,
            "host_config": host_config,
        }
        
        if self.container_name:
            config["name"] = self.container_name
        
        if self.working_dir:
            config["working_dir"] = self.working_dir
        
        if self.user:
            config["user"] = self.user
        
        if self.entrypoint:
            config["entrypoint"] = self.entrypoint
        
        return config
    
    @classmethod
    def from_scan_config(
        cls,
        image: str,
        target: str,
        results_dir: str,  # Host path for volume mounting
        scan_id: str,
        scan_type: str = "code",
        target_type: str = None,
        target_mount_path: Optional[str] = None,
        finding_policy: Optional[str] = None,
        collect_metadata: bool = True,
        exclude_paths: Optional[str] = None,
        git_branch: Optional[str] = None,
        results_dir_container: Optional[str] = None,  # Container path (what Scanner sees)
        asset_volumes: Optional[List[Dict[str, str]]] = None,  # Asset volumes from scanner manifests
        scanners: Optional[List[str]] = None  # Selected scanners from backend (if None, scanner filters by scan_type)
    ) -> 'ContainerSpec':
        """Create container spec from scan configuration.
        
        Args:
            image: Docker image name
            target: Scan target URL/path
            results_dir: Host path for results volume mount (from Worker's perspective)
            scan_id: Scan identifier
            scan_type: Type of scan (code, container, etc.)
            target_mount_path: Optional target mount path
            finding_policy: Optional finding policy path
            collect_metadata: Whether to collect metadata
            exclude_paths: Optional paths to exclude
            results_dir_container: Container path for results (defaults to /app/results)
            
        Note:
            Logs are part of Results - Scanner creates results/{scan_id}/logs/ automatically.
            No separate logs_dir needed.
        """
        
        # Command: Use orchestrator module (as defined in Dockerfile CMD)
        command = ["python3", "-m", "scanner.core.orchestrator"]
        
        # Container paths (what Scanner container sees inside)
        if not results_dir_container:
            raise ValueError("results_dir_container is required but not provided. Worker must set RESULTS_DIR_CONTAINER environment variable.")
        
        container_results_dir = results_dir_container
        
        # Environment variables (orchestrator reads these from env)
        # RESULTS_DIR_IN_CONTAINER is the BASE directory - orchestrator will append scan_id itself
        # This prevents double scan_id in path: /app/results/{scan_id}/{scan_id}
        
        if not target_type:
            raise ValueError(f"target_type is required but not provided. Backend must determine target_type (e.g., git_repo, local_mount, etc.)")
        
        environment = {
            "SCAN_ID": scan_id,  # Required - orchestrator uses this to build scan-specific path
            "SCAN_TARGET": target,  # Orchestrator expects SCAN_TARGET
            "SCAN_TYPE": scan_type,  # Scanner expects same ScanType values as backend
            "TARGET_TYPE": target_type,
            "PROJECT_RESULTS_DIR": container_results_dir,  # Base results directory in container
            "RESULTS_DIR_IN_CONTAINER": container_results_dir,  # Base directory - orchestrator appends scan_id
            "TARGET_PATH_IN_CONTAINER": "/target",
            "COLLECT_METADATA": "true" if collect_metadata else "false",
        }
        
        # Add selected scanners if provided (from backend/queue message)
        # This allows backend to control which scanners run, instead of scanner filtering
        # If scanners is None or empty, scanner will filter by scan_type (fallback)
        import json
        scanners_list = scanners if scanners is not None else []
        if scanners_list:
            environment["SELECTED_SCANNERS"] = json.dumps(scanners_list)
        
        # Add exclude paths if provided
        if exclude_paths:
            environment["SIMPLESECCHECK_EXCLUDE_PATHS"] = exclude_paths
        
        # Add git branch if provided
        if git_branch:
            environment["GIT_BRANCH"] = git_branch
        
        # Automatically detect PUID/PGID from mounted project root directory
        # This ensures files are created with correct ownership on host
        # Same approach as backend/worker - detect from project root ownership
        try:
            host_project_root = os.environ.get("HOST_PROJECT_ROOT", os.environ.get("PWD", "."))
            if not os.path.isabs(host_project_root):
                host_project_root = os.path.abspath(host_project_root)
            project_root_stat = os.stat(host_project_root)
            detected_uid = str(project_root_stat.st_uid)
            detected_gid = str(project_root_stat.st_gid)
            environment["PUID"] = detected_uid
            environment["PGID"] = detected_gid
        except (OSError, AttributeError):
            # If stat fails, don't set PUID/PGID - scanner will use defaults
            pass
        
        # Determine if container should be read-only
        # For git_repo, we need /target to be writable for Git Clone
        # For local_mount, /target is read-only (mounted from host)
        container_read_only = target_type != "git_repo"
        
        # Create container spec
        # Increase tmpfs size to avoid "no space left on device" errors (especially for Trivy DB downloads)
        # tmpfs format: ["/tmp:size=500m", "/var/tmp:size=200m"]
        tmpfs_config = []
        if container_read_only:
            tmpfs_config = ["/tmp:size=500m", "/var/tmp:size=200m"]
        else:
            tmpfs_config = ["/tmp:size=500m", "/var/tmp:size=200m", "/target:size=2g"]
        
        spec = cls(
            image=image,
            command=command,
            environment=environment,
            container_name=f"ssc-scan-{scan_id[:8]}",
            read_only=container_read_only,
            tmpfs=tmpfs_config,
            cpu_limit="2000m",  # 2 CPU cores
            memory_limit="4g",  # 4GB RAM
            labels={
                "simpleseccheck.scan_id": scan_id,
                "simpleseccheck.scan_type": scan_type,
                "simpleseccheck.job_type": "scan"
            }
        )
        
        # Validate all paths are strings before adding volumes
        if not isinstance(results_dir, str):
            raise TypeError(f"results_dir must be a string, got {type(results_dir)}: {results_dir}")
        
        # Add volume mounts
        # Mount host paths to container paths (what Scanner container sees)
        # NOTE: Logs are part of Results - Scanner creates results/{scan_id}/logs/ automatically
        spec.add_volume(results_dir, container_results_dir, read_only=False)
        
        # Mount scanner asset volumes (if provided)
        # Plugins define their required volumes in manifest.yaml (e.g., OWASP data, Trivy cache)
        # Backend fetches these from worker API and includes them in queue message
        # Plugins define their required volumes in manifest.yaml, backend sends them via queue
        if asset_volumes:
            host_project_root = os.environ.get("HOST_PROJECT_ROOT", os.environ.get("PWD", "."))
            if not os.path.isabs(host_project_root):
                host_project_root = os.path.abspath(host_project_root)
            for asset_volume in asset_volumes:
                host_subpath = asset_volume.get("host_subpath")
                container_path = asset_volume.get("container_path")
                if host_subpath and container_path:
                    asset_host_path = os.path.join(host_project_root, host_subpath)
                    spec.add_volume(asset_host_path, container_path, read_only=False)
        
        # For local_mount, mount target from host (read-only)
        # For git_repo, /target is tmpfs (writable for Git Clone)
        if target_mount_path:
            if not isinstance(target_mount_path, str):
                raise TypeError(f"target_mount_path must be a string, got {type(target_mount_path)}: {target_mount_path}")
            spec.add_volume(target_mount_path, "/target", read_only=True)
        
        if finding_policy:
            if not isinstance(finding_policy, str):
                # Skip if finding_policy is not a string
                pass
            elif finding_policy.startswith("/target/"):
                spec.add_volume(
                    finding_policy.replace("/target/", ""),
                    finding_policy,
                    read_only=True
                )
        
        return spec