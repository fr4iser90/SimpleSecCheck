"""Contract: every production plugin manifest defines scan_profiles quick / standard / deep."""
from __future__ import annotations

from pathlib import Path
from typing import List

import pytest

REQUIRED_PROFILES = ("quick", "standard", "deep")
# Template-only; no scanner plugin
SKIP_PLUGINS = frozenset({"base"})


def _plugin_manifest_paths() -> List[Path]:
    root = Path(__file__).resolve().parents[2] / "scanner" / "plugins"
    out = sorted(root.glob("*/manifest.yaml"))
    return [p for p in out if p.parent.name not in SKIP_PLUGINS]


@pytest.mark.parametrize(
    "manifest_path",
    _plugin_manifest_paths(),
    ids=lambda p: p.parent.name,
)
def test_manifest_scan_profiles_contract(manifest_path: Path) -> None:
    yaml = pytest.importorskip("yaml", reason="PyYAML required for manifest contract tests")
    raw = manifest_path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    plugin_id = data.get("id") or manifest_path.parent.name

    sp = data.get("scan_profiles")
    assert isinstance(sp, dict), f"{plugin_id}: scan_profiles must be a mapping"

    for name in REQUIRED_PROFILES:
        assert name in sp, f"{plugin_id}: scan_profiles missing {name!r}"
        prof = sp[name]
        assert isinstance(prof, dict), f"{plugin_id}: scan_profiles[{name!r}] must be a mapping"
        if "timeout" in prof:
            t = prof["timeout"]
            assert isinstance(t, int), f"{plugin_id}: scan_profiles[{name!r}].timeout must be int"
            assert 30 <= t <= 86400, (
                f"{plugin_id}: scan_profiles[{name!r}].timeout must be 30–86400, got {t}"
            )
        if "env" in prof and prof["env"] is not None:
            assert isinstance(prof["env"], dict), (
                f"{plugin_id}: scan_profiles[{name!r}].env must be a mapping or omitted"
            )


def test_at_least_one_plugin_manifest_exists() -> None:
    paths = _plugin_manifest_paths()
    assert len(paths) >= 5, "expected multiple scanner/plugins/*/manifest.yaml files"
