"""Scanner tool settings entity (admin overrides per tools_key)."""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class ScannerToolSettings:
    """Per-scanner override: enabled, timeout_seconds, config (env vars)."""
    scanner_key: str
    enabled: Optional[bool]
    timeout_seconds: Optional[int]
    config: Dict[str, Any]
    updated_at: datetime
    updated_by_user_id: Optional[str] = None
