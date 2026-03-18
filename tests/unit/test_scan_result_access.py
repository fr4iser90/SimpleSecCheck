"""Tests for scan result access (owner, shared users, share token)."""

from domain.services.scan_result_access import can_read_scan_results, is_scan_owner


def test_owner_user():
    assert is_scan_owner(
        metadata={},
        scan_user_id="550e8400-e29b-41d4-a716-446655440000",
        actor_user_id="550e8400-e29b-41d4-a716-446655440000",
        actor_session_id=None,
        actor_is_authenticated=True,
    )


def test_guest_owner():
    assert is_scan_owner(
        metadata={"session_id": "g1"},
        scan_user_id=None,
        actor_user_id=None,
        actor_session_id="g1",
        actor_is_authenticated=False,
    )


def test_read_shared_user():
    meta = {"report_shared_with_user_ids": ["660e8400-e29b-41d4-a716-446655440001"]}
    assert can_read_scan_results(
        metadata=meta,
        scan_user_id="550e8400-e29b-41d4-a716-446655440000",
        actor_user_id="660e8400-e29b-41d4-a716-446655440001",
        actor_session_id=None,
        actor_is_authenticated=True,
    )


def test_read_share_token():
    assert can_read_scan_results(
        metadata={"report_share_token": "x" * 16},
        scan_user_id=None,
        actor_user_id=None,
        actor_session_id=None,
        actor_is_authenticated=False,
        share_token_query="x" * 16,
    )


def test_stranger_denied():
    assert not can_read_scan_results(
        metadata={},
        scan_user_id="550e8400-e29b-41d4-a716-446655440000",
        actor_user_id="660e8400-e29b-41d4-a716-446655440001",
        actor_session_id=None,
        actor_is_authenticated=True,
    )
