#!/usr/bin/env python3
import subprocess
from pathlib import Path

from scanner.core.command_retry import run_with_retry
from scanner.plugins.codeql.scanner import codeql_pack_cached
from scanner.plugins.trivy.scanner import trivy_db_usable


def test_trivy_db_usable_requires_real_db(tmp_path):
    cache = tmp_path / "cache"
    db_dir = cache / "db"
    db_dir.mkdir(parents=True)
    assert not trivy_db_usable(str(cache))
    (db_dir / "trivy.db").write_bytes(b"x" * (1024 * 1024 + 1))
    assert trivy_db_usable(str(cache))


def test_run_with_retry_succeeds_on_second_attempt():
    calls = {"n": 0}

    def fn(_attempt: int) -> subprocess.CompletedProcess:
        calls["n"] += 1
        code = 0 if calls["n"] >= 2 else 1
        return subprocess.CompletedProcess(["cmd"], code)

    result = run_with_retry(fn, max_attempts=3, delay_seconds=0)
    assert result.returncode == 0
    assert calls["n"] == 2


def test_codeql_pack_cached_detects_version_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEQL_HOME", str(tmp_path))
    pack_root = tmp_path / "packages" / "codeql" / "javascript-queries" / "1.0.0"
    pack_root.mkdir(parents=True)
    assert codeql_pack_cached("codeql/javascript-queries", tmp_path)
    assert not codeql_pack_cached("codeql/java-queries", tmp_path)
