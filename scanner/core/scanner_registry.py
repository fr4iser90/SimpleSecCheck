"""
Scanner Registry
Modern, dynamic scanner registration system - no hardcoded steps!
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
from pathlib import Path
import inspect


class ScanType(Enum):
    """Scan type enumeration"""
    CODE = "code"
    DEPENDENCY = "dependency"
    SECRETS = "secrets"
    CONFIG = "config"
    CONTAINER = "container"
    WEBSITE = "website"
    NETWORK = "network"
    IMAGE = "image"
    MOBILE = "mobile"


class TargetType(Enum):
    """Target type enumeration"""
    LOCAL_CODE = "local_code"
    GIT_REPO = "git_repo"
    DOCKER_IMAGE = "docker_image"
    WEBSITE = "website"
    NETWORK_HOST = "network_host"
    APK = "apk"
    IPA = "ipa"
    FILE_SYSTEM = "file_system"


class ArtifactType(Enum):
    """Artifact type enumeration"""
    PACKAGE_JSON = "package.json"
    REQUIREMENTS = "requirements.txt"
    DOCKERFILE = "Dockerfile"
    ANDROID_MANIFEST = "AndroidManifest.xml"
    APK = "apk"
    IPA = "ipa"


@dataclass
class ScannerCapability:
    """Scanner capability definition"""
    scan_type: ScanType
    supported_targets: List[TargetType]
    supported_artifacts: List[ArtifactType]


@dataclass
class Scanner:
    """Scanner definition"""
    name: str
    capabilities: List[ScannerCapability]
    script_path: str  # Path to scanner script (inside container)
    enabled: bool = True
    priority: int = 0  # Execution order (lower = earlier)
    requires_condition: Optional[str] = None  # Optional condition (e.g., "IS_NATIVE")
    python_class: Optional[str] = None  # Fully-qualified Python scanner class


class ScannerRegistry:
    """Central registry for all scanners - dynamically extensible"""
    _scanners: Dict[str, Scanner] = {}
    
    @classmethod
    def register(cls, scanner: Scanner):
        """Register a scanner"""
        cls._scanners[scanner.name] = scanner

    @classmethod
    def get_scanners_for_target(
        cls,
        target_type: TargetType,
        scan_types: Optional[List[ScanType]] = None,
        conditions: Optional[Dict[str, any]] = None,
    ) -> List[Scanner]:
        """
        Get all enabled scanners for a target type and optional scan types.
        """
        scanners = []
        for scanner in cls._scanners.values():
            if not scanner.enabled:
                continue
            # Check condition if required
            if scanner.requires_condition:
                if not conditions or not conditions.get(scanner.requires_condition):
                    continue
            # Capability match
            matches = False
            for capability in scanner.capabilities:
                if target_type not in capability.supported_targets:
                    continue
                if scan_types and capability.scan_type not in scan_types:
                    continue
                matches = True
                break
            if matches:
                scanners.append(scanner)
        return sorted(scanners, key=lambda s: s.priority)

    @classmethod
    def get_scanners_for_type(cls, scan_type: ScanType) -> List[Scanner]:
        """
        Get all enabled scanners that support the given scan type.

        Args:
            scan_type: Scan type to filter scanners by.

        Returns:
            List of scanners that advertise the scan type.
        """
        scanners = []
        for scanner in cls._scanners.values():
            if not scanner.enabled:
                continue
            for capability in scanner.capabilities:
                if capability.scan_type == scan_type:
                    scanners.append(scanner)
                    break
        return sorted(scanners, key=lambda s: s.priority)
    
    @classmethod
    def get_total_steps(
        cls, 
        target_type: TargetType,
        scan_types: Optional[List[ScanType]],
        has_git_clone: bool, 
        collect_metadata: bool,
        conditions: Optional[Dict[str, any]] = None
    ) -> int:
        """
        Dynamically calculate total number of steps for a scan
        
        Args:
            scan_type: The scan type
            has_git_clone: Whether Git clone step is needed
            collect_metadata: Whether metadata collection is enabled
            conditions: Optional conditions for conditional scanners
        """
        steps = 0
        
        if has_git_clone:
            steps += 1  # Git Clone
        
        steps += 1  # Initialization
        
        # Count scanners for this scan type/target
        scanners = cls.get_scanners_for_target(target_type, scan_types, conditions)
        steps += len(scanners)
        
        if collect_metadata:
            steps += 1  # Metadata Collection
        
        steps += 1  # Completion
        
        return steps
    
    @classmethod
    def get_all_scanners(cls) -> List[Scanner]:
        """Get all registered scanners"""
        return list(cls._scanners.values())
    
    @classmethod
    def get_scanner(cls, name: str) -> Optional[Scanner]:
        """Get a specific scanner by name"""
        return cls._scanners.get(name)
    
    @classmethod
    def register_from_class(cls, scanner_class):
        """
        Register a scanner from its class (auto-discovery)
        
        Args:
            scanner_class: Scanner class that inherits from BaseScanner
        """
        # Get scanner name from class name (e.g., SemgrepScanner -> Semgrep)
        # Allow explicit override via SCANNER_NAME/NAME for registry-safe IDs
        class_name = scanner_class.__name__
        scanner_name = (
            getattr(scanner_class, "SCANNER_NAME", None)
            or getattr(scanner_class, "NAME", None)
            or class_name.replace("Scanner", "").replace("OWASP", "OWASP Dependency Check")
        )
        
        # Get metadata from class attributes
        capabilities = getattr(scanner_class, "CAPABILITIES", [])
        priority = getattr(scanner_class, "PRIORITY", 0)
        requires_condition = getattr(scanner_class, "REQUIRES_CONDITION", None)
        script_path = getattr(scanner_class, "SCRIPT_PATH", None)
        module = scanner_class.__module__
        python_class = f"{module}.{class_name}"
                
        # Create and register Scanner
        scanner = Scanner(
            name=scanner_name,
            capabilities=capabilities,
            script_path=script_path,
            priority=priority,
            requires_condition=requires_condition,
            python_class=python_class
        )
        
        cls.register(scanner)


# Auto-register all scanners on import
def _register_all_scanners():
    """Register all scanners - add new scanners here!"""
    BASE_DIR = "/SimpleSecCheck"
    TOOLS_DIR = f"{BASE_DIR}/scripts/tools"
    
    # === CODE SCANNERS ===
  

# Auto-register on import (legacy manual registration - will be replaced by auto-registration)
# This is kept as fallback for scanners that don't have metadata yet
_register_all_scanners()

# Auto-discover Python scanner classes (dynamic registration)
try:
    import scanner.scanners  # noqa: F401
except Exception:
    try:
        import scanners  # type: ignore # noqa: F401
    except Exception:
        pass
