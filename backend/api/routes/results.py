"""
Results API — HTML report (summary.html), AI prompt for findings.

Access: owner, report_shared_with_user_ids, or ?share_token= (report_share_token in metadata).
"""
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi import status as fastapi_status

from api.deps.actor_context import get_actor_context, ActorContext
from domain.services.finding_policy_defaults import DEFAULT_FINDING_POLICY_PATH
from application.services.scan_service import ScanService
from domain.exceptions.scan_exceptions import ScanNotFoundException
from domain.services.scan_result_access import can_read_scan_results
from config.settings import get_settings
from infrastructure.container import get_scan_service

router = APIRouter(
    prefix="/api",
    tags=["results"],
    responses={404: {"description": "Not found"}, 403: {"description": "Forbidden"}},
)


def _report_path(scan_id: str) -> Path:
    s = get_settings()
    base = Path(s.RESULTS_DIR_HOST if hasattr(s, "RESULTS_DIR_HOST") else "/app/results")
    return base / scan_id / "summary" / "summary.html"


def _extract_findings_from_report_html(html_path: Path) -> List[Dict[str, Any]]:
    """Extract findings JSON from summary.html script id=\"findings-data\"."""
    try:
        text = html_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    match = re.search(
        r'<script[^>]*\sid="findings-data"[^>]*>\s*([\s\S]*?)\s*</script>',
        text,
    )
    if not match:
        return []
    raw = match.group(1).strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    return data if isinstance(data, list) else []


