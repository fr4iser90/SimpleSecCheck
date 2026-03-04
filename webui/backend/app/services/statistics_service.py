"""
Statistics Service
Computes aggregated scan statistics from results directories
"""

from pathlib import Path
from typing import Dict, Tuple, Optional

from app.database import get_database
from app.services.ai_prompt_service import collect_findings_from_results


SEVERITY_BUCKETS = ("critical", "high", "medium", "low", "info")


def _normalize_severity(raw: str) -> str:
    """Normalize severity strings into standard buckets."""
    if not raw:
        return "info"

    severity = str(raw).strip().upper()

    if "CRITICAL" in severity or severity == "CRIT":
        return "critical"
    if "HIGH" in severity or "ERROR" in severity:
        return "high"
    if "MEDIUM" in severity or "MODERATE" in severity or "WARN" in severity:
        return "medium"
    if "LOW" in severity:
        return "low"
    if "INFO" in severity or "INFORMATIONAL" in severity:
        return "info"

    return "info"


def _empty_severity_counts() -> Dict[str, int]:
    return {bucket: 0 for bucket in SEVERITY_BUCKETS}


def compute_statistics_from_results(
    results_dir: Path,
    base_dir: Optional[Path] = None,
) -> Tuple[Dict[str, int], Dict[str, int], int]:
    """
    Compute statistics from a scan results directory.
    Returns (findings_by_severity, findings_by_tool, false_positive_count).
    """
    findings_by_severity = _empty_severity_counts()
    findings_by_tool: Dict[str, int] = {}

    findings = collect_findings_from_results(results_dir, base_dir=base_dir)
    for finding in findings:
        severity_bucket = _normalize_severity(finding.get("severity", ""))
        if severity_bucket in findings_by_severity:
            findings_by_severity[severity_bucket] += 1

        tool_name = finding.get("tool", "Unknown")
        findings_by_tool[tool_name] = findings_by_tool.get(tool_name, 0) + 1

    false_positive_count = 0
    return findings_by_severity, findings_by_tool, false_positive_count


async def increment_statistics_for_results(
    results_dir: Path,
    base_dir: Optional[Path] = None,
) -> bool:
    """Increment global statistics for a completed scan."""
    findings_by_severity, findings_by_tool, false_positive_count = compute_statistics_from_results(
        results_dir=results_dir,
        base_dir=base_dir,
    )
    db = get_database()
    return await db.increment_statistics(
        findings_by_severity=findings_by_severity,
        findings_by_tool=findings_by_tool,
        false_positive_count=false_positive_count,
    )