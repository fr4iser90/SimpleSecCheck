"""
Manifest-driven asset bootstrap: run optional `assets[].update` commands for each plugin.
No hardcoded plugin ids — discovers all scanner/plugins/*/manifest.yaml via ScannerAssetsManager.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from scanner.core.scanner_assets.manager import ScannerAssetsManager
from scanner.core.scanner_assets.models import AssetMount

logger = logging.getLogger(__name__)


def _plugins_root() -> Path:
    env = os.getenv("SCANNER_PLUGINS_ROOT", "").strip()
    if env:
        return Path(env)
    root = os.getenv("SCANNER_ROOT", "/app/scanner").strip() or "/app/scanner"
    return Path(root) / "plugins"


def _substitute(value: str, mount: AssetMount) -> str:
    return (
        str(value)
        .replace("{container_path}", mount.container_path)
        .replace("{host_subpath}", mount.host_subpath)
    )


def run_bootstrap_assets(
    scanners_root: Optional[Path] = None,
    timeout_seconds: Optional[int] = None,
) -> int:
    """
    Run every enabled asset update command (sorted by manifest id).

    Returns 0 if all steps succeeded, 1 if any step failed or plugins root missing.
    """
    root = scanners_root or _plugins_root()
    if not root.is_dir():
        print(f"[bootstrap] ERROR: plugins root not found: {root}", file=sys.stderr)
        return 1

    if timeout_seconds is None:
        try:
            timeout_seconds = int(os.getenv("SIMPLESECCHECK_BOOTSTRAP_TIMEOUT_SEC", "900"))
        except (TypeError, ValueError):
            timeout_seconds = 900

    manager = ScannerAssetsManager(root)
    manifests = sorted(manager.load_manifests().values(), key=lambda m: m.id)
    failures = 0
    ran = 0

    for manifest in manifests:
        for asset in manifest.assets:
            upd = asset.update
            if not upd or not upd.enabled or not upd.command:
                continue
            cmd = [_substitute(c, asset.mount) for c in upd.command]
            env = os.environ.copy()
            if upd.env:
                for k, v in upd.env.items():
                    env[str(k)] = _substitute(str(v), asset.mount)

            label = f"{manifest.id}/{asset.id}"
            print(f"[bootstrap] {label}: {' '.join(cmd)}", flush=True)
            ran += 1
            try:
                result = subprocess.run(
                    cmd,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )
            except subprocess.TimeoutExpired:
                print(
                    f"[bootstrap] {label}: TIMEOUT after {timeout_seconds}s",
                    file=sys.stderr,
                )
                failures += 1
                continue
            except OSError as e:
                print(f"[bootstrap] {label}: {e}", file=sys.stderr)
                failures += 1
                continue

            if result.returncode != 0:
                err = (result.stderr or result.stdout or "").strip()
                tail = err[-4000:] if len(err) > 4000 else err
                print(
                    f"[bootstrap] {label}: exit {result.returncode}\n{tail}",
                    file=sys.stderr,
                )
                failures += 1
            else:
                print(f"[bootstrap] {label}: ok", flush=True)

    if ran == 0:
        print("[bootstrap] no assets with update.enabled (nothing to do)", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(run_bootstrap_assets())
