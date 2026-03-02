"""
AI Prompt Service
Generates structured prompts for AI analysis of security scan findings
Supports token-saving mode (Chinese) and standard mode (English)

Uses existing processor modules to parse findings - no need to maintain separate parsers!
"""
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Callable

# Setup paths using central path_setup module
# NO PATH CALCULATIONS HERE - everything is handled by path_setup.py
sys.path.insert(0, "/project/src")
from core.path_setup import setup_paths
setup_paths()

# Import finding policy functions
from core.finding_policy import load_policy, apply_semgrep_policy, apply_gitleaks_policy, apply_bandit_policy

# Tool configuration: maps tool name to (json_file, summary_function, normalizer_function)
TOOL_CONFIG = {
    "Semgrep": {
        "json_file": "semgrep.json",
        "summary_func": "semgrep_summary",
        "normalizer": lambda f: {
            "tool": "Semgrep",
            "severity": f.get("severity", "UNKNOWN"),
            "rule_id": f.get("rule_id", ""),
            "path": f.get("path", ""),
            "line": str(f.get("start", "")),
            "message": f.get("message", ""),
        }
    },
    "Trivy": {
        "json_file": "trivy.json",
        "summary_func": "trivy_summary",
        "normalizer": lambda f: {
            "tool": "Trivy",
            "severity": f.get("Severity", "UNKNOWN"),
            "rule_id": f.get("VulnerabilityID", ""),
            "path": f.get("PkgName", ""),
            "line": "",
            "message": f.get("Title", f.get("Description", "")),
        }
    },
    "CodeQL": {
        "json_file": "codeql.json",
        "summary_func": "codeql_summary",
        "normalizer": lambda f: {
            "tool": "CodeQL",
            "severity": f.get("severity", f.get("level", "note").upper()),
            "rule_id": f.get("rule_id", f.get("ruleId", "")),
            "path": f.get("path", ""),
            "line": str(f.get("start", "")),
            "message": f.get("message", ""),
        }
    },
    "GitLeaks": {
        "json_file": "gitleaks.json",
        "summary_func": "gitleaks_summary",
        "normalizer": lambda f: {
            "tool": "GitLeaks",
            "severity": "HIGH",
            "rule_id": f.get("rule_id", ""),
            "path": f.get("file", ""),
            "line": str(f.get("line", "")),
            "message": f.get("description", ""),
        }
    },
    "TruffleHog": {
        "json_file": "trufflehog.json",
        "summary_func": "trufflehog_summary",
        "normalizer": lambda f: {
            "tool": "TruffleHog",
            "severity": "HIGH",
            "rule_id": f.get("detector", ""),
            "path": f.get("redacted", ""),
            "line": "",
            "message": f.get("raw", "")[:100] if f.get("raw") else "",
        }
    },
    "Detect-secrets": {
        "json_file": "detect-secrets.json",
        "summary_func": "detect_secrets_summary",
        "normalizer": lambda f: {
            "tool": "Detect-secrets",
            "severity": "HIGH" if f.get("is_secret") else "MEDIUM",
            "rule_id": f.get("type", ""),
            "path": f.get("filename", ""),
            "line": str(f.get("line_number", "")),
            "message": f"Secret type: {f.get('type', '')}",
        }
    },
    "OWASP Dependency Check": {
        "json_file": "owasp-dependency-check-report.json",
        "summary_func": "owasp_dependency_check_summary",
        "normalizer": lambda f: {
            "tool": "OWASP Dependency Check",
            "severity": f.get("severity", "UNKNOWN"),
            "rule_id": f.get("name", ""),
            "path": f.get("fileName", ""),
            "line": "",
            "message": f.get("description", ""),
        }
    },
    "Safety": {
        "json_file": "safety.json",
        "summary_func": "safety_summary",
        "normalizer": lambda f: {
            "tool": "Safety",
            "severity": "HIGH",
            "rule_id": f.get("vulnerability", ""),
            "path": f.get("package", ""),
            "line": "",
            "message": f.get("advisory", ""),
        }
    },
    "Snyk": {
        "json_file": "snyk.json",
        "summary_func": "snyk_summary",
        "normalizer": lambda f: {
            "tool": "Snyk",
            "severity": f.get("severity", "MEDIUM").upper(),
            "rule_id": f.get("vulnerability_id", f.get("id", "")),
            "path": f.get("package", ""),
            "line": "",
            "message": f.get("title", f.get("description", "")),
        }
    },
    "ESLint": {
        "json_file": "eslint.json",
        "summary_func": "eslint_summary",
        "normalizer": lambda f: {
            "tool": "ESLint",
            "severity": {1: "LOW", 2: "MEDIUM", 3: "HIGH"}.get(f.get("severity", 1), "LOW"),
            "rule_id": f.get("rule_id", ""),
            "path": f.get("file_path", ""),
            "line": str(f.get("line", "")),
            "message": f.get("message", ""),
        }
    },
    "Bandit": {
        "json_file": "bandit.json",
        "summary_func": "bandit_summary",
        "normalizer": lambda f: {
            "tool": "Bandit",
            "severity": f.get("issue_severity", "MEDIUM").upper(),
            "rule_id": f.get("test_id", ""),
            "path": f.get("filename", ""),
            "line": str(f.get("line_number", "")),
            "message": f.get("issue_text", ""),
        }
    },
    "Brakeman": {
        "json_file": "brakeman.json",
        "summary_func": "brakeman_summary",
        "normalizer": lambda f: {
            "tool": "Brakeman",
            "severity": {"High": "HIGH", "Medium": "MEDIUM", "Low": "LOW", "Weak": "LOW"}.get(
                f.get("confidence", ""), "MEDIUM"
            ),
            "rule_id": f.get("warning_type", ""),
            "path": f.get("file", ""),
            "line": str(f.get("line", "")),
            "message": f.get("message", ""),
        }
    },
    "npm audit": {
        "json_file": "npm-audit.json",
        "summary_func": "npm_audit_summary",
        "normalizer": lambda f: {
            "tool": "npm audit",
            "severity": f.get("severity", "MODERATE").upper(),
            "rule_id": f.get("package", ""),
            "path": f.get("package", ""),
            "line": "",
            "message": f"Vulnerability in {f.get('package', '')}",
        }
    },
    "SonarQube": {
        "json_file": "sonarqube.json",
        "summary_func": "sonarqube_summary",
        "normalizer": lambda f: {
            "tool": "SonarQube",
            "severity": f.get("severity", "MEDIUM").upper(),
            "rule_id": f.get("rule", ""),
            "path": f.get("component", ""),
            "line": str(f.get("line", "")),
            "message": f.get("message", ""),
        }
    },
    "Nuclei": {
        "json_file": "nuclei.json",
        "summary_func": "nuclei_summary",
        "normalizer": lambda f: {
            "tool": "Nuclei",
            "severity": f.get("severity", "MEDIUM").upper(),
            "rule_id": f.get("template_id", ""),
            "path": f.get("host", ""),
            "line": "",
            "message": f.get("name", f.get("description", "")),
        }
    },
    "Wapiti": {
        "json_file": "wapiti.json",
        "summary_func": "wapiti_summary",
        "normalizer": lambda f: {
            "tool": "Wapiti",
            "severity": "MEDIUM",
            "rule_id": f.get("category", ""),
            "path": f.get("target", ""),
            "line": "",
            "message": f.get("description", ""),
        }
    },
    "Nikto": {
        "json_file": "nikto.json",
        "summary_func": "nikto_summary",
        "normalizer": lambda f: {
            "tool": "Nikto",
            "severity": "MEDIUM",
            "rule_id": f.get("id", ""),
            "path": f.get("url", ""),
            "line": "",
            "message": f.get("msg", ""),
        }
    },
    "Kube-hunter": {
        "json_file": "kube-hunter.json",
        "summary_func": "kube_hunter_summary",
        "normalizer": lambda f: {
            "tool": "Kube-hunter",
            "severity": f.get("severity", "MEDIUM").upper(),
            "rule_id": f.get("id", ""),
            "path": f.get("location", ""),
            "line": "",
            "message": f.get("description", ""),
        }
    },
    "Kube-bench": {
        "json_file": "kube-bench.json",
        "summary_func": "kube_bench_summary",
        "normalizer": lambda f: {
            "tool": "Kube-bench",
            "severity": "MEDIUM",
            "rule_id": f.get("id", ""),
            "path": f.get("group", ""),
            "line": "",
            "message": f.get("description", ""),
        }
    },
    "Docker Bench": {
        "json_file": "docker-bench.json",
        "summary_func": "docker_bench_summary",
        "normalizer": lambda f: {
            "tool": "Docker Bench",
            "severity": "MEDIUM",
            "rule_id": f.get("test", ""),
            "path": f.get("group", ""),
            "line": "",
            "message": f.get("description", ""),
        }
    },
}


