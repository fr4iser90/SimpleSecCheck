"""Manifest-driven asset bootstrap (no hardcoded plugin names)."""
from __future__ import annotations

from pathlib import Path

import pytest

from scanner.core.asset_bootstrap import run_bootstrap_assets


def _write_minimal_manifest(plugins: Path, plugin_id: str, *, with_update: bool) -> None:
    d = plugins / plugin_id
    d.mkdir(parents=True)
    upd = ""
    if with_update:
        upd = """
  update:
    enabled: true
    command:
    - python3
    - -c
    - pass
"""
    body = f"""id: {plugin_id}
version: '1.0'
display_name: Stub
description: test
categories: []
install: []
assets:
- id: data
  type: data
  description: test
  mount:
    host_subpath: scanner/plugins/{plugin_id}/data
    container_path: /tmp/{plugin_id}_data
{upd}
scan_profiles:
  quick:
    timeout: 30
  standard:
    timeout: 30
  deep:
    timeout: 30
"""
    (d / "manifest.yaml").write_text(body, encoding="utf-8")


def test_bootstrap_no_updates_is_ok(tmp_path: Path) -> None:
    plugins = tmp_path / "plugins"
    _write_minimal_manifest(plugins, "stub_a", with_update=False)
    assert run_bootstrap_assets(scanners_root=plugins) == 0


def test_bootstrap_runs_enabled_command(tmp_path: Path) -> None:
    plugins = tmp_path / "plugins"
    _write_minimal_manifest(plugins, "stub_b", with_update=True)
    assert run_bootstrap_assets(scanners_root=plugins, timeout_seconds=30) == 0


def test_bootstrap_failure_nonzero(tmp_path: Path) -> None:
    plugins = tmp_path / "plugins"
    d = plugins / "stub_fail"
    d.mkdir(parents=True)
    manifest = """id: stub_fail
version: '1.0'
display_name: Stub
description: test
categories: []
install: []
assets:
- id: data
  type: data
  description: test
  mount:
    host_subpath: x
    container_path: /tmp/x
  update:
    enabled: true
    command:
    - python3
    - -c
    - import sys; sys.exit(42)
scan_profiles:
  quick:
    timeout: 30
  standard:
    timeout: 30
  deep:
    timeout: 30
"""
    (d / "manifest.yaml").write_text(manifest, encoding="utf-8")
    assert run_bootstrap_assets(scanners_root=plugins, timeout_seconds=30) == 1


def test_substitute_container_path_in_command(tmp_path: Path) -> None:
    plugins = tmp_path / "plugins"
    d = plugins / "stub_sub"
    d.mkdir(parents=True)
    manifest = """id: stub_sub
version: '1.0'
display_name: Stub
description: test
categories: []
install: []
assets:
- id: data
  type: data
  description: test
  mount:
    host_subpath: x
    container_path: /tmp/mounted_here
  update:
    enabled: true
    command:
    - python3
    - -c
    - import os,sys; sys.exit(0 if os.environ.get('MOUNT')=='/tmp/mounted_here' else 1)
    env:
      MOUNT: '{container_path}'
scan_profiles:
  quick:
    timeout: 30
  standard:
    timeout: 30
  deep:
    timeout: 30
"""
    (d / "manifest.yaml").write_text(manifest, encoding="utf-8")
    assert run_bootstrap_assets(scanners_root=plugins, timeout_seconds=30) == 0
