#!/usr/bin/env python3
"""Parse source-file inline suppressions (# nosec, # nosemgrep, eslint-disable, etc.).

Used alongside optional finding-policy.json. Inline comments need no policy file;
optional tuning via SSC_INLINE_SUPPRESSIONS_* environment variables.
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# (relative_path, line_number) -> suppressions on that line
SuppressionIndex = dict[tuple[str, int], list["LineSuppressions"]]

_SCAN_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".go",
    ".rb",
    ".java",
    ".kt",
    ".scala",
    ".php",
    ".cs",
    ".swift",
    ".sh",
    ".bash",
    ".yaml",
    ".yml",
    ".tf",
    ".hcl",
}

_NOSEC_RE = re.compile(r"#\s*nosec(?:\s+([A-Za-z]\d+(?:\s+[A-Za-z]\d+)*))?", re.IGNORECASE)
_NOSEMGREP_RE = re.compile(
    r"#\s*nosemgrep(?::\s*([^#\n]+))?",
    re.IGNORECASE,
)
_NOQA_RE = re.compile(r"#\s*noqa(?::\s*([^#\n]+))?", re.IGNORECASE)
_SSC_ACCEPT_RE = re.compile(
    r"#\s*ssc:accept(?:\s*:\s*|\s+)([^#\n]+)?",
    re.IGNORECASE,
)
_GITLEAKS_ALLOW_RE = re.compile(r"#\s*gitleaks:allow\b", re.IGNORECASE)
_ESLINT_DISABLE_NEXT_RE = re.compile(
    r"(?://|/\*)\s*eslint-disable-next-line(?:\s+([^*\n]+))?",
    re.IGNORECASE,
)
_ESLINT_DISABLE_LINE_RE = re.compile(
    r"(?://|/\*)\s*eslint-disable-line(?:\s+([^*\n]+))?",
    re.IGNORECASE,
)

_DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": True,
    "line_lookback": 1,
    "cross_tool_nosec": True,
    "cross_tool_nosemgrep": True,
}


@dataclass
class LineSuppressions:
    """Suppressions parsed from a single source line."""

    nosec_all: bool = False
    nosec_ids: set[str] = field(default_factory=set)
    nosemgrep_all: bool = False
    nosemgrep_ids: set[str] = field(default_factory=set)
    noqa_codes: set[str] = field(default_factory=set)
    noqa_all: bool = False
    ssc_accept_all: bool = False
    ssc_accept_ids: set[str] = field(default_factory=set)
    gitleaks_allow: bool = False
    eslint_disable_next: set[str] = field(default_factory=set)
    eslint_disable_next_all: bool = False
    eslint_disable_line: set[str] = field(default_factory=set)
    eslint_disable_line_all: bool = False
    reason: str = ""
    source_line: str = ""


def debug(msg: str) -> None:
    print(f"[inline_suppressions] {msg}", file=sys.stderr)


def get_inline_config() -> dict[str, Any]:
    """Scanner inline-suppression settings (env only — not part of finding-policy.json)."""
    cfg = dict(_DEFAULT_CONFIG)
    enabled = os.environ.get("SSC_INLINE_SUPPRESSIONS_ENABLED", "").strip().lower()
    if enabled in ("0", "false", "no", "off"):
        cfg["enabled"] = False
    elif enabled in ("1", "true", "yes", "on"):
        cfg["enabled"] = True
    lookback = os.environ.get("SSC_INLINE_SUPPRESSIONS_LINE_LOOKBACK", "").strip()
    if lookback:
        try:
            cfg["line_lookback"] = max(0, int(lookback))
        except ValueError:
            pass
    cross_nosec = os.environ.get("SSC_INLINE_SUPPRESSIONS_CROSS_TOOL_NOSEC", "").strip().lower()
    if cross_nosec in ("0", "false", "no", "off"):
        cfg["cross_tool_nosec"] = False
    elif cross_nosec in ("1", "true", "yes", "on"):
        cfg["cross_tool_nosec"] = True
    cross_nosemgrep = os.environ.get("SSC_INLINE_SUPPRESSIONS_CROSS_TOOL_NOSEMGREP", "").strip().lower()
    if cross_nosemgrep in ("0", "false", "no", "off"):
        cfg["cross_tool_nosemgrep"] = False
    elif cross_nosemgrep in ("1", "true", "yes", "on"):
        cfg["cross_tool_nosemgrep"] = True
    return cfg


def _parse_ssc_accept_ids(raw: str) -> tuple[set[str], str]:
    """Split rule id(s) from optional em-dash reason tail."""
    text = raw.strip()
    if not text:
        return set(), ""
    for sep in (" — ", " - ", " – "):
        if sep in text:
            head, tail = text.split(sep, 1)
            ids = set(_split_rule_list(head))
            return ids, tail.strip()
    parts = _split_rule_list(text)
    if len(parts) == 1:
        return {parts[0]}, ""
    return set(parts), ""


def _split_rule_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    parts = re.split(r"[,;\s]+", raw.strip())
    return [p.strip() for p in parts if p.strip()]


def _extract_reason(line: str, suppress_end: int) -> str:
    tail = line[suppress_end:].strip()
    if not tail:
        return ""
    tail = re.sub(r"^[-–—:\s]+", "", tail)
    return tail.strip()


def parse_line_suppressions(line: str) -> LineSuppressions | None:
    """Parse inline suppression tags from one source line."""
    if not line or not line.strip():
        return None

    sup = LineSuppressions()
    matched = False
    reason_parts: list[str] = []

    m = _NOSEC_RE.search(line)
    if m:
        matched = True
        ids_raw = m.group(1)
        if ids_raw:
            sup.nosec_ids = {x.upper() for x in _split_rule_list(ids_raw)}
        else:
            sup.nosec_all = True
        reason_parts.append(_extract_reason(line, m.end()))

    m = _NOSEMGREP_RE.search(line)
    if m:
        matched = True
        ids_raw = (m.group(1) or "").strip()
        if ids_raw:
            sup.nosemgrep_ids = set(_split_rule_list(ids_raw))
        else:
            sup.nosemgrep_all = True
        reason_parts.append(_extract_reason(line, m.end()))

    m = _NOQA_RE.search(line)
    if m:
        matched = True
        codes_raw = (m.group(1) or "").strip()
        if codes_raw:
            sup.noqa_codes = {c.upper() for c in _split_rule_list(codes_raw)}
        else:
            sup.noqa_all = True

    m = _SSC_ACCEPT_RE.search(line)
    if m:
        matched = True
        ids_raw = (m.group(1) or "").strip()
        if ids_raw:
            accept_ids, accept_reason = _parse_ssc_accept_ids(ids_raw)
            if accept_ids:
                sup.ssc_accept_ids = accept_ids
            else:
                sup.ssc_accept_all = True
            if accept_reason:
                reason_parts.append(accept_reason)
        else:
            sup.ssc_accept_all = True

    if _GITLEAKS_ALLOW_RE.search(line):
        matched = True
        sup.gitleaks_allow = True

    m = _ESLINT_DISABLE_NEXT_RE.search(line)
    if m:
        matched = True
        rules_raw = (m.group(1) or "").strip()
        if rules_raw:
            sup.eslint_disable_next = set(_split_rule_list(rules_raw))
        else:
            sup.eslint_disable_next_all = True

    m = _ESLINT_DISABLE_LINE_RE.search(line)
    if m:
        matched = True
        rules_raw = (m.group(1) or "").strip()
        if rules_raw:
            sup.eslint_disable_line = set(_split_rule_list(rules_raw))
        else:
            sup.eslint_disable_line_all = True

    if not matched:
        return None

    sup.reason = " — ".join(p for p in reason_parts if p).strip()
    sup.source_line = line
    return sup


def _suppression_line_continues(source_line: str) -> bool:
    """True when a suppress comment likely applies to following lines (multi-line stmt)."""
    code = source_line.split("#", 1)[0].split("//", 1)[0].rstrip()
    if not code:
        return False
    return code.endswith(("(", ",", "\\", "[", "{", "+"))


def normalize_finding_path(path: str, target_root: str) -> str:
    """Return repo-relative path for index lookup."""
    if not path:
        return ""
    p = str(path).replace("\\", "/")
    root = str(target_root).replace("\\", "/").rstrip("/")
    if root and p.startswith(root + "/"):
        return p[len(root) + 1 :]
    for prefix in ("/app/target/", "/target/"):
        if p.startswith(prefix):
            return p[len(prefix) :]
    return p.lstrip("/")


def extract_finding_fields(finding: dict[str, Any]) -> tuple[str, int, str]:
    """Return (path, line, rule_id) from a tool-specific finding dict."""
    path = str(
        finding.get("path")
        or finding.get("file")
        or finding.get("filename")
        or finding.get("file_path")
        or ""
    )
    line_raw = (
        finding.get("line")
        or finding.get("line_number")
        or (finding.get("start") if isinstance(finding.get("start"), (int, str)) else None)
    )
    if line_raw is None and isinstance(finding.get("start"), dict):
        line_raw = finding["start"].get("line", 0)
    try:
        line = int(line_raw or 0)
    except (TypeError, ValueError):
        line = 0
    rule_id = str(
        finding.get("rule_id")
        or finding.get("check_id")
        or finding.get("test_id")
        or finding.get("id")
        or finding.get("type")
        or ""
    ).strip()
    return path, line, rule_id


def _rule_id_matches(rule_id: str, allowed: set[str], allow_all: bool) -> bool:
    if allow_all:
        return True
    if not allowed:
        return False
    rid = (rule_id or "").strip()
    if not rid:
        return False
    rid_upper = rid.upper()
    for item in allowed:
        candidate = item.strip()
        if not candidate:
            continue
        if candidate.upper() == rid_upper:
            return True
        if candidate in rid or rid.endswith("." + candidate) or rid.endswith("/" + candidate):
            return True
    return False


def _eslint_matches(
    rule_id: str,
    sup: LineSuppressions,
    *,
    on_next_line: bool,
) -> bool:
    rid = (rule_id or "").strip()
    if on_next_line:
        if sup.eslint_disable_next_all:
            return True
        if not sup.eslint_disable_next:
            return False
        if not rid:
            return True
        return rid in sup.eslint_disable_next
    if sup.eslint_disable_line_all:
        return True
    if not sup.eslint_disable_line:
        return False
    if not rid:
        return True
    return rid in sup.eslint_disable_line


def _match_suppression_for_tool(
    tool_key: str,
    rule_id: str,
    sup: LineSuppressions,
    *,
    on_next_line: bool,
    config: dict[str, Any],
) -> tuple[bool, str]:
    """Return (matched, suppress_tag) for one LineSuppressions on a candidate line."""
    key = (tool_key or "").lower()

    if key == "bandit":
        if _rule_id_matches(rule_id, sup.nosec_ids, sup.nosec_all):
            return True, "nosec"
        if config.get("cross_tool_nosemgrep") and _rule_id_matches(
            rule_id, sup.nosemgrep_ids, sup.nosemgrep_all
        ):
            return True, "nosemgrep"
        if sup.ssc_accept_all or _rule_id_matches(rule_id, sup.ssc_accept_ids, False):
            return True, "ssc:accept"
        return False, ""

    if key == "semgrep":
        if _rule_id_matches(rule_id, sup.nosemgrep_ids, sup.nosemgrep_all):
            return True, "nosemgrep"
        if config.get("cross_tool_nosec") and _rule_id_matches(rule_id, sup.nosec_ids, sup.nosec_all):
            return True, "nosec"
        if sup.ssc_accept_all or _rule_id_matches(rule_id, sup.ssc_accept_ids, False):
            return True, "ssc:accept"
        return False, ""

    if key == "eslint":
        if _eslint_matches(rule_id, sup, on_next_line=on_next_line):
            tag = "eslint-disable-next-line" if on_next_line else "eslint-disable-line"
            return True, tag
        if sup.ssc_accept_all or _rule_id_matches(rule_id, sup.ssc_accept_ids, False):
            return True, "ssc:accept"
        return False, ""

    if key == "gitleaks":
        if sup.gitleaks_allow:
            return True, "gitleaks:allow"
        if sup.ssc_accept_all or _rule_id_matches(rule_id, sup.ssc_accept_ids, False):
            return True, "ssc:accept"
        return False, ""

    # Cross-tool markers for tools without native inline syntax (CodeQL, Checkov, …)
    cross_nosec = config.get("cross_tool_nosec", True)
    cross_nosemgrep = config.get("cross_tool_nosemgrep", True)
    if cross_nosec and _rule_id_matches(rule_id, sup.nosec_ids, sup.nosec_all):
        return True, "nosec"
    if cross_nosemgrep and _rule_id_matches(rule_id, sup.nosemgrep_ids, sup.nosemgrep_all):
        return True, "nosemgrep"
    if sup.ssc_accept_all or _rule_id_matches(rule_id, sup.ssc_accept_ids, False):
        return True, "ssc:accept"
    if sup.gitleaks_allow and key == "gitleaks":
        return True, "gitleaks:allow"
    return False, ""


def is_finding_inline_suppressed(
    finding: dict[str, Any],
    tool_key: str,
    index: SuppressionIndex,
    target_root: str,
    config: dict[str, Any],
) -> tuple[bool, str, str]:
    """Return (suppressed, reason, suppress_tag)."""
    path, line, rule_id = extract_finding_fields(finding)
    if not path or line <= 0:
        return False, "", ""

    rel = normalize_finding_path(path, target_root)
    lookback = int(config.get("line_lookback", 1))

    for offset in range(0, lookback + 1):
        candidate_line = line - offset
        if candidate_line <= 0:
            continue
        sups = index.get((rel, candidate_line), [])
        on_next_line = offset == 1
        for sup in sups:
            if offset > 0:
                if on_next_line and tool_key.lower() == "eslint":
                    pass  # eslint-disable-next-line always applies to next line
                elif not _suppression_line_continues(sup.source_line):
                    continue
            matched, tag = _match_suppression_for_tool(
                tool_key,
                rule_id,
                sup,
                on_next_line=on_next_line,
                config=config,
            )
            if matched:
                reason = sup.reason or f"Suppressed via inline {tag}"
                return True, reason, tag

    # Fallback: match by basename if full relative path miss (scanner path variants)
    base = os.path.basename(rel)
    if base and base != rel:
        for (indexed_path, candidate_line), sups in index.items():
            if os.path.basename(indexed_path) != base:
                continue
            if abs(candidate_line - line) > lookback:
                continue
            on_next_line = candidate_line == line - 1
            for sup in sups:
                if candidate_line < line:
                    if on_next_line and tool_key.lower() == "eslint":
                        pass
                    elif not _suppression_line_continues(sup.source_line):
                        continue
                matched, tag = _match_suppression_for_tool(
                    tool_key,
                    rule_id,
                    sup,
                    on_next_line=on_next_line,
                    config=config,
                )
                if matched:
                    reason = sup.reason or f"Suppressed via inline {tag}"
                    return True, reason, tag

    return False, "", ""


def build_suppression_index(target_root: str) -> SuppressionIndex:
    """Walk target tree and index inline suppressions by (relative_path, line)."""
    index: SuppressionIndex = {}
    root = Path(target_root)
    if not root.is_dir():
        debug(f"Target root not found or not a directory: {target_root}")
        return index

    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in _SCAN_EXTENSIONS:
            continue
        try:
            rel = file_path.relative_to(root).as_posix()
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            debug(f"Skip {file_path}: {exc}")
            continue

        for line_no, line in enumerate(text.splitlines(), start=1):
            sup = parse_line_suppressions(line)
            if sup:
                index.setdefault((rel, line_no), []).append(sup)

    debug(f"Indexed inline suppressions in {len(index)} line(s) under {target_root}")
    return index


def make_inline_accept_record(
    finding: dict[str, Any],
    tool_name: str,
    reason: str,
    suppress_tag: str,
) -> dict[str, Any]:
    path, line, rule_id = extract_finding_fields(finding)
    message = str(
        finding.get("message")
        or finding.get("issue_text")
        or finding.get("description")
        or ""
    )
    return {
        "tool": tool_name,
        "reason": reason or "Suppressed via inline comment",
        "id": rule_id,
        "path": path,
        "line": str(line) if line else "",
        "message": message,
        "accept_source": "inline",
        "suppress_tag": suppress_tag,
    }


def apply_inline_suppressions(
    findings: list[Any],
    index: SuppressionIndex,
    *,
    tool_key: str,
    tool_name: str,
    target_root: str,
    config: dict[str, Any] | None = None,
) -> tuple[list[Any], list[dict[str, Any]]]:
    """Filter findings suppressed by inline comments. Returns (remaining, accepted_records)."""
    cfg = config or _DEFAULT_CONFIG
    if not findings or not index or not cfg.get("enabled", True):
        return findings or [], []

    remaining: list[Any] = []
    accepted: list[dict[str, Any]] = []

    for finding in findings:
        if not isinstance(finding, dict):
            remaining.append(finding)
            continue
        suppressed, reason, tag = is_finding_inline_suppressed(
            finding, tool_key, index, target_root, cfg
        )
        if suppressed:
            accepted.append(
                make_inline_accept_record(finding, tool_name, reason, tag)
            )
        else:
            remaining.append(finding)

    return remaining, accepted
