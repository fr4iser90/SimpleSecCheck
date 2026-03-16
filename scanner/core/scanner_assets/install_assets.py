"""
Scanner Assets Installer
Runs install commands declared in scanner manifests.
Optimized to only reinstall tools whose manifests changed.
"""
from __future__ import annotations

import os
import subprocess
import hashlib
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional

from .manager import ScannerAssetsManager


def get_manifest_hash(manifest_path: Path) -> str:
    """Calculate hash of manifest file for change detection."""
    if not manifest_path.exists():
        return ""
    content = manifest_path.read_text()
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def load_manifest_cache(cache_file: Path) -> Dict[str, str]:
    """Load cached manifest hashes."""
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text())
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_manifest_cache(cache_file: Path, cache: Dict[str, str]) -> None:
    """Save manifest hashes to cache."""
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(cache, indent=2))
    except (IOError, OSError):
        pass  # Non-critical, cache is optional


def run_command(command: List[str]) -> None:
    """Run a command with shell when needed and fail fast on errors."""
    if not command:
        return
    if len(command) == 1:
        subprocess.run(command[0], shell=True, check=True)
        return
    subprocess.run(command, check=True)


def install_from_manifests(
    scanners_root: Path,
    cache_file: Optional[Path] = None,
    force_all: bool = False
) -> None:
    """
    Install tools from manifests, only reinstalling changed ones.
    
    Args:
        scanners_root: Root directory containing scanner plugins
        cache_file: Path to cache file for manifest hashes (optional)
        force_all: If True, install all tools regardless of cache
    """
    manager = ScannerAssetsManager(scanners_root)
    manifests = list(manager.load_manifests().values())
    manifests.sort(key=lambda manifest: (0 if manifest.name == "base" else 1, manifest.name))
    
    # Load cache if available
    cache = {}
    if cache_file and not force_all:
        cache = load_manifest_cache(cache_file)
    
    # Track which manifests changed
    changed_manifests = []
    new_cache = {}
    
    for manifest in manifests:
        manifest_path = scanners_root / manifest.name / "manifest.yaml"
        current_hash = get_manifest_hash(manifest_path)
        cached_hash = cache.get(manifest.name, "")
        
        # Always install base, or if manifest changed, or if force_all
        should_install = (
            manifest.name == "base" or
            current_hash != cached_hash or
            cached_hash == "" or
            force_all
        )
        
        if should_install:
            changed_manifests.append(manifest.name)
            print(f"[Install] Installing {manifest.name} (manifest changed or first install)")
            try:
                for command in manifest.install:
                    run_command(command)
            except subprocess.CalledProcessError as e:
                print(
                    f"[Warning] Install failed for {manifest.name}: {e}. Continuing (tool may be optional or installed at runtime).",
                    file=sys.stderr,
                )
        else:
            print(f"[Skip] Skipping {manifest.name} (manifest unchanged)")
        
        new_cache[manifest.name] = current_hash
    
    # Save updated cache
    if cache_file:
        save_manifest_cache(cache_file, new_cache)
    
    if changed_manifests:
        print(f"[Summary] Installed/updated: {', '.join(changed_manifests)}")
    else:
        print("[Summary] No changes detected, using cached installations")


def main() -> None:
    base_dir = Path(os.getenv("SIMPLE_SECCHECK_ROOT", "/app"))
    # Manifests are in plugins/, not scanners/
    scanners_root = base_dir / "scanner" / "plugins"
    
    # Cache file location
    cache_file = base_dir / ".scanner_manifest_cache.json"
    
    # Check if we should force reinstall all (e.g., if cache is disabled)
    force_all = os.getenv("FORCE_REINSTALL_ALL", "false").lower() == "true"
    
    install_from_manifests(scanners_root, cache_file, force_all=force_all)


if __name__ == "__main__":
    main()
