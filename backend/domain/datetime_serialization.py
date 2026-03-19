"""UTC ISO-8601 strings with explicit 'Z' for JSON/API (correct JS Date parsing)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def isoformat_utc(dt: Optional[datetime]) -> Optional[str]:
    """
    Naive datetimes are treated as UTC (matches datetime.utcnow() usage in this codebase).
    Aware datetimes are converted to UTC. Result always ends with 'Z'.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        utc = dt.replace(tzinfo=timezone.utc)
    else:
        utc = dt.astimezone(timezone.utc)
    return utc.isoformat().replace("+00:00", "Z")


def parse_api_datetime(s: str) -> datetime:
    """
    Parse ISO strings from API/Redis. 'Z' suffix supported; naive strings are treated as UTC.
    """
    if not s:
        raise ValueError("empty datetime string")
    normalized = s.replace("Z", "+00:00") if s.endswith("Z") else s
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
