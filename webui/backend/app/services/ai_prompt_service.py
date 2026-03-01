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

# Tool configuration: maps tool name to (json_file, summary_function, normalizer_function)
TOOL_CONFIG = {
    "Semgrep": {
        "json_file": "semgrep.json",
        "summary_func": "semgrep_summary",
        "normalizer": lambda f: {
            "tool": "Semgrep",
            "severity": f.get("severity", "UNKNOWN"),
            "check_id": f.get("check_id", ""),
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
            "check_id": f.get("VulnerabilityID", ""),
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
            "check_id": f.get("rule_id", f.get("ruleId", "")),
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
            "check_id": f.get("rule_id", ""),
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
            "check_id": f.get("detector", ""),
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
            "check_id": f.get("type", ""),
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
            "check_id": f.get("name", ""),
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
            "check_id": f.get("vulnerability", ""),
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
            "check_id": f.get("vulnerability_id", f.get("id", "")),
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
            "check_id": f.get("rule_id", ""),
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
            "check_id": f.get("test_id", ""),
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
            "check_id": f.get("warning_type", ""),
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
            "check_id": f.get("package", ""),
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
            "check_id": f.get("rule", ""),
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
            "check_id": f.get("template_id", ""),
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
            "check_id": f.get("category", ""),
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
            "check_id": f.get("id", ""),
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
            "check_id": f.get("id", ""),
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
            "check_id": f.get("id", ""),
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
            "check_id": f.get("test", ""),
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


def collect_findings_from_results(results_dir: Path) -> List[Dict]:
    """
    Collect all findings from JSON files in results directory using existing processors
    Returns unified list of findings with tool, severity, path, line, message
    """
    all_findings = []
    
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
            
            # Parse findings using processor
            raw_findings = summary_func(json_data)
            
            # Skip if None (tool was skipped) or empty
            if raw_findings is None or not raw_findings:
                continue
            
            # Normalize findings to unified format
            normalizer = config["normalizer"]
            for raw_finding in raw_findings:
                normalized = normalizer(raw_finding)
                all_findings.append(normalized)
        
        except Exception as e:
            print(f"[AI Prompt] Error processing {tool_name} ({config['json_file']}): {e}")
            continue
    
    return all_findings


def generate_ai_prompt(findings: List[Dict], token_saving: bool = False, policy_path: str = "config/finding-policy.json") -> str:
    """
    Generate structured AI prompt for false positive analysis
    
    Args:
        findings: List of finding dictionaries
        token_saving: If True, use Chinese for token efficiency
        policy_path: Path where finding policy should be placed (default: "config/finding-policy.json")
    
    Returns:
        Formatted prompt string
    """
    if token_saving:
        return _generate_chinese_prompt(findings, policy_path)
    else:
        return _generate_english_prompt(findings, policy_path)


def _generate_english_prompt(findings: List[Dict], policy_path: str = "config/finding-policy.json") -> str:
    """Generate English prompt (standard mode)"""
    # Group by tool
    by_tool = {}
    for f in findings:
        tool = f["tool"]
        if tool not in by_tool:
            by_tool[tool] = []
        by_tool[tool].append(f)
    
    prompt_parts = [
        "# Security Scan Findings Analysis Request\n\n",
        "I have performed a security scan on my codebase and found the following issues. ",
        "Please analyze each finding and:\n",
        "1. Identify false positives (findings that are not actual security issues)\n",
        "2. For false positives, suggest code changes if possible to avoid triggering the rule\n",
        "3. If code changes are not possible/appropriate, generate a finding policy JSON entry\n",
        "4. Provide the complete finding_policy.json structure with all false positives\n\n",
        "## Findings Summary\n",
        f"Total findings: {len(findings)}\n",
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
            if finding.get('check_id'):
                prompt_parts.append(f"- **Rule ID**: `{finding['check_id']}`\n")
            prompt_parts.append(f"- **Message**: {finding['message']}\n\n")
    
    prompt_parts.append("\n## Expected Output\n")
    prompt_parts.append("1. List of false positives with explanations\n")
    prompt_parts.append("2. Code change suggestions (if applicable)\n")
    prompt_parts.append("3. Complete `finding_policy.json` structure with all false positives\n")
    prompt_parts.append(f"   - Place in `{policy_path}`\n")
    prompt_parts.append("   - Use proper regex patterns for path/message matching\n")
    prompt_parts.append("   - Include clear reasons for each accepted finding\n")
    
    return "".join(prompt_parts)


def _generate_chinese_prompt(findings: List[Dict], policy_path: str = "config/finding-policy.json") -> str:
    """Generate Chinese prompt (token-saving mode)"""
    # Group by tool
    by_tool = {}
    for f in findings:
        tool = f["tool"]
        if tool not in by_tool:
            by_tool[tool] = []
        by_tool[tool].append(f)
    
    prompt_parts = [
        "# 安全扫描结果分析请求\n\n",
        "我对代码库进行了安全扫描，发现以下问题。请分析每个发现并：\n",
        "1. 识别误报（非实际安全问题的发现）\n",
        "2. 对于误报，如可能，建议代码更改以避免触发规则\n",
        "3. 如果无法/不适合更改代码，生成finding policy JSON条目\n",
        "4. 提供包含所有误报的完整finding_policy.json结构\n\n",
        "## 发现摘要\n",
        f"总发现数: {len(findings)}\n",
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
            if finding.get('check_id'):
                prompt_parts.append(f"- **规则ID**: `{finding['check_id']}`\n")
            prompt_parts.append(f"- **消息**: {finding['message']}\n\n")
    
    prompt_parts.append("\n## 期望输出\n")
    prompt_parts.append("1. 误报列表及说明\n")
    prompt_parts.append("2. 代码更改建议（如适用）\n")
    prompt_parts.append("3. 包含所有误报的完整`finding_policy.json`结构\n")
    prompt_parts.append(f"   - 放置在`{policy_path}`\n")
    prompt_parts.append("   - 使用正确的正则表达式匹配路径/消息\n")
    prompt_parts.append("   - 为每个接受的发现包含清晰的理由\n")
    
    return "".join(prompt_parts)
