"""Shared rolling-window logic for per-scanner duration estimates."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

MAX_SAMPLES = 100


def apply_duration_sample(
    recent: Optional[Sequence[int]],
    duration_seconds: int,
    *,
    max_samples: int = MAX_SAMPLES,
) -> Dict[str, Any]:
    """
    Append a duration sample and compute rolling stats over the last *max_samples* runs.

    Returns dict with recent_durations, avg/min/max (window), window_sample_count.
    """
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive")

    window: List[int] = [int(x) for x in (recent or []) if int(x) > 0]
    window.append(int(duration_seconds))
    if len(window) > max_samples:
        window = window[-max_samples:]

    return {
        "recent_durations": window,
        "avg_duration_seconds": int(sum(window) / len(window)),
        "min_duration_seconds": min(window),
        "max_duration_seconds": max(window),
        "window_sample_count": len(window),
    }


def estimate_total_seconds(
    scanner_names: Sequence[str],
    measured_avgs: Dict[str, int],
) -> Optional[int]:
    """
    Sum rolling averages for all requested scanners.

    Returns None when any scanner has no measured data (no fallbacks).
    """
    cleaned = [(name or "").strip() for name in scanner_names if name and str(name).strip()]
    if not cleaned:
        return None

    total = 0
    for name in cleaned:
        if name not in measured_avgs:
            return None
        total += int(measured_avgs[name])
    return total
