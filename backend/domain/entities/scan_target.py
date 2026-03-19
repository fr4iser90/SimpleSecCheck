"""
ScanTarget entity – single source of truth for saved/user targets.

Target → ScanJob (existing Scan) → Scanner → Results.
source = primary identifier (URL, path, image name); config = type-specific options.
type must be a valid TargetType value (system-level contract).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from domain.entities.target_type import TargetType
from domain.value_objects.auto_scan_config import AutoScanConfig


def _validate_target_type(value: str) -> None:
    """Raise ValueError if value is not a valid TargetType. Keeps ScanTarget.type bound to TargetType."""
    if not value or not value.strip():
        raise ValueError("Target type is required")
    if not TargetType.is_valid(value.strip()):
        raise ValueError(
            f"Invalid target type: {value!r}. Valid types: {', '.join(TargetType.get_all_values())}"
        )


@dataclass
class ScanTarget:
    """User-saved scan target. type + source + config; auto_scan optional. type = TargetType value."""
    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    type: str = ""  # Must be TargetType value: git_repo | container_registry | local_mount | ...
    source: str = ""  # primary identifier: repo URL, image name, path
    display_name: str = ""

    auto_scan: AutoScanConfig = field(default_factory=AutoScanConfig)
    config: Dict[str, Any] = field(default_factory=dict)  # validated per type (GitTargetConfig etc.)

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "source": self.source,
            "display_name": self.display_name or self.source,
            "auto_scan": self.auto_scan.to_dict(),
            "config": self.config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScanTarget":
        created = data.get("created_at")
        updated = data.get("updated_at")
        if isinstance(created, str):
            created = datetime.fromisoformat(created.replace("Z", "+00:00")) if created else datetime.utcnow()
        elif created is None:
            created = datetime.utcnow()
        if isinstance(updated, str):
            updated = datetime.fromisoformat(updated.replace("Z", "+00:00")) if updated else datetime.utcnow()
        elif updated is None:
            updated = datetime.utcnow()
        return cls(
            id=str(data.get("id", uuid4())),
            user_id=str(data.get("user_id", "")),
            type=str(data.get("type", "")),
            source=str(data.get("source", "")),
            display_name=str(data.get("display_name", "")),
            auto_scan=AutoScanConfig.from_dict(data.get("auto_scan") or {}),
            config=dict(data.get("config") or {}),
            created_at=created or datetime.utcnow(),
            updated_at=updated or datetime.utcnow(),
        )
