"""Tests for Git web URL -> clone URL normalization."""
import pytest

from domain.utils.git_repo_url import (
    normalize_git_repo_url,
    normalize_repo_url_for_target_type,
)
from domain.entities.target_type import TargetType


@pytest.mark.parametrize(
    "raw,expected",
    [
        (
            "https://github.com/foo/bar/tree/develop/src",
            "https://github.com/foo/bar.git",
        ),
        (
            "https://github.com/foo/bar",
            "https://github.com/foo/bar.git",
        ),
        (
            "https://github.com/foo/bar.git",
            "https://github.com/foo/bar.git",
        ),
        (
            "https://www.github.com/foo/bar",
            "https://github.com/foo/bar.git",
        ),
        (
            "https://gitlab.com/group/subgroup/proj/-/blob/main/README.md",
            "https://gitlab.com/group/subgroup/proj.git",
        ),
    ],
)
def test_normalize_git_repo_url(raw: str, expected: str) -> None:
    assert normalize_git_repo_url(raw) == expected


def test_normalize_only_for_git_target_type() -> None:
    u = "https://github.com/a/b/blob/main/x"
    assert normalize_repo_url_for_target_type(TargetType.GIT_REPO.value, u) == "https://github.com/a/b.git"
    assert normalize_repo_url_for_target_type(TargetType.WEBSITE.value, u) == u
