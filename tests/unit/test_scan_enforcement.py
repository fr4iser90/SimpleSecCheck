"""Unit tests for scan policy pattern matching."""
import pytest

from application.services.scan_enforcement import _target_matches_blocked_pattern


@pytest.mark.parametrize(
    "target,pattern,expect",
    [
        ("https://evil.com/x", "https://evil.com/*", True),
        ("https://good.com", "https://evil.com/*", False),
        ("file:///etc/passwd", "file://*", True),
        ("https://x.com", "regex:https://[a-z]+\\.com", True),
        ("ftp://x.com", "regex:^https://", False),
    ],
)
def test_blocked_patterns(target, pattern, expect):
    assert _target_matches_blocked_pattern(target, pattern) is expect
