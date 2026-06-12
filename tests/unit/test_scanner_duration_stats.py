"""Unit tests for shared scanner duration rolling-window logic."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shared.scanner_duration_stats import (  # noqa: E402
    MAX_SAMPLES,
    apply_duration_sample,
    estimate_total_seconds,
)


def test_apply_duration_sample_single():
    result = apply_duration_sample([], 90)
    assert result["avg_duration_seconds"] == 90
    assert result["window_sample_count"] == 1
    assert result["recent_durations"] == [90]


def test_apply_duration_sample_rolling_window():
    recent = list(range(1, MAX_SAMPLES + 1))
    result = apply_duration_sample(recent, 999, max_samples=MAX_SAMPLES)
    assert len(result["recent_durations"]) == MAX_SAMPLES
    assert result["recent_durations"][0] == 2
    assert result["recent_durations"][-1] == 999
    assert result["avg_duration_seconds"] == int(sum(result["recent_durations"]) / MAX_SAMPLES)


def test_estimate_total_requires_all_measured():
    assert estimate_total_seconds(["trivy", "gitleaks"], {"trivy": 60}) is None


def test_estimate_total_sums_measured_only():
    assert estimate_total_seconds(
        ["trivy", "gitleaks"],
        {"trivy": 60, "gitleaks": 40},
    ) == 100
