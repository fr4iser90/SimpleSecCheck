"""
Auto-scan configuration for a saved target.

mode: interval = time-based (e.g. every 6h) – supported by scheduler.
      event   = event-based (push, webhook) – to be wired later via webhooks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Literal

# Event types (for event-based auto-scan)
AutoScanEvent = Optional[Literal["push", "webhook"]]
AutoScanMode = Literal["interval", "event"]


@dataclass
class AutoScanConfig:
    """Auto-scan settings for a target."""
    enabled: bool = False
    mode: AutoScanMode = "interval"  # "interval" | "event"
    interval_seconds: Optional[int] = None  # for mode=interval (e.g. 21600 = 6h)
    event: AutoScanEvent = None  # for mode=event: "push" | "webhook" | None

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "mode": self.mode,
            "interval_seconds": self.interval_seconds,
            "event": self.event,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AutoScanConfig":
        if not data:
            return cls()
        return cls(
            enabled=bool(data.get("enabled", False)),
            mode=data.get("mode") or "interval",
            interval_seconds=data.get("interval_seconds"),
            event=data.get("event"),
        )
