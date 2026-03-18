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
                if manifest.id in manifests:
                    raise ValueError(
                        f"Duplicate manifest id {manifest.id!r}: {manifest_path} vs existing"
                    )
                manifests[manifest.id] = manifest
        return manifests

    def list_assets(self) -> List[ScannerAsset]:
        assets: List[ScannerAsset] = []
        for manifest in self.load_manifests().values():
            assets.extend(manifest.assets)
        return assets

    def get_manifest(self, plugin_id: str) -> Optional[ScannerManifest]:
        """plugin_id must match manifest id (and plugin folder name)."""
        return self.load_manifests().get(plugin_id)

    def get_asset(self, plugin_id: str, asset_id: str) -> Optional[ScannerAsset]:
        manifest = self.get_manifest(plugin_id)
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

    def get_display_name(self, plugin_id: str) -> str:
        manifest = self.get_manifest(plugin_id)
        if not manifest:
            return plugin_id
        return (manifest.display_name or plugin_id).strip() or plugin_id

    def _load_manifest_file(self, manifest_path: Path) -> Optional[ScannerManifest]:
        try:
            data = yaml.safe_load(manifest_path.read_text()) or {}
        except Exception:
            return None

        plugin_dir = manifest_path.parent.name
        scanner_id = data.get("id")
        if scanner_id is not None:
            scanner_id = str(scanner_id).strip()
        if not scanner_id:
            return None
        if scanner_id != plugin_dir:
            # Single source: id must match plugin directory
            return None

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

        install_commands: List[List[str]] = []
        if isinstance(install_data, list):
            for command in install_data:
                if isinstance(command, list) and command:
                    install_commands.append([str(item) for item in command])
                elif isinstance(command, str) and command.strip():
                    install_commands.append([command])

        description = data.get("description") or None
        if description is not None:
            description = str(description).strip() or None
        categories = data.get("categories")
        if categories is not None and not isinstance(categories, list):
            categories = [str(categories)] if categories else None
        if categories is not None:
            categories = [str(c).strip().lower() for c in categories if c]
        icon = data.get("icon")
        if icon is not None:
            icon = str(icon).strip() or None
        display_name = data.get("display_name")
        if display_name is not None:
            display_name = str(display_name).strip() or None

        version = data.get("version")
        if version is not None:
            version = str(version).strip() or None

        languages = data.get("languages")
        if languages is None:
            languages = None  # all
        elif isinstance(languages, list):
            if not languages:
                languages = None
            else:
                languages = [str(l).strip() for l in languages if l]
        else:
            languages = [str(languages).strip()] if str(languages).strip() else None

        severity_supported = data.get("severity_supported")
        if severity_supported is not None and not isinstance(severity_supported, bool):
            severity_supported = None
        severity_map = data.get("severity_map")
        if severity_map is not None and isinstance(severity_map, dict):
            severity_map = {str(k).strip(): str(v).strip() for k, v in severity_map.items() if k and v}
        else:
            severity_map = None

        timeout = None
        ex = data.get("execution")
        if isinstance(ex, dict) and ex.get("timeout") is not None:
            try:
                t = int(ex["timeout"])
                if t > 0:
                    timeout = t
            except (TypeError, ValueError):
                pass

        homepage = data.get("homepage")
        if homepage is not None:
            homepage = str(homepage).strip() or None
        documentation = data.get("documentation")
        if documentation is not None:
            documentation = str(documentation).strip() or None

        return ScannerManifest(
            id=scanner_id,
            assets=assets,
            install=install_commands,
            raw=data,
            version=version,
            languages=languages,
            severity_supported=severity_supported,
            severity_map=severity_map,
            timeout=timeout,
            display_name=display_name,
            description=description,
            categories=categories,
            icon=icon,
            homepage=homepage,
            documentation=documentation,
        )


def get_plugin_display_name(plugin_id: str, scanners_root: Optional[Path] = None) -> str:
    root = scanners_root or Path(__file__).resolve().parent.parent.parent / "plugins"
    if not root.exists():
        return plugin_id
    try:
        manager = ScannerAssetsManager(root)
        return manager.get_display_name(plugin_id)
    except Exception:
        return plugin_id
