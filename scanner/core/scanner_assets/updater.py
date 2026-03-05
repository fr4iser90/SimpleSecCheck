"""
Scanner Assets Updater
Runs asset update commands (e.g., OWASP DB update) in Docker
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Optional

from .models import ScannerAsset


class ScannerAssetUpdater:
    def __init__(self, docker_image: str):
        self.docker_image = docker_image

    def build_update_command(
        self,
        asset: ScannerAsset,
        host_asset_path: Path,
        extra_env: Optional[List[str]] = None,
    ) -> List[str]:
        if not asset.update or not asset.update.enabled:
            raise ValueError("Asset update is not enabled")

        cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{host_asset_path}:{asset.mount.container_path}",
        ]

        if extra_env:
            for env in extra_env:
                cmd.extend(["-e", env])

        cmd.append(self.docker_image)
        cmd.extend(asset.update.command)
        return cmd

    def run_update(
        self,
        asset: ScannerAsset,
        host_asset_path: Path,
        extra_env: Optional[List[str]] = None,
    ) -> int:
        cmd = self.build_update_command(asset, host_asset_path, extra_env)
        host_asset_path.mkdir(parents=True, exist_ok=True)
        process = subprocess.run(cmd, capture_output=False, text=True)
        return process.returncode