def _build_ai_prompt(
    findings: List[Dict[str, Any]],
    language: str,
    policy_path: str,
    max_findings: int = 100,
) -> str:
    """Build AI prompt text from findings (same structure as report's generatePromptLocally)."""
    policy_file = policy_path.split("/")[-1] if policy_path else "finding-policy.json"
    by_tool: dict = {}
    for f in findings[:max_findings]:
        tool = (f.get("tool") or "Unknown").strip()
        if tool not in by_tool:
            by_tool[tool] = []
        by_tool[tool].append(f)
    list_len = sum(len(v) for v in by_tool.values())

    pr_workflow_en = "\n\n## Pull Request workflow\nIf you need to apply fixes in a repository: clone the repo if needed, apply fixes per finding or per file, commit with clear messages, and open a Pull Request. Re-run the scan with FINDING_POLICY_FILE set to verify.\n"
    pr_workflow_de = "\n\n## Pull-Request-Workflow\nWenn Sie Fixes im Repository anwenden müssen: Repo ggf. klonen, Fixes pro Finding oder pro Datei anwenden, mit klaren Commit-Messages committen und einen Pull Request öffnen. Scan mit gesetztem FINDING_POLICY_FILE erneut ausführen.\n"
    pr_workflow_zh = "\n\n## 提交流程\n如需在仓库中应用修复：如需要请先克隆仓库，按发现或按文件修复，用清晰消息提交，并提交 Pull Request。使用 FINDING_POLICY_FILE 重新运行扫描以验证。\n"

    lang = (language or "english").lower()
    parts: List[str] = []

    if lang == "german":
        parts = [
            "# Sicherheitsscan-Ergebnisse Analyseanfrage\n\n",
            "Ich habe einen Sicherheitsscan meines Codebases durchgeführt und die folgenden Probleme gefunden. ",
            "Bitte analysieren Sie jeden Fund und:\n",
            "1. Identifizieren Sie False Positives (Funde, die keine tatsächlichen Sicherheitsprobleme sind)\n",
            "2. Für False Positives schlagen Sie Code-Änderungen vor, falls möglich, um die Regel nicht auszulösen\n",
            "3. Wenn Code-Änderungen nicht möglich/angemessen sind, generieren Sie einen finding policy JSON-Eintrag\n",
            f"4. Stellen Sie die vollständige {policy_file}-Struktur mit allen False Positives bereit\n\n",
            "## Funde-Zusammenfassung\n",
            f"Gesamtanzahl Funde: {list_len}\n",
            f"Tools: {', '.join(by_tool.keys())}\n\n",
        ]
        for tool, items in by_tool.items():
            parts.append(f"## {tool} Funde ({len(items)} insgesamt)\n\n")
            for i, finding in enumerate(items, 1):
                parts.append(f"### Fund {i}\n")
                parts.append(f"- **Schweregrad**: {finding.get('severity') or 'UNKNOWN'}\n")
                parts.append(f"- **Datei**: `{finding.get('path') or ''}`\n")
                if finding.get("line"):
                    parts.append(f"- **Zeile**: {finding['line']}\n")
                if finding.get("rule_id"):
                    parts.append(f"- **Regel-ID**: `{finding['rule_id']}`\n")
                parts.append(f"- **Nachricht**: {finding.get('message') or ''}\n\n")
        parts.extend([
            "\n## Erwartete Ausgabe\n",
            "1. Liste der False Positives mit Erklärung\n",
            "2. Code-Änderungsvorschläge (falls zutreffend)\n",
            f"3. Vollständige `{policy_file}`-Struktur mit allen False Positives\n",
            f"   - Platzieren in `{policy_path}`\n",
            "   - Verwenden Sie geeignete Regex-Muster für Pfad/Nachricht-Matching\n",
            "   - Enthalten Sie klare Gründe für jeden akzeptierten Fund\n",
            pr_workflow_de,
        ])
    elif lang == "chinese":
        parts = [
            "# 安全扫描结果分析请求\n\n",
            "我对代码库进行了安全扫描，发现以下问题。请分析每个发现并：\n",
            "1. 识别误报（非实际安全问题的发现）\n",
            "2. 对于误报，如可能，建议代码更改以避免触发规则\n",
            "3. 如果无法/不适合更改代码，生成finding policy JSON条目\n",
            f"4. 提供包含所有误报的完整{policy_file}结构\n\n",
            "## 发现摘要\n",
            f"总发现数: {list_len}\n",
            f"工具: {', '.join(by_tool.keys())}\n\n",
        ]
        for tool, items in by_tool.items():
            parts.append(f"## {tool} 发现 ({len(items)} 个)\n\n")
            for i, finding in enumerate(items, 1):
                parts.append(f"### 发现 {i}\n")
                parts.append(f"- **严重性**: {finding.get('severity') or 'UNKNOWN'}\n")
                parts.append(f"- **文件**: `{finding.get('path') or ''}`\n")
                if finding.get("line"):
                    parts.append(f"- **行号**: {finding['line']}\n")
                if finding.get("rule_id"):
                    parts.append(f"- **规则ID**: `{finding['rule_id']}`\n")
                parts.append(f"- **消息**: {finding.get('message') or ''}\n\n")
        parts.extend([
            "\n## 期望输出\n",
            "1. 误报列表及说明\n",
            "2. 代码更改建议（如适用）\n",
            f"3. 包含所有误报的完整`{policy_file}`结构\n",
            f"   - 放置在`{policy_path}`\n",
            "   - 使用适当的正则表达式进行路径/消息匹配\n",
            "   - 为每个接受的发现包含清晰的原因\n",
            pr_workflow_zh,
        ])
    else:
        parts = [
            "# Security Scan Findings Analysis Request\n\n",
            "I have performed a security scan on my codebase and found the following issues. ",
            "Please analyze each finding and:\n",
            "1. Identify false positives (findings that are not actual security issues)\n",
            "2. For false positives, suggest code changes if possible to avoid triggering the rule\n",
            "3. If code changes are not possible/appropriate, generate a finding policy JSON entry\n",
            f"4. Provide the complete {policy_file} structure with all false positives\n\n",
            "## Findings Summary\n",
            f"Total findings: {list_len}\n",
            f"Tools: {', '.join(by_tool.keys())}\n\n",
        ]
        for tool, items in by_tool.items():
            parts.append(f"## {tool} Findings ({len(items)} total)\n\n")
            for i, finding in enumerate(items, 1):
                parts.append(f"### Finding {i}\n")
                parts.append(f"- **Severity**: {finding.get('severity') or 'UNKNOWN'}\n")
                parts.append(f"- **File**: `{finding.get('path') or ''}`\n")
                if finding.get("line"):
                    parts.append(f"- **Line**: {finding['line']}\n")
                if finding.get("rule_id"):
                    parts.append(f"- **Rule ID**: `{finding['rule_id']}`\n")
                parts.append(f"- **Message**: {finding.get('message') or ''}\n\n")
        parts.extend([
            "\n## Expected Output\n",
            "1. List of false positives with explanations\n",
            "2. Code change suggestions (if applicable)\n",
            f"3. Complete `{policy_file}` structure with all false positives\n",
            f"   - Place in `{policy_path}`\n",
            "   - Use proper regex patterns for path/message matching\n",
            "   - Include clear reasons for each accepted finding\n",
            pr_workflow_en,
        ])
    return "".join(parts)


