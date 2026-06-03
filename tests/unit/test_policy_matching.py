#!/usr/bin/env python3
import pytest

from scanner.core.policy_matching import matches_path_for_policy, normalize_policy_path


@pytest.mark.parametrize(
    "path,expected",
    [
        ("backend/x.py", "backend/x.py"),
        ("/target/backend/x.py", "backend/x.py"),
        ("/app/target/backend/x.py", "backend/x.py"),
        ("\\target\\backend\\x.py", "backend/x.py"),
    ],
)
def test_normalize_policy_path(path, expected):
    assert normalize_policy_path(path) == expected


@pytest.mark.parametrize(
    "path,regex",
    [
        ("backend/api.py", r"backend/.*"),
        ("/target/backend/api.py", r"backend/.*"),
        ("/app/target/backend/api.py", r"backend/.*"),
    ],
)
def test_matches_path_for_policy_with_mount_prefix(path, regex):
    assert matches_path_for_policy(path, regex) is True


def test_matches_path_for_policy_none_regex():
    assert matches_path_for_policy("any/path", None) is True
