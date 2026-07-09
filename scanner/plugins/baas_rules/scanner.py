"""
BaaS Rules & RLS Scanner

Detects overly permissive Firebase Security Rules and Supabase RLS policies
in repository files (firestore.rules, storage.rules, supabase/migrations/*.sql, etc.).
"""
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability


# Firebase rules: allow read/write when condition is always true
_FIREBASE_OPEN_ALLOW = re.compile(
    r"allow\s+(?:read|write|read,\s*write|write,\s*read)\s*:\s*if\s+true\b",
    re.IGNORECASE,
)
_FIREBASE_WILDCARD_MATCH = re.compile(
    r"match\s+/\{document=\*\*\}",
    re.IGNORECASE,
)

# Supabase / PostgreSQL RLS
_SUPABASE_OPEN_USING = re.compile(
    r"create\s+policy\s+.+?\s+using\s*\(\s*true\s*\)",
    re.IGNORECASE | re.DOTALL,
)
_SUPABASE_OPEN_CHECK = re.compile(
    r"create\s+policy\s+.+?\s+with\s+check\s*\(\s*true\s*\)",
    re.IGNORECASE | re.DOTALL,
)
_SUPABASE_DISABLE_RLS = re.compile(
    r"alter\s+table\s+.+\s+disable\s+row\s+level\s+security",
    re.IGNORECASE,
)
_SUPABASE_GRANT_ALL = re.compile(
    r"grant\s+all\s+on\s+.+\s+to\s+(anon|authenticated|public)\b",
    re.IGNORECASE,
)
_SUPABASE_ANON_POLICY = re.compile(
    r"create\s+policy\s+.+\s+for\s+all\s+to\s+anon\b",
    re.IGNORECASE | re.DOTALL,
)

_RULE_FILENAMES = frozenset({
    "firestore.rules",
    "storage.rules",
    "database.rules.json",
    "realtime.rules.json",
})

_SUPABASE_PATH_MARKERS = ("supabase/migrations/", "supabase/seed.sql", "supabase/policies/")


def _line_number(content: str, match_start: int) -> int:
    return content[:match_start].count("\n") + 1


def _issue(
    *,
    file: str,
    line: int,
    severity: str,
    rule_id: str,
    message: str,
    recommendation: str,
    platform: str,
) -> Dict[str, Any]:
    return {
        "file": file,
        "line": line,
        "severity": severity,
        "rule_id": rule_id,
        "type": rule_id,
        "message": message,
        "description": message,
        "recommendation": recommendation,
        "platform": platform,
    }


