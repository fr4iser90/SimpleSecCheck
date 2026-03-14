"""
Container specification entity for the worker domain.

Defines the specifications for container execution including image, volumes, and environment.
"""

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
        config = {
            "image": self.image,
            "command": self.command,
            "environment": self.environment,
            "volumes": [v.to_docker_mount() for v in self.volumes],
            "network_mode": self.network_mode.value,
            "labels": self.labels,
            "ports": self.ports,
        }
        
        if self.container_name:
            config["name"] = self.container_name
        
        if self.privileged:
            config["privileged"] = True
        
        if self.read_only:
            config["read_only"] = True
        
        if self.tmpfs:
            config["tmpfs"] = {path: "rw,noexec,nosuid,size=100m" for path in self.tmpfs}
        
        if self.cpu_limit:
            config["cpu_quota"] = int(self.cpu_limit.replace("m", "")) * 1000
        
        if self.memory_limit:
            config["mem_limit"] = self.memory_limit
        
        if self.restart_policy:
            config["restart_policy"] = {"Name": self.restart_policy}
        
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
        results_dir: str,
        logs_dir: str,
        scan_id: str,
        scan_type: str = "code",
        target_mount_path: Optional[str] = None,
        finding_policy: Optional[str] = None,
        collect_metadata: bool = True,
        exclude_paths: Optional[str] = None
    ) -> 'ContainerSpec':
        """Create container spec from scan configuration."""
        
        # Base command
        command = ["ssc", "scan", target]
        
        # Add results directory
        command.extend(["--json", f"/app/results/{scan_id}.json"])
        
        # Environment variables
        environment = {
            "SCAN_ID": scan_id,
            "SCAN_TYPE": scan_type,
            "TARGET_TYPE": "local_mount" if scan_type == "code" else scan_type,
            "PROJECT_RESULTS_DIR": "/app/results",
            "RESULTS_DIR_IN_CONTAINER": "/app/results",
            "TARGET_PATH_IN_CONTAINER": "/target",
            "COLLECT_METADATA": "true" if collect_metadata else "false",
        }
        
        # Add exclude paths if provided
        if exclude_paths:
            environment["SIMPLESECCHECK_EXCLUDE_PATHS"] = exclude_paths
        
        # Create container spec
        spec = cls(
            image=image,
            command=command,
            environment=environment,
            container_name=f"ssc-scan-{scan_id[:8]}",
            read_only=True,
            tmpfs=["/tmp", "/var/tmp"],
            cpu_limit="2000m",  # 2 CPU cores
            memory_limit="4g",  # 4GB RAM
            labels={
                "simpleseccheck.scan_id": scan_id,
                "simpleseccheck.scan_type": scan_type,
                "simpleseccheck.job_type": "scan"
            }
        )
        
        # Add volume mounts
        spec.add_volume(results_dir, "/app/results", read_only=False)
        spec.add_volume(logs_dir, "/app/logs", read_only=False)
        
        if target_mount_path:
            spec.add_volume(target_mount_path, "/target", read_only=True)
        
        if finding_policy:
            # Add finding policy if it's a container path
            if finding_policy.startswith("/target/"):
                spec.add_volume(
                    finding_policy.replace("/target/", ""),
                    finding_policy,
                    read_only=True
                )
        
        return spec