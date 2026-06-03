#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union

FieldSource = Union[str, Callable[[Dict[str, Any], Dict[str, Any]], Any]]


def trufflehog_details(item: Dict[str, Any], parent: Dict[str, Any]) -> str:
    source_meta = item.get("SourceMetadata", {}) or {}
    source_data = source_meta.get("Data", {}) if isinstance(source_meta, dict) else {}
    filesystem = source_data.get("Filesystem", {}) if isinstance(source_data, dict) else {}
    file_path = filesystem.get("file", "") if isinstance(filesystem, dict) else ""
    line = filesystem.get("line", "") if isinstance(filesystem, dict) else ""
    redacted = item.get("Redacted", "")
    raw_value = item.get("Raw", "")
    parts = []
    if file_path:
        parts.append(f"{file_path}:{line}" if line else file_path)
    if redacted or raw_value:
        parts.append(redacted or raw_value)
    return " | ".join(parts)


def codeql_path(item: Dict[str, Any], parent: Dict[str, Any]) -> str:
    locations = item.get("locations") or []
    if not locations:
        return item.get("path", "")
    phy = (locations[0].get("physicalLocation") or {}) if isinstance(locations[0], dict) else {}
    return (phy.get("artifactLocation") or {}).get("uri", "")


def codeql_start(item: Dict[str, Any], parent: Dict[str, Any]) -> Any:
    locations = item.get("locations") or []
    if not locations:
        start = item.get("start", {})
        return start.get("line", "") if isinstance(start, dict) else start
    phy = (locations[0].get("physicalLocation") or {}) if isinstance(locations[0], dict) else {}
    return (phy.get("region") or {}).get("startLine", "")


def codeql_message(item: Dict[str, Any], parent: Dict[str, Any]) -> str:
    msg = item.get("message", "")
    if isinstance(msg, dict):
        return msg.get("text", "")
    return str(msg or "")


def trivy_path(item: Dict[str, Any], parent: Dict[str, Any]) -> str:
    target = parent.get("Target", "")
    pkg = item.get("PkgName", "")
    if target and pkg:
        return f"{target} | {pkg}"
    return target or pkg


def trivy_title(item: Dict[str, Any], parent: Dict[str, Any]) -> str:
    return item.get("Title", "") or item.get("Description", "")


@dataclass(frozen=True)
class ParseSpec:
    """
    One spec for all report inputs.
    - input="json": raw is JSON (or path to JSON if load_json_if_path).
    - input="dual_file": summary_func(html_path, xml_path); fields = XML tag map.
    """

    input: str = "json"
    fields: Tuple[Tuple[str, str], ...] = ()

    items_key: Optional[str] = None
    root_is_list: bool = False
    items_from_dict_values: bool = False
    nested_items_key: Optional[str] = None
    parent_fields: Tuple[Tuple[str, FieldSource], ...] = ()
    dict_key_parent_field: Optional[str] = None
    inner_dict_key_parent_field: Optional[str] = None
    variants: Tuple["ParseSpec", ...] = ()

    skip_if: Optional[Callable[[Dict[str, Any]], bool]] = None
    coerce_json_string: bool = False
    load_json_if_path: bool = False
    skipped_key: Optional[str] = None

    # dual_file (input="dual_file"): fields = (out_key, xml_element_tag)
    xml_item_xpath: str = ".//alertitem"
    xml_nested_xpath: str = ""
    xml_nested_fields: Tuple[Tuple[str, str], ...] = ()
    xml_nested_output_key: str = "instances"
    risk_levels: Tuple[str, ...] = ("High", "Medium", "Low", "Informational")
    html_summary_table_class: str = "summary"
    log_prefix: str = "[parse_spec]"


def _get_by_path(obj: Any, path: str) -> Any:
    cur = obj
    for part in path.split("."):
        if cur is None:
            return None
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def _resolve_field(
    item: Dict[str, Any],
    parent: Dict[str, Any],
    source: FieldSource,
) -> Any:
    if callable(source):
        return source(item, parent)
    if source.startswith("parent."):
        return _get_by_path(parent, source[len("parent.") :])
    return _get_by_path(item, source)


