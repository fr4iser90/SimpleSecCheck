#!/usr/bin/env python3
from __future__ import annotations

import html as html_module
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

from scanner.output.html_utils import render_findings_table_section


CellGetter = Union[str, Callable[[Dict[str, Any]], Any]]


def is_summary_alerts_payload(data: Any) -> bool:
    return (
        isinstance(data, dict)
        and "summary" in data
        and isinstance(data.get("alerts"), list)
    )


@dataclass(frozen=True)
class ColumnSpec:
    header: str
    getter: CellGetter
    css_class: str = ""


@dataclass(frozen=True)
class ToolHtmlSpec:
    title: str
    empty_html: str
    columns: Sequence[ColumnSpec]
    severity_getter: Optional[CellGetter] = None
    skipped_html: Optional[str] = None
    omit_section_if_empty: bool = False


def _get_value(finding: Dict[str, Any], getter: CellGetter) -> Any:
    if callable(getter):
        return getter(finding)
    return finding.get(getter, "")


def _severity_icon(label: str) -> str:
    s = (label or "").upper()
    if s in ("CRITICAL", "HIGH", "BLOCKER", "ERROR"):
        return "🚨"
    if s in ("MEDIUM", "MODERATE", "WARNING", "WARN", "MAJOR"):
        return "⚠️"
    if s in ("LOW", "INFO", "INFORMATIONAL", "MINOR"):
        return "ℹ️"
    return "❓"


def _risk_row_icon(risk: str) -> str:
    if risk == "High":
        return "🚨"
    if risk == "Medium":
        return "⚠️"
    if risk in ("Low", "Informational"):
        return "ℹ️"
    return ""


def _render_summary_alerts(data: Dict[str, Any], spec: ToolHtmlSpec, html_path: str = "") -> str:
    empty = spec.empty_html or (
        '<div class="all-clear"><span class="icon sev-PASSED">✅</span> '
        "All clear! No issues found.</div>"
    )
    parts = [f"<h2>{html_module.escape(spec.title)}</h2>"]
    summary = data.get("summary") or {}
    alerts = data.get("alerts") or []

    parts.append("<table><tr><th>Risk Level</th><th>Number of Alerts</th></tr>")
    for risk, count in summary.items():
        icon = _risk_row_icon(str(risk))
        sev_class = html_module.escape(str(risk).upper())
        parts.append(
            f'<tr class="row-{sev_class}"><td class="severity-{sev_class}">{icon} '
            f"{html_module.escape(str(risk))}</td><td>{count}</td></tr>"
        )
    parts.append("</table>")

    if alerts:
        parts.append("<h3>Detailed Findings</h3>")
        for alert in alerts:
            if not isinstance(alert, dict):
                continue
            riskdesc = str(alert.get("riskdesc", alert.get("severity", "")))
            css_class = riskdesc.split()[0].lower() if riskdesc else "unknown"
            title = html_module.escape(str(alert.get("alert", alert.get("name", alert.get("title", "")))))
            desc = html_module.escape(str(alert.get("desc", alert.get("description", ""))))
            solution = html_module.escape(str(alert.get("solution", "")))
            count = html_module.escape(str(alert.get("count", "")))
            parts.append(
                f'<div class="alert-detail {css_class}"><h4>{title}</h4>'
                f'<div class="alert-meta"><span class="risk-badge {css_class}">'
                f"{html_module.escape(riskdesc)}</span>"
                f'<span class="alert-count">Count: {count}</span></div>'
                f'<div class="alert-description"><p><strong>Description:</strong></p><p>{desc}</p></div>'
                f'<div class="alert-solution"><p><strong>Solution:</strong></p><p>{solution}</p></div></div>'
            )
    elif sum(summary.values()) == 0:
        parts.append(empty)

    if html_path and Path(html_path).exists():
        parts.append('<p>See full ZAP report: <a href="zap-report.xml.html">zap-report.xml.html</a></p>')
    elif Path(os.environ.get("RESULTS_DIR", "/app/results"), "zap-report.html").exists():
        parts.append('<p>See full ZAP report: <a href="zap-report.html">zap-report.html</a></p>')
    return "".join(parts)


def make_html_renderer(spec: ToolHtmlSpec) -> Callable[..., str]:
    headers = [c.header for c in spec.columns]

    def _render(findings: Any, *extra: Any) -> str:
        if findings is None and spec.skipped_html:
            return f"<h2>{html_module.escape(spec.title)}</h2>{spec.skipped_html}"
        if spec.omit_section_if_empty and not findings:
            return ""
        if is_summary_alerts_payload(findings):
            html_path = str(extra[0]) if extra else ""
            return _render_summary_alerts(findings, spec, html_path)

        rows: List[str] = []
        for f in findings or []:
            if not isinstance(f, dict):
                continue
            sev_label = ""
            if spec.severity_getter is not None:
                sev_label = str(_get_value(f, spec.severity_getter) or "").upper()
            sev_icon = _severity_icon(sev_label) if sev_label else ""
            sev_class = html_module.escape(sev_label) if sev_label else "INFO"
            cells: List[str] = []
            for col in spec.columns:
                v = _get_value(f, col.getter)
                v_esc = html_module.escape(str(v if v is not None else ""))
                td_class = col.css_class
                if spec.severity_getter is not None and col.getter == spec.severity_getter:
                    td_class = f"severity-{sev_class}".strip()
                    v_esc = f"{sev_icon} {v_esc}".strip()
                if td_class:
                    cells.append(f'<td class="{html_module.escape(td_class)}">{v_esc}</td>')
                else:
                    cells.append(f"<td>{v_esc}</td>")
            rows.append(f'<tr class="finding-row sev-{sev_class}">' + "".join(cells) + "</tr>")

        return render_findings_table_section(
            title=spec.title,
            headers=headers,
            rows_html=rows,
            empty_html=spec.empty_html,
        )

    return _render