class BaasRulesScanner(BaseScanner):
    """Firebase / Supabase rules and RLS policy scanner."""

    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.CONFIG,
            supported_targets=[
                TargetType.LOCAL_MOUNT,
                TargetType.GIT_REPO,
                TargetType.UPLOADED_CODE,
            ],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 35
    REQUIRES_CONDITION = None

    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None,
    ):
        super().__init__("baas_rules", target_path, results_dir, log_file, config_path)

    def find_rule_files(self) -> List[Path]:
        """Collect Firebase rules files, firebase.json, and Supabase SQL migrations."""
        found: List[Path] = []
        root = self.target_path

        for path in root.rglob("*"):
            if not path.is_file():
                continue
            name = path.name.lower()
            rel = str(path.relative_to(root)).replace("\\", "/").lower()

            if name in _RULE_FILENAMES:
                found.append(path)
                continue
            if name == "firebase.json":
                found.append(path)
                continue
            if any(marker in rel for marker in _SUPABASE_PATH_MARKERS):
                if name.endswith(".sql"):
                    found.append(path)
                continue
            if rel.endswith("supabase/config.toml"):
                found.append(path)

        return sorted(set(found))

    def analyze_firebase_rules(self, path: Path, content: str) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        rel = str(path.relative_to(self.target_path))

        for match in _FIREBASE_OPEN_ALLOW.finditer(content):
            issues.append(
                _issue(
                    file=rel,
                    line=_line_number(content, match.start()),
                    severity="CRITICAL",
                    rule_id="firebase_open_allow",
                    message="Firebase rule allows read/write without authentication (`if true`).",
                    recommendation=(
                        "Restrict access with `request.auth != null` or fine-grained conditions. "
                        "Never expose production data with `if true`."
                    ),
                    platform="firebase",
                )
            )

        if _FIREBASE_WILDCARD_MATCH.search(content) and _FIREBASE_OPEN_ALLOW.search(content):
            for match in _FIREBASE_WILDCARD_MATCH.finditer(content):
                issues.append(
                    _issue(
                        file=rel,
                        line=_line_number(content, match.start()),
                        severity="HIGH",
                        rule_id="firebase_wildcard_match",
                        message="Wildcard document match `{document=**}` combined with open allow rules.",
                        recommendation=(
                            "Scope rules to specific collections/documents and require authentication."
                        ),
                        platform="firebase",
                    )
                )
                break

        return issues

    def analyze_firebase_json_rules(self, path: Path, data: dict) -> List[Dict[str, Any]]:
        """Check legacy Realtime Database rules JSON for .read/.write: true."""
        issues: List[Dict[str, Any]] = []
        rel = str(path.relative_to(self.target_path))

        def walk(node: Any, pointer: str) -> None:
            if not isinstance(node, dict):
                return
            for key, value in node.items():
                current = f"{pointer}/{key}" if pointer else key
                if key in (".read", ".write") and value is True:
                    issues.append(
                        _issue(
                            file=rel,
                            line=0,
                            severity="CRITICAL",
                            rule_id="firebase_json_open_rule",
                            message=f"Realtime Database rule `{current}` is set to true (open access).",
                            recommendation="Set `.read`/`.write` to false or use auth-based conditions.",
                            platform="firebase",
                        )
                    )
                elif isinstance(value, dict):
                    walk(value, current)

        rules = data.get("rules", data)
        if isinstance(rules, dict):
            walk(rules, "")
        return issues

    def analyze_supabase_sql(self, path: Path, content: str) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        rel = str(path.relative_to(self.target_path))

        checks: List[Tuple[re.Pattern, str, str, str]] = [
            (
                _SUPABASE_OPEN_USING,
                "CRITICAL",
                "supabase_rls_open_using",
                "Supabase RLS policy uses `USING (true)` — all rows visible to role.",
            ),
            (
                _SUPABASE_OPEN_CHECK,
                "CRITICAL",
                "supabase_rls_open_check",
                "Supabase RLS policy uses `WITH CHECK (true)` — unrestricted writes.",
            ),
            (
                _SUPABASE_DISABLE_RLS,
                "CRITICAL",
                "supabase_rls_disabled",
                "Row Level Security is explicitly disabled on a table.",
            ),
            (
                _SUPABASE_GRANT_ALL,
                "HIGH",
                "supabase_overly_permissive_grant",
                "GRANT ALL to anon/authenticated/public — verify RLS protects these roles.",
            ),
            (
                _SUPABASE_ANON_POLICY,
                "HIGH",
                "supabase_anon_all_policy",
                "Policy grants ALL operations to anon role — often unintentional on public Supabase projects.",
            ),
        ]

        for pattern, severity, rule_id, message in checks:
            for match in pattern.finditer(content):
                issues.append(
                    _issue(
                        file=rel,
                        line=_line_number(content, match.start()),
                        severity=severity,
                        rule_id=rule_id,
                        message=message,
                        recommendation=(
                            "Enable RLS on all public-facing tables and use role-specific USING/WITH CHECK "
                            "expressions (e.g. auth.uid() = user_id)."
                        ),
                        platform="supabase",
                    )
                )

        if "enable row level security" not in content.lower() and "create table" in content.lower():
            if "supabase/migrations" in rel.replace("\\", "/").lower():
                issues.append(
                    _issue(
                        file=rel,
                        line=1,
                        severity="MEDIUM",
                        rule_id="supabase_rls_not_enabled",
                        message="Migration creates tables but does not enable Row Level Security.",
                        recommendation="Add `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` for user-facing tables.",
                        platform="supabase",
                    )
                )

        return issues

    def analyze_file(self, path: Path) -> List[Dict[str, Any]]:
        rel_lower = str(path.relative_to(self.target_path)).replace("\\", "/").lower()
        name_lower = path.name.lower()
        issues: List[Dict[str, Any]] = []

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            self.log(f"Could not read {path}: {exc}", "WARNING")
            return issues

        if name_lower in ("database.rules.json", "realtime.rules.json"):
            try:
                data = json.loads(content)
                issues.extend(self.analyze_firebase_json_rules(path, data))
            except json.JSONDecodeError as exc:
                self.log(f"Invalid JSON in {path}: {exc}", "WARNING")
        elif name_lower.endswith(".rules"):
            issues.extend(self.analyze_firebase_rules(path, content))
        elif name_lower == "firebase.json":
            try:
                data = json.loads(content)
                for key in ("firestore", "storage", "database"):
                    section = data.get(key, {})
                    if isinstance(section, dict) and section.get("rules"):
                        rules_path = path.parent / section["rules"]
                        if rules_path.is_file():
                            rules_content = rules_path.read_text(encoding="utf-8", errors="replace")
                            if rules_path.name.lower().endswith(".json"):
                                try:
                                    issues.extend(
                                        self.analyze_firebase_json_rules(
                                            rules_path, json.loads(rules_content)
                                        )
                                    )
                                except json.JSONDecodeError:
                                    pass
                            else:
                                issues.extend(self.analyze_firebase_rules(rules_path, rules_content))
            except json.JSONDecodeError:
                pass
        elif name_lower.endswith(".sql") or "supabase/migrations" in rel_lower:
            issues.extend(self.analyze_supabase_sql(path, content))

        return issues

    def scan(self) -> bool:
        self.log("Searching for Firebase rules and Supabase RLS files...")
        rule_files = self.find_rule_files()

        if not rule_files:
            self.log("No Firebase/Supabase rules files found, skipping scan.", "WARNING")
            status_path = self.results_dir / "status.json"
            status_path.write_text(
                json.dumps({
                    "status": "skipped",
                    "message": "No firestore.rules, storage.rules, or supabase/migrations SQL found.",
                }),
                encoding="utf-8",
            )
            return True

        self.log(f"Found {len(rule_files)} rules file(s), analyzing...")
        all_issues: List[Dict[str, Any]] = []
        for path in rule_files:
            all_issues.extend(self.analyze_file(path))

        by_severity = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for item in all_issues:
            sev = str(item.get("severity", "MEDIUM")).upper()
            by_severity[sev] = by_severity.get(sev, 0) + 1

        result = {
            "status": "success",
            "file_count": len(rule_files),
            "files_scanned": [str(p.relative_to(self.target_path)) for p in rule_files],
            "findings": all_issues,
            "total_issues": len(all_issues),
            "summary": by_severity,
        }

        json_output = self.results_dir / "report.json"
        text_output = self.results_dir / "report.txt"
        json_output.write_text(json.dumps(result, indent=2), encoding="utf-8")

        lines = [
            "BaaS Rules & RLS Analysis",
            "=" * 50,
            f"Files scanned: {len(rule_files)}",
            f"Total issues: {len(all_issues)}",
            "",
        ]
        for item in all_issues:
            lines.append(f"[{item['severity']}] {item['platform']} — {item['rule_id']}")
            lines.append(f"  File: {item['file']}:{item.get('line', 0)}")
            lines.append(f"  {item['message']}")
            lines.append(f"  → {item['recommendation']}")
            lines.append("")
        text_output.write_text("\n".join(lines), encoding="utf-8")

        self.log(f"Analysis complete — {len(all_issues)} issue(s) found.", "SUCCESS")
        return True


if __name__ == "__main__":
    import sys

    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/app/results")
    log_file = os.getenv("LOG_FILE", "app/results/logs/scan.log")

    scanner = BaasRulesScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
    )
    success = scanner.run()
    sys.exit(0 if success else 1)
