"""API key format and hashing (shared by routes and auth)."""
import hashlib
import secrets


API_KEY_PREFIX = "ssc_"


def is_api_key_token(token: str) -> bool:
    """True if the bearer token looks like a SimpleSecCheck API key."""
    t = (token or "").strip()
    return t.startswith(API_KEY_PREFIX) and len(t) > len(API_KEY_PREFIX) + 8


def generate_api_key(user_id: str) -> str:
    """Generate a new API key plain text."""
    random_part = secrets.token_urlsafe(32)
    return f"{API_KEY_PREFIX}{user_id[:8]}_{random_part}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage (SHA-256 hex)."""
    return hashlib.sha256(api_key.encode()).hexdigest()
