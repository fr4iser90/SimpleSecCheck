"""Scanner entity (from discovery / DB)."""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Scanner:
    """Scanner definition (name, scan types, enabled, metadata)."""
    id: str
    name: str
    scan_types: List[str]
    priority: int
    requires_condition: Optional[str]
    enabled: bool
    scanner_metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    last_discovered_at: Optional[datetime] = None
