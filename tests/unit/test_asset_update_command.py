"""Asset update jobs must write into the mounted cache dir, not a literal {container_path}."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_MOUNT = "/app/scanner/plugins/owasp/data"


def test_command_placeholder_replaced_with_mount_path():
    from worker.api.scanner_api import _render_asset_update_command

    rendered = _render_asset_update_command(
        ["dependency-check", "--updateonly", "--data", "{container_path}"],
        container_path=_MOUNT,
    )

    assert rendered == ["dependency-check", "--updateonly", "--data", _MOUNT]
    assert not any("{container_path}" in arg for arg in rendered)


def test_env_placeholder_replaced_and_declared_host_env_copied():
    from worker.api.scanner_api import _render_asset_update_env

    with patch.dict("os.environ", {"NVD_API_KEY": "nvd-test-key"}, clear=False):
        env = _render_asset_update_env(
            {"TRIVY_CACHE_DIR": "{container_path}"},
            container_path="/app/scanner/plugins/trivy/data",
            env_from_host=["NVD_API_KEY"],
        )

    assert env == {
        "TRIVY_CACHE_DIR": "/app/scanner/plugins/trivy/data",
        "NVD_API_KEY": "nvd-test-key",
    }


def test_declared_host_env_is_omitted_when_unset_not_passed_empty():
    from worker.api.scanner_api import _render_asset_update_env

    with patch.dict("os.environ", {}, clear=True):
        env = _render_asset_update_env(None, container_path=_MOUNT, env_from_host=["NVD_API_KEY"])

    assert env == {}


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({}, 1800),
        ({"timeout_seconds": "3600"}, 3600),
        ({"timeout_seconds": 5}, 60),
        ({"timeout_seconds": 99999}, 7200),
        ({"timeout_seconds": "not-a-number"}, 1800),
    ],
)
def test_asset_update_timeout_default_and_clamp(payload, expected):
    from worker.api.scanner_api import _asset_update_timeout

    assert _asset_update_timeout(payload) == expected


def test_owasp_manifest_declares_nvd_passthrough_and_longer_timeout():
    from scanner.core.scanner_assets.manager import ScannerAssetsManager

    asset = ScannerAssetsManager(_REPO / "scanner" / "plugins").get_asset("owasp", "data")

    assert asset is not None and asset.update is not None
    assert asset.update.enabled is True
    assert asset.update.timeout_seconds == 3600
    assert "NVD_API_KEY" in (asset.update.env_from_host or [])
    assert "{container_path}" in asset.update.command


def test_trivy_manifest_targets_cache_dir_at_its_mount():
    from scanner.core.scanner_assets.manager import ScannerAssetsManager

    asset = ScannerAssetsManager(_REPO / "scanner" / "plugins").get_asset("trivy", "cache")

    assert asset is not None and asset.update is not None
    assert asset.update.env == {"TRIVY_CACHE_DIR": "{container_path}"}
    assert asset.mount.container_path == "/app/scanner/plugins/trivy/data"