def _load_processor_module(module_name: str):
    """Dynamically import a processor module"""
    try:
        return __import__(module_name, fromlist=[''])
    except ImportError as e:
        print(f"[AI Prompt] Warning: Could not import {module_name}: {e}")
        return None


def _get_summary_function(tool_name: str, summary_func_name: str) -> Optional[Callable]:
    """Get the summary function from a processor module"""
    # Map tool names to module names (e.g., "Semgrep" -> "semgrep_processor")
    module_name_map = {
        "Semgrep": "semgrep_processor",
        "Trivy": "trivy_processor",
        "CodeQL": "codeql_processor",
        "GitLeaks": "gitleaks_processor",
        "TruffleHog": "trufflehog_processor",
        "Detect-secrets": "detect_secrets_processor",
        "OWASP Dependency Check": "owasp_dependency_check_processor",
        "Safety": "safety_processor",
        "Snyk": "snyk_processor",
        "ESLint": "eslint_processor",
        "Bandit": "bandit_processor",
        "Brakeman": "brakeman_processor",
        "npm audit": "npm_audit_processor",
        "SonarQube": "sonarqube_processor",
        "Nuclei": "nuclei_processor",
        "Wapiti": "wapiti_processor",
        "Nikto": "nikto_processor",
        "Kube-hunter": "kube_hunter_processor",
        "Kube-bench": "kube_bench_processor",
        "Docker Bench": "docker_bench_processor",
    }
    
    module_name = module_name_map.get(tool_name)
    if not module_name:
        return None
    
    module = _load_processor_module(module_name)
    if not module:
        return None
    
    return getattr(module, summary_func_name, None)


