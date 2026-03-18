"""Redis keys for guest sessions (issued / admin revoke)."""

TTL_SECONDS = 86400 * 30  # align with session_id cookie max_age


def issued_key(session_id: str) -> str:
    return f"guest:session:issued:{session_id}"


def revoked_key(session_id: str) -> str:
    return f"guest:session:revoked:{session_id}"
