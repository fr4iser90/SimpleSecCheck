"""Tests for plugin manifest exit_codes lookup used by BaseScanner.run_command."""
from pathlib import Path

import pytest

from scanner.core.manifest_exit_codes import (
    lookup_exit_description,
    plugin_manifest_path_from_class,
)


class _FakeSemgrep:
    __module__ = "scanner.plugins.semgrep.scanner"


class _FakeOwasp:
    __module__ = "scanner.plugins.owasp.scanner"


def test_plugin_manifest_path_from_class():
    p = plugin_manifest_path_from_class(_FakeSemgrep)
    assert p is not None
    assert p.name == "manifest.yaml"
    assert p.parent.name == "semgrep"


def test_lookup_semgrep_exit_2():
    root = Path(__file__).resolve().parents[2] / "scanner" / "plugins" / "semgrep" / "manifest.yaml"
    if not root.is_file():
        pytest.skip("semgrep manifest not found")
    desc, note, has_codes = lookup_exit_description(root, ["semgrep", "scan", "."], 2)
    assert has_codes
    assert desc and "Fatal" in desc
    assert note is None


def test_lookup_owasp_exit_14():
    root = Path(__file__).resolve().parents[2] / "scanner" / "plugins" / "owasp" / "manifest.yaml"
    if not root.is_file():
        pytest.skip("owasp manifest not found")
    desc, _, has_codes = lookup_exit_description(
        root, ["dependency-check", "--version"], 14
    )
    assert has_codes
    assert desc and "OSS Index" in desc


def test_binary_mismatch_skips():
    root = Path(__file__).resolve().parents[2] / "scanner" / "plugins" / "semgrep" / "manifest.yaml"
    if not root.is_file():
        pytest.skip("semgrep manifest not found")
    desc, note, has_codes = lookup_exit_description(root, ["pip3", "install", "x"], 1)
    assert desc is None and note is None and not has_codes
