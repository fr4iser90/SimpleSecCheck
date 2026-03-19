"""Re-export for API code; implementation lives in domain (no circular imports)."""
from domain.datetime_serialization import isoformat_utc

__all__ = ["isoformat_utc"]
