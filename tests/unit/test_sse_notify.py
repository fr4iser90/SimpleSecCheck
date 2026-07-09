"""Unit tests for SSE notify helpers."""
from infrastructure.realtime.sse_notify import GUEST_SSE_PREFIX, sse_subscriber_key


def test_sse_subscriber_key_user():
    assert sse_subscriber_key("user-1") == "user-1"
    assert sse_subscriber_key("user-1", "guest-sess") == "user-1"


def test_sse_subscriber_key_guest():
    assert sse_subscriber_key(None, "abc-session") == f"{GUEST_SSE_PREFIX}abc-session"


def test_sse_subscriber_key_empty():
    assert sse_subscriber_key(None, None) is None
    assert sse_subscriber_key("", "") is None
