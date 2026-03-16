"""
Scanner Assets Models
Defines data structures for scanner asset manifests
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class AssetMount:
    host_subpath: str
    container_path: str


@dataclass
class AssetUpdate:
    enabled: bool
    command: List[str]


@dataclass
class ScannerAsset:
    id: str
    type: str
    description: Optional[str]
    mount: AssetMount
    update: Optional[AssetUpdate]


@dataclass
class ScannerManifest:
    """Manifest for a scanner plugin. Identity, capabilities, and UI metadata – execution stays in code."""
    # Identity (required)
    name: str
    assets: List[ScannerAsset]
    install: List[List[str]]
    raw: Dict[str, Any]

    # Identity (optional, recommended for enterprise)
    version: Optional[str] = None

    # Capabilities – orchestration, scoring, filtering
    languages: Optional[List[str]] = None  # e.g. ["python"] – project detector can skip if repo irrelevant
    severity_supported: Optional[bool] = None  # False for tools like gitleaks that don't emit severity
    severity_map: Optional[Dict[str, str]] = None  # e.g. {"ERROR": "HIGH", "WARNING": "MEDIUM"}
    category: Optional[str] = None  # code | dependency | secrets | container | iac | web – for domain scoring

    # Execution hints (optional)
    timeout: Optional[int] = None  # seconds; orchestrator can enforce

    # UI / registry metadata
    display_name: Optional[str] = None
    description: Optional[str] = None
    categories: Optional[List[str]] = None
    icon: Optional[str] = None
    homepage: Optional[str] = None
    documentation: Optional[str] = None
