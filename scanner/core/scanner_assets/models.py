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
    name: str
    assets: List[ScannerAsset]
    install: List[List[str]]
    raw: Dict[str, Any]
