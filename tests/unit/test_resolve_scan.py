"""Unit tests for resolve-scan URL matching."""
import importlib.util
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


def _load_git_repo_url():
    spec = importlib.util.spec_from_file_location(
        "git_repo_url",
        _BACKEND / "domain" / "utils" / "git_repo_url.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_repo_urls_match_with_and_without_git():
    mod = _load_git_repo_url()
    assert mod.repo_urls_match(
        "https://github.com/org/repo",
        "https://github.com/org/repo.git",
    )


def test_repo_urls_match_case_insensitive():
    mod = _load_git_repo_url()
    assert mod.repo_urls_match(
        "HTTPS://GitHub.com/Org/Repo.git",
        "https://github.com/org/repo",
    )
