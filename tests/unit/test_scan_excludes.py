#!/usr/bin/env python3
import os

import pytest

from scanner.core.finding_policy import publish_finding_policy_path_to_env
from scanner.core.scan_excludes import (
    ENV_EXCLUDE_PATHS,
    bandit_extra_argv,
    detect_secrets_exclude_argv,
    merged_exclude_list,
    owasp_exclude_argv,
    path_matches_exclude,
    prepare_scan_excludes_env,
    semgrep_exclude_argv,
    trivy_skip_argv,
)


def _fixture_repo(tmp_path, monkeypatch):
    monkeypatch.delenv("FINDING_POLICY_FILE_IN_CONTAINER", raising=False)
    monkeypatch.delenv("FINDING_POLICY_FILE", raising=False)
    target = tmp_path / "repo"
    target.mkdir()
    (target / ".scanning").mkdir()
    (target / ".scanning" / "notes.txt").write_text("x", encoding="utf-8")
    policy = target / ".scanning" / "finding-policy.json"
    policy.write_text("{}", encoding="utf-8")
    return target, policy


def test_policy_file_only_not_dot_scanning_dir(tmp_path, monkeypatch):
    target, policy = _fixture_repo(tmp_path, monkeypatch)
    monkeypatch.setenv(ENV_EXCLUDE_PATHS, "node_modules")

    publish_finding_policy_path_to_env(target)
    patterns = merged_exclude_list(target)
    assert patterns == [".scanning/finding-policy.json", "node_modules"]
    assert path_matches_exclude(target, policy)
    assert not path_matches_exclude(target, target / ".scanning" / "notes.txt")


def test_prepare_scan_excludes_env_merges_once(tmp_path, monkeypatch):
    target, _ = _fixture_repo(tmp_path, monkeypatch)
    monkeypatch.setenv(ENV_EXCLUDE_PATHS, "vendor")

    merged = prepare_scan_excludes_env(target)
    assert ".scanning/finding-policy.json" in merged
    assert "vendor" in merged
    assert os.environ[ENV_EXCLUDE_PATHS] == merged


def test_cli_builders_support_single_file(tmp_path, monkeypatch):
    target, _ = _fixture_repo(tmp_path, monkeypatch)
    monkeypatch.setenv(ENV_EXCLUDE_PATHS, "vendor")
    prepare_scan_excludes_env(target)
    csv = os.environ[ENV_EXCLUDE_PATHS]

    assert "--exclude" in semgrep_exclude_argv(csv)
    assert ".scanning/finding-policy.json" in semgrep_exclude_argv(csv)

    ds = detect_secrets_exclude_argv(csv)
    file_patterns = [a for i, a in enumerate(ds) if i > 0 and ds[i - 1] == "--exclude-files"]
    assert any(".scanning" in a for a in file_patterns)
    assert any("vendor" in a for a in file_patterns)

    owasp = owasp_exclude_argv(csv)
    assert ".scanning/finding-policy.json" in owasp

    trivy = trivy_skip_argv(csv)
    assert any("finding-policy" in a for a in trivy)
    assert any("skip-files" in a for a in trivy)

    bandit = bandit_extra_argv(target)
    assert bandit.count("-x") >= 1


def test_path_matches_exclude_ignores_empty_normalized_patterns(tmp_path, monkeypatch):
    target = tmp_path / "repo"
    target.mkdir()
    monkeypatch.setenv(ENV_EXCLUDE_PATHS, "/target/,/")
    assert not path_matches_exclude(target, target / "src" / "main.py")


def test_base_scanner_helpers(tmp_path, monkeypatch):
    from scanner.plugins.semgrep.scanner import SemgrepScanner

    target, _ = _fixture_repo(tmp_path, monkeypatch)
    prepare_scan_excludes_env(target)
    log = tmp_path / "log.txt"
    log.parent.mkdir(parents=True, exist_ok=True)
    scanner = SemgrepScanner(
        target_path=str(target),
        results_dir=str(tmp_path / "out"),
        log_file=str(log),
    )
    args = scanner.get_exclude_args()
    assert "--exclude" in args
    assert ".scanning/finding-policy.json" in args
