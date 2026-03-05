"""
Scanner Assets Manager
Loads scanner manifest files and resolves asset mounts
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional
import yaml

from .models import ScannerManifest, ScannerAsset, AssetMount, AssetUpdate


class ScannerAssetsManager:
    def __init__(self, scanners_root: Path):
        self.scanners_root = scanners_root

    def load_manifests(self) -> Dict[str, ScannerManifest]:
        manifests: Dict[str, ScannerManifest] = {}
        for manifest_path in self.scanners_root.rglob("manifest.yaml"):
            manifest = self._load_manifest_file(manifest_path)
            if manifest:
                manifests[manifest.name] = manifest
        return manifests

    def list_assets(self) -> List[ScannerAsset]:
        assets: List[ScannerAsset] = []
        for manifest in self.load_manifests().values():
            assets.extend(manifest.assets)
        return assets

    def get_manifest(self, scanner_name: str) -> Optional[ScannerManifest]:
        return self.load_manifests().get(scanner_name)

    def get_asset(self, scanner_name: str, asset_id: str) -> Optional[ScannerAsset]:
        manifest = self.get_manifest(scanner_name)
        if not manifest:
            return None
        for asset in manifest.assets:
            if asset.id == asset_id:
                return asset
        return None

    def resolve_host_path(self, host_project_root: Path, asset: ScannerAsset) -> Path:
        host_subpath = asset.mount.host_subpath.strip()
        if not host_subpath:
            return host_project_root
        return host_project_root / host_subpath

    def _load_manifest_file(self, manifest_path: Path) -> Optional[ScannerManifest]:
        try:
            data = yaml.safe_load(manifest_path.read_text()) or {}
        except Exception:
            return None

        name = data.get("name")
        assets_data = data.get("assets", [])
        install_data = data.get("install", [])
        assets: List[ScannerAsset] = []
        for asset_data in assets_data:
            mount_data = asset_data.get("mount", {})
            update_data = asset_data.get("update")

            host_subpath = str(mount_data.get("host_subpath", "") or "").strip()
            container_path = str(mount_data.get("container_path", "") or "").strip()
            mount = AssetMount(
                host_subpath=host_subpath,
                container_path=container_path,
            )
            update = None
            if update_data:
                update = AssetUpdate(
                    enabled=bool(update_data.get("enabled", False)),
                    command=list(update_data.get("command", [])),
                )
            assets.append(
                ScannerAsset(
                    id=str(asset_data.get("id")),
                    type=str(asset_data.get("type")),
                    description=asset_data.get("description"),
                    mount=mount,
                    update=update,
                )
            )

        if not name:
            return None

        install_commands: List[List[str]] = []
        if isinstance(install_data, list):
            for command in install_data:
                if isinstance(command, list) and command:
                    install_commands.append([str(item) for item in command])
                elif isinstance(command, str) and command.strip():
                    install_commands.append([command])

        return ScannerManifest(name=name, assets=assets, install=install_commands, raw=data)