def collect_findings_from_results(results_dir: Path, base_dir: Optional[Path] = None) -> List[Dict]:
    """
    Collect all findings from JSON files in results directory using existing processors
    Applies finding policy to filter out accepted findings
    Returns unified list of findings with tool, severity, path, line, message (filtered by policy)
    """
    all_findings = []
    
    # Group findings by tool for policy application
    findings_by_tool = {}
    
    for tool_name, config in TOOL_CONFIG.items():
        json_file = results_dir / config["json_file"]
        if not json_file.exists():
            continue
        
        try:
            # Load JSON
            with open(json_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Get summary function from processor module
            summary_func = _get_summary_function(tool_name, config["summary_func"])
            if not summary_func:
                print(f"[AI Prompt] Warning: Could not find summary function for {tool_name}")
                continue
            
            # Parse findings using processor (returns raw findings in tool-specific format)
            raw_findings = summary_func(json_data)
            
            # Skip if None (tool was skipped) or empty
            if raw_findings is None or not raw_findings:
                continue
            
            # Store raw findings by tool for policy filtering
            findings_by_tool[tool_name] = raw_findings
        
        except Exception as e:
            print(f"[AI Prompt] Error processing {tool_name} ({config['json_file']}): {e}")
            continue
    
    # Load and apply finding policy
    # Priority: 1) results_dir/finding-policy.json (copied by scanner), 2) metadata, 3) environment
    policy_path = None
    
    # 1. Check if policy was copied to results_dir by scanner
    policy_in_results = results_dir / "finding-policy.json"
    if policy_in_results.exists():
        policy_path = str(policy_in_results)
        print(f"[AI Prompt] Using finding policy from results directory: {policy_path}")
    else:
        # 2. Try to load policy path from scan metadata
        from core.scan_metadata import load_metadata
        metadata = load_metadata(str(results_dir))
        if metadata and metadata.get("finding_policy"):
            finding_policy_path = metadata.get("finding_policy")
            # This is the container path like /target/config/finding-policy.json
            # Try to construct relative path and check in project root
            if finding_policy_path.startswith("/target/"):
                policy_relative = finding_policy_path.replace("/target/", "")
                if base_dir:
                    policy_candidate = base_dir / policy_relative
                    if policy_candidate.exists():
                        policy_path = str(policy_candidate)
                        print(f"[AI Prompt] Using finding policy from metadata path: {policy_path}")
        
        # 3. Fallback: Try environment variable (for backward compatibility)
        if not policy_path:
            env_policy = os.environ.get("FINDING_POLICY_FILE")
            if env_policy and env_policy.strip():
                if Path(env_policy).exists():
                    policy_path = env_policy
                    print(f"[AI Prompt] Using finding policy from environment: {policy_path}")
    
    finding_policy = {}
    if policy_path:
        finding_policy = load_policy(policy_path)
        if finding_policy:
            print(f"[AI Prompt] Loaded finding policy successfully")
        else:
            print(f"[AI Prompt] Warning: Failed to load finding policy from: {policy_path}")
    else:
        print(f"[AI Prompt] No finding policy found - all findings will be included")
    
    # Apply policy to each tool's findings
    for tool_name, raw_findings in findings_by_tool.items():
        filtered_findings = raw_findings
        
        # Apply tool-specific policy
        if tool_name == "Semgrep" and finding_policy.get("semgrep"):
            filtered_findings, _ = apply_semgrep_policy(raw_findings, finding_policy.get("semgrep", {}))
        elif tool_name == "GitLeaks" and finding_policy.get("gitleaks"):
            filtered_findings, _ = apply_gitleaks_policy(raw_findings, finding_policy.get("gitleaks", {}))
        elif tool_name == "Bandit" and finding_policy.get("bandit"):
            filtered_findings, _ = apply_bandit_policy(raw_findings, finding_policy.get("bandit", {}))
        
        # Normalize filtered findings to unified format
        normalizer = TOOL_CONFIG[tool_name]["normalizer"]
        for raw_finding in filtered_findings:
            normalized = normalizer(raw_finding)
            all_findings.append(normalized)
    
    return all_findings


def generate_ai_prompt(findings: List[Dict], language: str = "english", policy_path: str = "config/finding-policy.json", max_findings_per_prompt: int = 50) -> str:
    """
    Generate structured AI prompt for false positive analysis
    Automatically splits into multiple prompts if findings exceed max_findings_per_prompt
    
    Args:
        findings: List of finding dictionaries
        language: Language for prompt (english, chinese, german)
        policy_path: Path where finding policy should be placed (default: "config/finding-policy.json")
        max_findings_per_prompt: Maximum findings per prompt before splitting (default: 50)
    
    Returns:
        Formatted prompt string (or multiple prompts separated by delimiters if split)
    """
    language = language.lower()
    
    # Split findings if too many
    if len(findings) > max_findings_per_prompt:
        return _generate_split_prompt(findings, language, policy_path, max_findings_per_prompt)
    
    if language == "chinese":
        return _generate_chinese_prompt(findings, policy_path)
    elif language == "german":
        return _generate_german_prompt(findings, policy_path)
    else:
        return _generate_english_prompt(findings, policy_path)


def _generate_split_prompt(findings: List[Dict], language: str, policy_path: str, max_findings: int) -> str:
    """Generate multiple prompts when findings exceed max_findings_per_prompt"""
    # Group by tool first
    by_tool = {}
    for f in findings:
        tool = f["tool"]
        if tool not in by_tool:
            by_tool[tool] = []
        by_tool[tool].append(f)
    
    # Split into chunks
    chunks = []
    current_chunk = []
    current_count = 0
    
    for tool, tool_findings in by_tool.items():
        # If adding this tool would exceed limit, start new chunk
        if current_count + len(tool_findings) > max_findings and current_chunk:
            chunks.append(current_chunk)
            current_chunk = []
            current_count = 0
        
        # Add all findings from this tool (keep tool findings together)
        current_chunk.extend(tool_findings)
        current_count += len(tool_findings)
    
    # Add remaining chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    # Generate prompts for each chunk
    prompts = []
    for i, chunk in enumerate(chunks, 1):
        if language == "chinese":
            prompt = _generate_chinese_prompt(chunk, policy_path, chunk_num=i, total_chunks=len(chunks))
        elif language == "german":
            prompt = _generate_german_prompt(chunk, policy_path, chunk_num=i, total_chunks=len(chunks))
        else:
            prompt = _generate_english_prompt(chunk, policy_path, chunk_num=i, total_chunks=len(chunks))
        prompts.append(prompt)
    
    # Join with clear separator
    separator = "\n\n" + "="*80 + "\n\n"
    return separator.join(prompts)


def _generate_english_prompt(findings: List[Dict], policy_path: str = "config/finding-policy.json", chunk_num: int = None, total_chunks: int = None) -> str:
    """Generate English prompt (standard mode)"""
    # Group by tool
    by_tool = {}
    for f in findings:
        tool = f["tool"]
        if tool not in by_tool:
            by_tool[tool] = []
        by_tool[tool].append(f)
    
    # Add chunk info if split
    chunk_header = ""
    if chunk_num and total_chunks:
        chunk_header = f"## Part {chunk_num} of {total_chunks}\n\n"
    
    prompt_parts = [
        "# Security Scan Findings Analysis Request\n\n",
        chunk_header,
        "I have performed a security scan on my codebase and found the following issues. ",
        "Please analyze each finding and:\n",
        "1. Identify false positives (findings that are not actual security issues)\n",
        "2. For false positives, suggest code changes if possible to avoid triggering the rule\n",
        "3. If code changes are not possible/appropriate, generate a finding policy JSON entry\n",
        f"4. Provide the complete {os.path.basename(policy_path)} structure with all false positives\n\n",
        "## Findings Summary\n",
        f"Total findings in this part: {len(findings)}\n",
        f"Tools: {', '.join(by_tool.keys())}\n\n"
    ]
    
    # Add findings by tool
    for tool, tool_findings in by_tool.items():
        prompt_parts.append(f"## {tool} Findings ({len(tool_findings)} total)\n\n")
        
        for i, finding in enumerate(tool_findings, 1):
            prompt_parts.append(f"### Finding {i}\n")
            prompt_parts.append(f"- **Severity**: {finding['severity']}\n")
            prompt_parts.append(f"- **File**: `{finding['path']}`\n")
            if finding.get('line'):
                prompt_parts.append(f"- **Line**: {finding['line']}\n")
            if finding.get('rule_id'):
                prompt_parts.append(f"- **Rule ID**: `{finding['rule_id']}`\n")
            prompt_parts.append(f"- **Message**: {finding['message']}\n\n")
    
    prompt_parts.append("\n## Expected Output\n")
    prompt_parts.append("1. List of false positives with explanations\n")
    prompt_parts.append("2. Code change suggestions (if applicable)\n")
    prompt_parts.append(f"3. Complete `{os.path.basename(policy_path)}` structure with all false positives\n")
    prompt_parts.append(f"   - Place in `{policy_path}`\n")
    prompt_parts.append("   - Use proper regex patterns for path/message matching\n")
    prompt_parts.append("   - Include clear reasons for each accepted finding\n")
    
    return "".join(prompt_parts)


def _generate_chinese_prompt(findings: List[Dict], policy_path: str = "config/finding-policy.json", chunk_num: int = None, total_chunks: int = None) -> str:
    """Generate Chinese prompt (token-saving mode)"""
    # Group by tool
    by_tool = {}
    for f in findings:
        tool = f["tool"]
        if tool not in by_tool:
            by_tool[tool] = []
        by_tool[tool].append(f)
    
    # Add chunk info if split
    chunk_header = ""
    if chunk_num and total_chunks:
        chunk_header = f"## 第 {chunk_num} 部分，共 {total_chunks} 部分\n\n"
    
    prompt_parts = [
        "# 安全扫描结果分析请求\n\n",
        chunk_header,
        "我对代码库进行了安全扫描，发现以下问题。请分析每个发现并：\n",
        "1. 识别误报（非实际安全问题的发现）\n",
        "2. 对于误报，如可能，建议代码更改以避免触发规则\n",
        "3. 如果无法/不适合更改代码，生成finding policy JSON条目\n",
        f"4. 提供包含所有误报的完整{os.path.basename(policy_path)}结构\n\n",
        "## 发现摘要\n",
        f"本部分总发现数: {len(findings)}\n",
        f"工具: {', '.join(by_tool.keys())}\n\n"
    ]
    
    # Add findings by tool
    for tool, tool_findings in by_tool.items():
        prompt_parts.append(f"## {tool} 发现 ({len(tool_findings)} 个)\n\n")
        
        for i, finding in enumerate(tool_findings, 1):
            prompt_parts.append(f"### 发现 {i}\n")
            prompt_parts.append(f"- **严重性**: {finding['severity']}\n")
            prompt_parts.append(f"- **文件**: `{finding['path']}`\n")
            if finding.get('line'):
                prompt_parts.append(f"- **行号**: {finding['line']}\n")
            if finding.get('rule_id'):
                prompt_parts.append(f"- **规则ID**: `{finding['rule_id']}`\n")
            prompt_parts.append(f"- **消息**: {finding['message']}\n\n")
    
    prompt_parts.append("\n## 期望输出\n")
    prompt_parts.append("1. 误报列表及说明\n")
    prompt_parts.append("2. 代码更改建议（如适用）\n")
    prompt_parts.append(f"3. 包含所有误报的完整`{os.path.basename(policy_path)}`结构\n")
    prompt_parts.append(f"   - 放置在`{policy_path}`\n")
    prompt_parts.append("   - 使用正确的正则表达式匹配路径/消息\n")
    prompt_parts.append("   - 为每个接受的发现包含清晰的理由\n")
    
    return "".join(prompt_parts)


def _generate_german_prompt(findings: List[Dict], policy_path: str = "config/finding-policy.json", chunk_num: int = None, total_chunks: int = None) -> str:
    """Generate German prompt"""
    # Group by tool
    by_tool = {}
    for f in findings:
        tool = f["tool"]
        if tool not in by_tool:
            by_tool[tool] = []
        by_tool[tool].append(f)
    
    # Add chunk info if split
    chunk_header = ""
    if chunk_num and total_chunks:
        chunk_header = f"## Teil {chunk_num} von {total_chunks}\n\n"
    
    prompt_parts = [
        "# Sicherheitsscan-Ergebnisse Analyseanfrage\n\n",
        chunk_header,
        "Ich habe einen Sicherheitsscan meines Codebases durchgeführt und die folgenden Probleme gefunden. ",
        "Bitte analysieren Sie jeden Fund und:\n",
        "1. Identifizieren Sie False Positives (Funde, die keine tatsächlichen Sicherheitsprobleme sind)\n",
        "2. Für False Positives schlagen Sie Code-Änderungen vor, falls möglich, um die Regel nicht auszulösen\n",
        "3. Wenn Code-Änderungen nicht möglich/angemessen sind, generieren Sie einen finding policy JSON-Eintrag\n",
        f"4. Stellen Sie die vollständige {os.path.basename(policy_path)}-Struktur mit allen False Positives bereit\n\n",
        "## Funde-Zusammenfassung\n",
        f"Gesamtanzahl Funde in diesem Teil: {len(findings)}\n",
        f"Tools: {', '.join(by_tool.keys())}\n\n"
    ]
    
    # Add findings by tool
    for tool, tool_findings in by_tool.items():
        prompt_parts.append(f"## {tool} Funde ({len(tool_findings)} insgesamt)\n\n")
        
        for i, finding in enumerate(tool_findings, 1):
            prompt_parts.append(f"### Fund {i}\n")
            prompt_parts.append(f"- **Schweregrad**: {finding['severity']}\n")
            prompt_parts.append(f"- **Datei**: `{finding['path']}`\n")
            if finding.get('line'):
                prompt_parts.append(f"- **Zeile**: {finding['line']}\n")
            if finding.get('rule_id'):
                prompt_parts.append(f"- **Regel-ID**: `{finding['rule_id']}`\n")
            prompt_parts.append(f"- **Nachricht**: {finding['message']}\n\n")
    
    prompt_parts.append("\n## Erwartete Ausgabe\n")
    prompt_parts.append("1. Liste der False Positives mit Erklärung\n")
    prompt_parts.append("2. Code-Änderungsvorschläge (falls zutreffend)\n")
    prompt_parts.append(f"3. Vollständige `{os.path.basename(policy_path)}`-Struktur mit allen False Positives\n")
    prompt_parts.append(f"   - Abzulegen in `{policy_path}`\n")
    prompt_parts.append("   - Verwenden Sie korrekte reguläre Ausdrücke zum Abgleichen von Pfad/Nachricht\n")
    prompt_parts.append("   - Enthalten Sie für jeden akzeptierten Fund eine klare Begründung\n")
    
    return "".join(prompt_parts)
