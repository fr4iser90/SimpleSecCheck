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
    """Manifest: id is the ONLY technical identity (tools_key). No manifest name field."""
    id: str
    assets: List[ScannerAsset]
    install: List[List[str]]
    raw: Dict[str, Any]

    version: Optional[str] = None
    languages: Optional[List[str]] = None  # None = all languages
    severity_supported: Optional[bool] = None
    severity_map: Optional[Dict[str, str]] = None
    timeout: Optional[int] = None  # seconds; from execution.timeout in YAML

    display_name: Optional[str] = None
    description: Optional[str] = None
    categories: Optional[List[str]] = None
    icon: Optional[str] = None
    homepage: Optional[str] = None
    documentation: Optional[str] = None
