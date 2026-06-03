"""
Safety Scanner
Python implementation of run_safety.sh
"""
import os
import json
import shlex
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability
from scanner.core.step_registry import SubStepType


class SafetyScanner(BaseScanner):
    """Safety scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.DEPENDENCY,
            supported_targets=[TargetType.LOCAL_MOUNT, TargetType.GIT_REPO, TargetType.UPLOADED_CODE],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 5
    REQUIRES_CONDITION = None
    ENV_VARS = {
        "SAFETY_CONFIG_PATH": "/app/scanner/plugins/safety/config/config.yaml"
    }
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None,
        step_name: Optional[str] = None,
    ):
        """
        Initialize Safety scanner.

        step_name: From registry/manifest (single source).
        """
        super().__init__("Safety", target_path, results_dir, log_file, config_path, step_name=step_name)
    
    def find_dependency_files(self) -> List[Path]:
        """Find Python dependency files (requirements*.txt, Pipfile, pyproject.toml, etc.).
        Excludes setup.py to avoid false positives (e.g. backend/api/routes/setup.py).
        """
        patterns = [
            "requirements*.txt",
            "Pipfile",
            "Pipfile.lock",
            "pyproject.toml",
            "environment.yml",
            "conda.yml",
        ]
        dependency_files = []
        for pattern in patterns:
            for file in self.target_path.rglob(pattern):
                if file.is_file():
                    dependency_files.append(file)
        return dependency_files
    
    def create_empty_reports(self):
        """Create empty reports when no dependency files found"""
        json_output = self.results_dir / "report.json"  # Changed from safety.json
        text_output = self.results_dir / "report.txt"   # Changed from safety.txt
        
        # Empty JSON report
        empty_json = {
            "vulnerabilities": [],
            "packages": [],
            "summary": {
                "total_packages": 0,
                "vulnerable_packages": 0,
                "total_vulnerabilities": 0
            }
        }
        with open(json_output, "w", encoding="utf-8") as f:
            json.dump(empty_json, f, indent=2)
        
        # Empty text report
        with open(text_output, "w", encoding="utf-8") as f:
            f.write("Safety Scan Results\n")
            f.write("===================\n")
            f.write("No Python dependency files found.\n")
            f.write(f"Scan completed at: {datetime.now().isoformat()}\n")

    def _safety_cli_works(self) -> bool:
        cached = getattr(self, "_safety_cli_works_cache", None)
        if cached is not None:
            return cached
        result = self.run_command(
            ["python3", "-c", "from safety.cli import cli"],
            capture_output=True,
        )
        ok = result.returncode == 0
        self._safety_cli_works_cache = ok
        return ok

    def _pip_audit_args_for_file(self, dep_file: Path) -> List[str]:
        name = dep_file.name.lower()
        if name in ("pyproject.toml", "pipfile"):
            return ["--path", str(dep_file.parent)]
        return ["--requirement", str(dep_file)]

    def _parse_pip_audit_json(self, raw: str) -> List[dict]:
        data = json.loads(raw)
        vulns: List[dict] = []
        if isinstance(data, list):
            for dep in data:
                for v in dep.get("vulns") or []:
                    vulns.append(
                        {
                            "package": dep.get("name", ""),
                            "installed_version": dep.get("version", ""),
                            "vulnerability_id": v.get("id", ""),
                            "severity": "MEDIUM",
                            "description": v.get("description", ""),
                            "cve": v.get("id", "")
                            if (v.get("id") or "").startswith("CVE")
                            else "",
                        }
                    )
            return vulns
        for v in data.get("vulnerabilities") or []:
            vulns.append(
                {
                    "package": v.get("name", v.get("package", "")),
                    "installed_version": v.get("version", v.get("installed_version", "")),
                    "vulnerability_id": v.get("id", v.get("vulnerability_id", "")),
                    "severity": v.get("severity", "MEDIUM"),
                    "description": v.get("description", ""),
                    "cve": v.get("id", "")
                    if (v.get("id") or "").startswith("CVE")
                    else v.get("cve", ""),
                }
            )
        return vulns

    def _run_pip_audit_all(self, dependency_files: List[Path], json_output: Path) -> bool:
        merged: List[dict] = []
        seen: set = set()
        for dep_file in dependency_files:
            cmd = ["pip-audit", "--format", "json", *self._pip_audit_args_for_file(dep_file)]
            try:
                result = self.run_command(cmd, capture_output=True, cwd=self.target_path)
            except FileNotFoundError:
                self.log("pip-audit not installed; cannot scan Python dependencies.", "WARNING")
                return False
            if result.returncode not in (0, 1):
                self.log(
                    f"pip-audit failed for {dep_file} (exit {result.returncode})",
                    "WARNING",
                )
                continue
            content = (result.stdout or "").strip()
            if not content:
                continue
            try:
                for item in self._parse_pip_audit_json(content):
                    key = (
                        item.get("package"),
                        item.get("vulnerability_id"),
                        item.get("installed_version"),
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    merged.append(item)
            except json.JSONDecodeError as e:
                self.log(f"pip-audit JSON parse failed for {dep_file}: {e}", "WARNING")
        if not merged:
            return False
        payload = {"vulnerabilities": merged, "packages": []}
        json_output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return True
    
    def scan(self) -> bool:
        """Run Safety scan with standardized substeps"""
        has_safety = self.check_tool_installed("safety")
        has_pip_audit = self.check_tool_installed("pip-audit")
        if not has_safety and not has_pip_audit:
            self.log("Neither safety nor pip-audit found in PATH", "ERROR")
            return False
        
        self.log(f"Running Python dependency security scan on {self.target_path}...")
        
        # INIT: Initialization
        self.substep_init("Initializing Safety scan...")
        self.complete_substep("Initialization", "Safety initialized")
        
        # PREPARE: Requirements Detection
        self.start_substep("Requirements Detection", "Detecting Python dependency files...", SubStepType.ACTION)
        dependency_files = self.find_dependency_files()
        
        if not dependency_files:
            self.complete_substep("Requirements Detection", "No Python dependency files found")
            self.log("No Python dependency files found", "WARNING")
            self.create_empty_reports()
            return True
        
        self.complete_substep("Requirements Detection", f"Found {len(dependency_files)} dependency file(s)")
        self.log(f"Found {len(dependency_files)} dependency file(s):")
        for file in dependency_files:
            self.log(f"  - {file}")
        
        json_output = self.results_dir / "report.json"
        text_output = self.results_dir / "report.txt"
        
        # PREPARE: Dependency Extraction
        self.start_substep("Dependency Extraction", "Extracting dependencies from files...", SubStepType.ACTION)
        # Dependency extraction happens during scan
        self.complete_substep("Dependency Extraction", "Dependencies extracted")

        def _safety_extra_for_output(output_format: str) -> List[str]:
            """Strip flags that newer Safety CLI rejects together with ``--output`` (e.g. admin env)."""
            tokens = shlex.split(os.getenv("SAFETY_EXTRA_ARGS", "").strip())
            if output_format not in ("json", "bare"):
                return tokens
            out: List[str] = []
            i = 0
            while i < len(tokens):
                t = tokens[i]
                if t in ("--full-report", "--json", "--bare"):
                    i += 1
                    continue
                if t.startswith("--full-report="):
                    i += 1
                    continue
                if t == "--output":
                    i += 2 if i + 1 < len(tokens) else 1
                    continue
                if t.startswith("--output="):
                    i += 1
                    continue
                out.append(t)
                i += 1
            return out

        def run_safety(output_format: str, output_path: Path, file_arg: bool = True) -> bool:
            extra = _safety_extra_for_output(output_format)
            cmd = ["safety", "check", *extra, "--output", output_format]
            if file_arg:
                cmd.extend(["--file", str(dep_file)])
            result = self.run_command(cmd, cwd=self.target_path, capture_output=True)
            if result.returncode not in (0, 1):
                return False
            content = (result.stdout or "").strip()
            if content:
                output_path.write_text(content, encoding="utf-8")
                return True
            return False

        # SCAN: Vulnerability Lookup
        self.start_substep("Vulnerability Lookup", "Checking dependencies against vulnerability database...", SubStepType.PHASE)

        scan_success = False
        use_pip_audit = not self._safety_cli_works()
        if use_pip_audit:
            self.log(
                "Safety CLI is broken on this image (typer/safety mismatch); using pip-audit.",
                "WARNING",
            )
            scan_success = self._run_pip_audit_all(dependency_files, json_output)
        else:
            dep_file = dependency_files[0]
            self.log("Running Safety scan with JSON output...")
            if run_safety("json", json_output, file_arg=True):
                scan_success = True
            elif run_safety("json", json_output, file_arg=False):
                scan_success = True
            else:
                self.log("Safety JSON failed; falling back to pip-audit.", "WARNING")
                scan_success = self._run_pip_audit_all(dependency_files, json_output)

        if scan_success:
            self.complete_substep("Vulnerability Lookup", "Vulnerability lookup completed")
        else:
            self.complete_substep("Vulnerability Lookup", "Vulnerability lookup completed (with warnings)")

        # PROCESS: Result Processing
        self.substep_process("Result Processing", "Processing scan results...")
        self.complete_substep("Result Processing", "Results processed")

        # REPORT: JSON Report
        self.substep_report("JSON", "Generating JSON report...")
        if json_output.exists() and json_output.stat().st_size > 0:
            self.complete_substep("Generating JSON Report", "JSON report generated successfully")
        else:
            self.fail_substep("Generating JSON Report", "JSON report generation failed")

        if not use_pip_audit and scan_success:
            self.log("Running Safety scan with text output...")
            dep_file = dependency_files[0]
            if not run_safety("text", text_output, file_arg=True):
                if not run_safety("text", text_output, file_arg=False):
                    self.log("Text report generation failed; JSON report is still valid.", "WARNING")
        elif scan_success and json_output.exists():
            try:
                data = json.loads(json_output.read_text(encoding="utf-8"))
                lines = ["Safety / pip-audit Scan Results", "===========================", ""]
                for v in data.get("vulnerabilities") or []:
                    lines.append(
                        f"- {v.get('package', '?')} {v.get('installed_version', '')}: "
                        f"{v.get('vulnerability_id', '')} — {v.get('description', '')[:120]}"
                    )
                if len(lines) <= 3:
                    lines.append("No vulnerabilities reported.")
                lines.append(f"\nScan completed at: {datetime.now().isoformat()}\n")
                text_output.write_text("\n".join(lines), encoding="utf-8")
            except (OSError, json.JSONDecodeError):
                pass
        
        # Check if reports were generated
        if json_output.exists() or text_output.exists():
            self.log("Safety scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("Safety scan completed but no results generated", "ERROR")
            return False


if __name__ == "__main__":
    import os
    import sys
    
    # Get default parameters from BaseScanner
    default_params = BaseScanner.get_default_params_from_env()
    
    # Get scanner-specific parameters
    config_path = os.getenv("SAFETY_CONFIG_PATH", "/app/scanner/plugins/safety/config/config.yaml")
    
    scanner = SafetyScanner(
        **default_params,
        config_path=config_path
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
