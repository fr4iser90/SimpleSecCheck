"""
Scan Configuration Value Object

This module defines the ScanConfig value object which represents immutable scan configuration.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

from domain.entities.target_type import TargetType
from domain.value_objects.scan_profile import ScanProfileName


class ScanMode(str, Enum):
    """Scan mode enumeration."""
    QUICK = "quick"
    FULL = "full"
    CUSTOM = "custom"


class ScanDepth(str, Enum):
    """Scan depth enumeration."""
    SHALLOW = "shallow"
    MEDIUM = "medium"
    DEEP = "deep"


@dataclass(frozen=True)
class ScanConfig:
    """Immutable scan configuration value object."""
    
    # Basic configuration
    scan_mode: ScanMode = ScanMode.QUICK
    scan_depth: ScanDepth = ScanDepth.MEDIUM
    timeout: int = 3600
    max_concurrent_scanners: int = 5
    
    # Scanner configuration
    enabled_scanners: List[str] = field(default_factory=list)
    scanner_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Target configuration
    target_type: str = TargetType.GIT_REPO.value
    target_depth: int = 3
    include_paths: List[str] = field(default_factory=list)
    exclude_paths: List[str] = field(default_factory=list)
    
    # Security configuration
    fail_on_critical: bool = False
    fail_on_high: bool = False
    max_critical_vulnerabilities: int = 0
    max_high_vulnerabilities: int = 10
    
    # Output configuration
    output_format: str = "json"
    include_raw_output: bool = False
    compress_results: bool = True
    
    # Advanced configuration
    custom_rules: List[str] = field(default_factory=list)
    environment_variables: Dict[str, str] = field(default_factory=dict)
    docker_options: Dict[str, Any] = field(default_factory=dict)
    
    # Optional scan options (passed to worker/scanner; not used by domain validation)
    finding_policy: Optional[str] = None
    collect_metadata: Optional[bool] = None
    git_branch: Optional[str] = None

    # Scan profile (manifest-driven per plugin); see manifest.yaml scan_profiles
    scan_profile: str = ScanProfileName.STANDARD.value
    profile_tuning: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def validate(self) -> bool:
        """Validate the scan configuration."""
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")
        
        if self.max_concurrent_scanners <= 0:
            raise ValueError("Max concurrent scanners must be positive")
        
        if self.target_depth <= 0:
            raise ValueError("Target depth must be positive")
        
        if self.scan_mode not in ScanMode:
            raise ValueError(f"Invalid scan mode: {self.scan_mode}")
        
        if self.scan_depth not in ScanDepth:
            raise ValueError(f"Invalid scan depth: {self.scan_depth}")

        allowed_profiles = {e.value for e in ScanProfileName}
        if self.scan_profile not in allowed_profiles:
            raise ValueError(
                f"Invalid scan_profile: {self.scan_profile}. Allowed: {sorted(allowed_profiles)}"
            )
        
        return True
    
    def get_scanner_config(self, scanner_name: str) -> Dict[str, Any]:
        """Get configuration for a specific scanner."""
        return self.scanner_configs.get(scanner_name, {})
    
    def is_path_included(self, path: str) -> bool:
        """Check if a path should be included in the scan."""
        if self.include_paths:
            return any(path.startswith(include_path) for include_path in self.include_paths)
        
        if self.exclude_paths:
            return not any(path.startswith(exclude_path) for exclude_path in self.exclude_paths)
        
        return True
    
    def should_fail_on_vulnerability(self, severity: str, count: int) -> bool:
        """Check if scan should fail based on vulnerability count and severity."""
        if severity == "critical" and self.fail_on_critical:
            return count > self.max_critical_vulnerabilities
        
        if severity == "high" and self.fail_on_high:
            return count > self.max_high_vulnerabilities
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'scan_mode': self.scan_mode.value,
            'scan_depth': self.scan_depth.value,
            'timeout': self.timeout,
            'max_concurrent_scanners': self.max_concurrent_scanners,
            'enabled_scanners': self.enabled_scanners,
            'scanner_configs': self.scanner_configs,
            'target_type': self.target_type,
            'target_depth': self.target_depth,
            'include_paths': self.include_paths,
            'exclude_paths': self.exclude_paths,
            'fail_on_critical': self.fail_on_critical,
            'fail_on_high': self.fail_on_high,
            'max_critical_vulnerabilities': self.max_critical_vulnerabilities,
            'max_high_vulnerabilities': self.max_high_vulnerabilities,
            'output_format': self.output_format,
            'include_raw_output': self.include_raw_output,
            'compress_results': self.compress_results,
            'custom_rules': self.custom_rules,
            'environment_variables': self.environment_variables,
            'docker_options': self.docker_options,
            'finding_policy': self.finding_policy,
            'collect_metadata': self.collect_metadata,
            'git_branch': self.git_branch,
            'scan_profile': self.scan_profile,
            'profile_tuning': self.profile_tuning,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScanConfig':
        """Create from dictionary."""
        return cls(
            scan_mode=ScanMode(data.get('scan_mode', 'quick')),
            scan_depth=ScanDepth(data.get('scan_depth', 'medium')),
            timeout=data.get('timeout', 3600),
            max_concurrent_scanners=data.get('max_concurrent_scanners', 5),
            enabled_scanners=data.get('enabled_scanners', []),
            scanner_configs=data.get('scanner_configs', {}),
            target_type=data.get('target_type', TargetType.GIT_REPO.value),
            target_depth=data.get('target_depth', 3),
            include_paths=data.get('include_paths', []),
            exclude_paths=data.get('exclude_paths', []),
            fail_on_critical=data.get('fail_on_critical', False),
            fail_on_high=data.get('fail_on_high', False),
            max_critical_vulnerabilities=data.get('max_critical_vulnerabilities', 0),
            max_high_vulnerabilities=data.get('max_high_vulnerabilities', 10),
            output_format=data.get('output_format', 'json'),
            include_raw_output=data.get('include_raw_output', False),
            compress_results=data.get('compress_results', True),
            custom_rules=data.get('custom_rules', []),
            environment_variables=data.get('environment_variables', {}),
            docker_options=data.get('docker_options', {}),
            finding_policy=data.get('finding_policy'),
            collect_metadata=data.get('collect_metadata'),
            git_branch=data.get('git_branch'),
            scan_profile=data.get('scan_profile') or ScanProfileName.STANDARD.value,
            profile_tuning=data.get('profile_tuning') or {},
        )
    
    def merge_with(self, other: 'ScanConfig') -> 'ScanConfig':
        """Merge with another scan config, prioritizing non-default values."""
        def _merge_value(self_val, other_val, default_val):
            if other_val != default_val:
                return other_val
            return self_val
        
        return ScanConfig(
            scan_mode=_merge_value(self.scan_mode, other.scan_mode, ScanMode.QUICK),
            scan_depth=_merge_value(self.scan_depth, other.scan_depth, ScanDepth.MEDIUM),
            timeout=_merge_value(self.timeout, other.timeout, 3600),
            max_concurrent_scanners=_merge_value(self.max_concurrent_scanners, other.max_concurrent_scanners, 5),
            enabled_scanners=other.enabled_scanners if other.enabled_scanners else self.enabled_scanners,
            scanner_configs={**self.scanner_configs, **other.scanner_configs},
            target_type=_merge_value(self.target_type, other.target_type, TargetType.GIT_REPO.value),
            target_depth=_merge_value(self.target_depth, other.target_depth, 3),
            include_paths=other.include_paths if other.include_paths else self.include_paths,
            exclude_paths=other.exclude_paths if other.exclude_paths else self.exclude_paths,
            fail_on_critical=_merge_value(self.fail_on_critical, other.fail_on_critical, False),
            fail_on_high=_merge_value(self.fail_on_high, other.fail_on_high, False),
            max_critical_vulnerabilities=_merge_value(self.max_critical_vulnerabilities, other.max_critical_vulnerabilities, 0),
            max_high_vulnerabilities=_merge_value(self.max_high_vulnerabilities, other.max_high_vulnerabilities, 10),
            output_format=_merge_value(self.output_format, other.output_format, "json"),
            include_raw_output=_merge_value(self.include_raw_output, other.include_raw_output, False),
            compress_results=_merge_value(self.compress_results, other.compress_results, True),
            custom_rules=other.custom_rules if other.custom_rules else self.custom_rules,
            environment_variables={**self.environment_variables, **other.environment_variables},
            docker_options={**self.docker_options, **other.docker_options},
            finding_policy=other.finding_policy if other.finding_policy is not None else self.finding_policy,
            collect_metadata=other.collect_metadata if other.collect_metadata is not None else self.collect_metadata,
            git_branch=other.git_branch if other.git_branch is not None else self.git_branch,
            scan_profile=(
                other.scan_profile
                if other.scan_profile != ScanProfileName.STANDARD.value
                else self.scan_profile
            ),
            profile_tuning={**self.profile_tuning, **other.profile_tuning},
        )