#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from scanner.core.policy_engine import ToolPolicySpec, apply_policy_with_severity_overrides
from scanner.output.ai_normalizer_utils import default_ai_normalizer
from scanner.output.finding_parse_spec import ParseSpec, make_summary_parser
from scanner.output.findings_html_renderer import ToolHtmlSpec, make_html_renderer
from scanner.output.processor_registry import ReportProcessor


def build_report_processor(
    *,
    name: str,
    parse_spec: ParseSpec,
    html_spec: ToolHtmlSpec,
    policy_spec: Optional[ToolPolicySpec] = None,
    policy_example_snippet: str = "",
    json_file: str = "report.json",
    html_file: Optional[str] = None,
    policy_key: Optional[str] = None,
    ai_tool_name: Optional[str] = None,
) -> ReportProcessor:
    """One factory, one parse spec, one html spec — all tools."""

    tool = ai_tool_name or name
    pk = policy_key if policy_key is not None else name.lower().replace(" ", "_")

    def _default_apply(findings, tool_policy):
        if policy_spec is None:
            return list(findings or []), []
        return apply_policy_with_severity_overrides(
            findings=findings,
            tool_policy=tool_policy or {},
            spec=policy_spec,
        )

    return ReportProcessor(
        name=name,
        summary_func=make_summary_parser(parse_spec),
        html_func=make_html_renderer(html_spec),
        ai_normalizer=default_ai_normalizer(tool, policy_key=pk if policy_spec else None, policy_spec=policy_spec),
        json_file=json_file,
        html_file=html_file,
        policy_key=pk if policy_spec else None,
        policy_spec=policy_spec,
        ai_tool_name=tool,
        apply_policy=_default_apply if policy_spec else None,
        policy_example_snippet=policy_example_snippet if policy_spec else None,
    )
