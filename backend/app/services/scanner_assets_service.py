"""
Scanner Assets Service
Generic asset listing and update handling for scanner manifests
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional

try:
    import sys
    scanner_root = os.getenv("SCANNER_ROOT", "/scanner")
    if scanner_root:
        sys.path.insert(0, scanner_root)

    from core.scanner_assets.manager import ScannerAssetsManager
    from core.scanner_assets.updater import ScannerAssetUpdater
except Exception as exc:
    ScannerAssetsManager = None
    ScannerAssetUpdater = None


def _get_scanners_root() -> Path:
    scanner_root = os.getenv("SCANNER_ROOT", "/scanner")
    if scanner_root:
        return Path(scanner_root) / "scanners"
    return Path("scanner/scanners")


def _format_age(seconds: float) -> str:
    if seconds < 60:
        return "just now"
    minutes = seconds / 60
    if minutes < 60:
        return f"{int(minutes)} min ago"
    hours = minutes / 60
    if hours < 48:
        return f"{int(hours)} h ago"
    days = hours / 24
    return f"{int(days)} d ago"


def _get_asset_last_updated(asset_path: Path) -> Optional[Dict[str, Optional[str]]]:
    if not asset_path.exists():
        return None

    try:
        if asset_path.is_dir():
            mtimes = [p.stat().st_mtime for p in asset_path.rglob("*") if p.is_file()]
            if not mtimes:
                return None
            latest_mtime = max(mtimes)
        else:
            latest_mtime = asset_path.stat().st_mtime
    except Exception:
        return None

    updated_at = datetime.fromtimestamp(latest_mtime, tz=timezone.utc)
    age_seconds = (datetime.now(tz=timezone.utc) - updated_at).total_seconds()

    return {
        "updated_at": updated_at.isoformat(),
        "age_seconds": int(age_seconds),
        "age_human": _format_age(age_seconds),
    }


def list_scanner_assets() -> List[Dict]:
    if not ScannerAssetsManager:
        raise RuntimeError("Scanner assets unavailable in this container")
    manager = ScannerAssetsManager(_get_scanners_root())
    host_project_root = os.getenv("HOST_PROJECT_ROOT")
    if host_project_root:
        host_root = Path(host_project_root)
    elif Path("/project").exists():
        host_root = Path("/project")
    else:
        host_root = Path(os.getenv("SCANNER_ROOT", ".")).resolve()
    assets = []
    for manifest in manager.load_manifests().values():
        for asset in manifest.assets:
            host_asset_path = manager.resolve_host_path(host_root, asset)
            last_updated = _get_asset_last_updated(host_asset_path)
            if not last_updated:
                scanner_root = Path(os.getenv("SCANNER_ROOT", "/scanner"))
                scanner_asset_path = manager.resolve_host_path(scanner_root, asset)
                last_updated = _get_asset_last_updated(scanner_asset_path)
            if not last_updated:
                container_path = Path(asset.mount.container_path)
                last_updated = _get_asset_last_updated(container_path)
            assets.append({
                "scanner": manifest.name,
                "asset": asdict(asset),
                "last_updated": last_updated,
            })
    return assets


def update_scanner_asset(scanner_name: str, asset_id: str) -> Dict:
    if not ScannerAssetsManager or not ScannerAssetUpdater:
        raise RuntimeError("Scanner assets unavailable in this container")
    manager = ScannerAssetsManager(_get_scanners_root())
    asset = manager.get_asset(scanner_name, asset_id)
    if not asset:
        raise ValueError("Asset not found")

    host_project_root = os.getenv("HOST_PROJECT_ROOT")
    if host_project_root:
        host_root = Path(host_project_root)
    else:
        # fallback for local/dev
        host_root = Path(".").resolve()

    host_asset_path = manager.resolve_host_path(host_root, asset)
    docker_image = os.getenv("DOCKER_IMAGE", "fr4iser/simpleseccheck:latest")
    updater = ScannerAssetUpdater(docker_image)
    nvd_api_key = os.getenv("NVD_API_KEY", "")
    extra_env = [f"NVD_API_KEY={nvd_api_key}"] if nvd_api_key else []

    exit_code = updater.run_update(asset, host_asset_path, extra_env=extra_env)
    return {
        "scanner": scanner_name,
        "asset_id": asset_id,
        "exit_code": exit_code,
    }