def _coerce_raw(raw: Any, spec: ParseSpec) -> Any:
    if spec.load_json_if_path and isinstance(raw, str) and Path(raw).exists():
        try:
            with open(raw, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None
    if spec.coerce_json_string and isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    return raw


def _log(spec: ParseSpec, msg: str) -> None:
    print(f"{spec.log_prefix} {msg}", file=sys.stderr)


def _risk_bucket(riskdesc: str, levels: Tuple[str, ...]) -> Optional[str]:
    for level in levels:
        if (riskdesc or "").startswith(level):
            return level
    return None


def _parse_dual_file_xml(xml_path: str, spec: ParseSpec) -> Optional[Dict[str, Any]]:
    from defusedxml import defuse_stdlib
    from defusedxml.ElementTree import parse as safe_parse

    defuse_stdlib()
    if not xml_path or not Path(xml_path).exists():
        return None
    try:
        root = safe_parse(xml_path).getroot()
        summary = {level: 0 for level in spec.risk_levels}
        alerts: List[Dict[str, Any]] = []
        for item in root.findall(spec.xml_item_xpath):
            record = {out_key: item.findtext(tag, "") for out_key, tag in spec.fields}
            if spec.xml_nested_xpath and spec.xml_nested_fields:
                nested = [
                    {out_key: inst.findtext(tag, "") for out_key, tag in spec.xml_nested_fields}
                    for inst in item.findall(spec.xml_nested_xpath)
                ]
                record[spec.xml_nested_output_key] = nested
            alerts.append(record)
            bucket = _risk_bucket(str(record.get("riskdesc", record.get("severity", ""))), spec.risk_levels)
            if bucket:
                summary[bucket] += 1
        return {"summary": summary, "alerts": alerts}
    except Exception as e:
        _log(spec, f"XML parse error: {e}")
        return None


def _parse_dual_file_html(html_path: str, spec: ParseSpec) -> Optional[Dict[str, Any]]:
    from bs4 import BeautifulSoup

    if not html_path or not Path(html_path).exists():
        return None
    try:
        with open(html_path, encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
        summary = {level: 0 for level in spec.risk_levels}
        table = soup.find("table", class_=spec.html_summary_table_class)
        if table:
            for row in table.find_all("tr"):
                cols = row.find_all("td")
                if len(cols) == 2:
                    risk = cols[0].get_text(strip=True)
                    if risk in summary:
                        try:
                            summary[risk] = int(cols[1].get_text(strip=True))
                        except ValueError:
                            pass
        return {"summary": summary, "alerts": []}
    except Exception as e:
        _log(spec, f"HTML parse error: {e}")
        return None


def parse_dual_file(html_path: str, xml_path: str, spec: ParseSpec) -> Dict[str, Any]:
    empty = {"summary": {level: 0 for level in spec.risk_levels}, "alerts": []}
    parsed = _parse_dual_file_xml(xml_path, spec) or _parse_dual_file_html(html_path, spec)
    return parsed if parsed is not None else empty


def _iter_items(raw: Any, spec: ParseSpec) -> Iterable[Tuple[Dict[str, Any], Dict[str, Any]]]:
    if raw is None:
        return

    if spec.root_is_list and isinstance(raw, list):
        parents = raw
    elif isinstance(raw, dict):
        if spec.items_key:
            container = _get_by_path(raw, spec.items_key) if "." in spec.items_key else raw.get(spec.items_key)
        else:
            container = raw
        if spec.dict_key_parent_field and isinstance(container, dict):
            for key, val in container.items():
                if isinstance(val, list):
                    parent = {spec.dict_key_parent_field: key}
                    for child in val:
                        if isinstance(child, dict):
                            yield child, parent
                    continue
                if isinstance(val, dict) and spec.inner_dict_key_parent_field:
                    outer_parent = {spec.dict_key_parent_field: key}
                    for inner_key, inner_val in val.items():
                        if not isinstance(inner_val, list):
                            continue
                        parent = {**outer_parent, spec.inner_dict_key_parent_field: inner_key}
                        for child in inner_val:
                            if isinstance(child, dict):
                                yield child, parent
                    continue
                if isinstance(val, dict) and spec.nested_items_key:
                    parent = dict(val)
                    parent[spec.dict_key_parent_field] = key
                    children = val.get(spec.nested_items_key) or []
                    if not isinstance(children, list):
                        continue
                    for child in children:
                        if isinstance(child, dict):
                            yield child, parent
            return
        if spec.items_from_dict_values and isinstance(container, dict):
            parents = list(container.values())
        elif isinstance(container, list):
            parents = container
        else:
            return
    else:
        return

    for parent in parents:
        if not isinstance(parent, dict):
            continue
        if spec.nested_items_key:
            children = parent.get(spec.nested_items_key) or []
            if not isinstance(children, list):
                continue
            for child in children:
                if isinstance(child, dict):
                    yield child, parent
        else:
            yield parent, parent


def _parse_json(raw: Any, spec: ParseSpec) -> Any:
    raw = _coerce_raw(raw, spec)
    if spec.skipped_key and isinstance(raw, dict) and raw.get(spec.skipped_key):
        return None

    if spec.variants:
        findings: List[Dict[str, Any]] = []
        for variant in spec.variants:
            for item, parent in _iter_items(raw, variant):
                finding: Dict[str, Any] = {}
                for out_key, parent_src in variant.parent_fields:
                    finding[out_key] = _resolve_field(parent, parent, parent_src)
                for out_key, src in variant.fields:
                    finding[out_key] = _resolve_field(item, parent, src)
                if variant.skip_if and variant.skip_if(finding):
                    continue
                findings.append(finding)
        return findings

    findings: List[Dict[str, Any]] = []
    for item, parent in _iter_items(raw, spec):
        finding: Dict[str, Any] = {}
        for out_key, parent_src in spec.parent_fields:
            finding[out_key] = _resolve_field(parent, parent, parent_src)
        for out_key, src in spec.fields:
            finding[out_key] = _resolve_field(item, parent, src)
        if spec.skip_if and spec.skip_if(finding):
            continue
        findings.append(finding)
    return findings


def parse_report(raw: Any, spec: ParseSpec) -> Any:
    if spec.input == "dual_file":
        html_path = raw[0] if isinstance(raw, (tuple, list)) and raw else (raw if isinstance(raw, str) else "")
        xml_path = raw[1] if isinstance(raw, (tuple, list)) and len(raw) > 1 else ""
        if isinstance(raw, tuple) and len(raw) == 2:
            html_path, xml_path = raw
        elif not isinstance(raw, (tuple, list)):
            html_path = str(raw or "")
            xml_path = ""
        return parse_dual_file(str(html_path or ""), str(xml_path or ""), spec)
    return _parse_json(raw, spec)


def make_summary_parser(spec: ParseSpec) -> Callable[..., Any]:
    def _summary(*args: Any) -> Any:
        if spec.input == "dual_file":
            html_path = args[0] if args else ""
            xml_path = args[1] if len(args) > 1 else ""
            return parse_dual_file(html_path, xml_path, spec)
        raw = args[0] if args else None
        return parse_report(raw, spec)

    return _summary