def _scan_svc():
    return get_scan_service()


async def _serve_report(
    scan_id: str,
    actor: ActorContext,
    svc: ScanService,
    share_token: Optional[str],
):
    try:
        dto = await svc.get_scan_by_id(scan_id)
    except ScanNotFoundException:
        raise HTTPException(fastapi_status.HTTP_404_NOT_FOUND, "Scan not found")

    uid = dto.user_id if dto.user_id not in (None, "") else None
    if not can_read_scan_results(
        metadata=dto.metadata or {},
        scan_user_id=str(uid) if uid else None,
        actor_user_id=actor.user_id,
        actor_session_id=actor.session_id,
        actor_is_authenticated=bool(actor.is_authenticated),
        share_token_query=share_token,
    ):
        raise HTTPException(fastapi_status.HTTP_403_FORBIDDEN, "Access denied")

    p = _report_path(scan_id)
    if not p.is_file():
        raise HTTPException(fastapi_status.HTTP_404_NOT_FOUND, "Report not found")
    return FileResponse(p, media_type="text/html", filename="summary.html")


@router.get("/results/{scan_id}/report")
async def get_results_report(
    scan_id: str,
    actor_context: ActorContext = Depends(get_actor_context),
    scan_service: ScanService = Depends(_scan_svc),
    share_token: Optional[str] = Query(None),
):
    return await _serve_report(scan_id, actor_context, scan_service, share_token)


@router.get("/results/{scan_id}/ai-prompt")
async def get_results_ai_prompt(
    scan_id: str,
    actor_context: ActorContext = Depends(get_actor_context),
    scan_service: ScanService = Depends(_scan_svc),
    share_token: Optional[str] = Query(None),
    language: str = Query("english", description="Prompt language: english, chinese, german"),
    policy_path: str = Query(DEFAULT_FINDING_POLICY_PATH, description="Policy file path in prompt"),
):
    """Return AI prompt built from scan report findings (same access as report)."""
    try:
        dto = await scan_service.get_scan_by_id(scan_id)
    except ScanNotFoundException:
        raise HTTPException(fastapi_status.HTTP_404_NOT_FOUND, "Scan not found")

    uid = dto.user_id if dto.user_id not in (None, "") else None
    if not can_read_scan_results(
        metadata=dto.metadata or {},
        scan_user_id=str(uid) if uid else None,
        actor_user_id=actor_context.user_id,
        actor_session_id=actor_context.session_id,
        actor_is_authenticated=bool(actor_context.is_authenticated),
        share_token_query=share_token,
    ):
        raise HTTPException(fastapi_status.HTTP_403_FORBIDDEN, "Access denied")

    html_path = _report_path(scan_id)
    if not html_path.is_file():
        raise HTTPException(fastapi_status.HTTP_404_NOT_FOUND, "Report not found")

    findings = _extract_findings_from_report_html(html_path)
    prompt = _build_ai_prompt(
        findings,
        language=language,
        policy_path=policy_path or DEFAULT_FINDING_POLICY_PATH,
        max_findings=100,
    )
    return {
        "prompt": prompt,
        "findings_count": len(findings),
        "language": language,
        "policy_path": policy_path or DEFAULT_FINDING_POLICY_PATH,
    }
