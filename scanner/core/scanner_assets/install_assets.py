"""
Scanner Assets Installer
Runs install commands declared in scanner manifests.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import List

from .manager import ScannerAssetsManager


def run_command(command: List[str]) -> None:
    """Run a command with shell when needed and fail fast on errors."""
    if not command:
        return
    if len(command) == 1:
        subprocess.run(command[0], shell=True, check=True)
        return
    subprocess.run(command, check=True)


def install_from_manifests(scanners_root: Path) -> None:
    manager = ScannerAssetsManager(scanners_root)
    manifests = list(manager.load_manifests().values())
    manifests.sort(key=lambda manifest: (0 if manifest.name == "base" else 1, manifest.name))
    for manifest in manifests:
        for command in manifest.install:
            run_command(command)


def main() -> None:
    base_dir = Path(os.getenv("SIMPLE_SECCHECK_ROOT", "/app"))
    # Manifests are in plugins/, not scanners/
    scanners_root = base_dir / "scanner" / "plugins"
    install_from_manifests(scanners_root)


if __name__ == "__main__":
    main()