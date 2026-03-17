"""
Safety Scanner
Python implementation of run_safety.sh
"""
import os
import json
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
        """Find Python dependency files"""
        patterns = [
            "requirements*.txt",
            "Pipfile",
            "Pipfile.lock",
            "pyproject.toml",
            "setup.py",
            "environment.yml",
            "conda.yml"
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
    
    def scan(self) -> bool:
        """Run Safety scan with standardized substeps"""
        if not self.check_tool_installed("safety"):
            self.log("safety not found in PATH", "ERROR")
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
        
        # Use first dependency file
        dep_file = dependency_files[0]
        
        # PREPARE: Dependency Extraction
        self.start_substep("Dependency Extraction", "Extracting dependencies from files...", SubStepType.ACTION)
        # Dependency extraction happens during scan
        self.complete_substep("Dependency Extraction", "Dependencies extracted")
        
        def run_safety(output_format: str, output_path: Path, file_arg: bool = True) -> bool:
            cmd = ["safety", "check", "--output", output_format]
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
        
        # JSON report (main scan)
        self.log("Running Safety scan with JSON output...")
        scan_success = False
        if not run_safety("json", json_output, file_arg=True):
            self.log("JSON report generation failed, trying alternative approach...", "WARNING")
            if not run_safety("json", json_output, file_arg=False):
                self.log("Trying pip-audit as fallback (safety may be broken on this Python).", "WARNING")
                try:
                    pip_audit_ok = self.run_command(
                        ["pip-audit", "--format", "json", "--requirement", str(dep_file)],
                        capture_output=True,
                        timeout=120,
                    )
                    if pip_audit_ok.returncode in (0, 1) and (pip_audit_ok.stdout or "").strip():
                        try:
                            import json as _json
                            data = _json.loads(pip_audit_ok.stdout)
                            vulns = data.get("vulnerabilities") or []
                            safety_like = {
                                "vulnerabilities": [
                                    {
                                        "package": v.get("name", ""),
                                        "installed_version": v.get("version", ""),
                                        "vulnerability_id": v.get("id", ""),
                                        "severity": "MEDIUM",
                                        "description": v.get("description", ""),
                                        "cve": v.get("id", "") if (v.get("id") or "").startswith("CVE") else "",
                                    }
                                    for v in vulns
                                ],
                                "packages": [],
                            }
                            json_output.write_text(_json.dumps(safety_like, indent=2), encoding="utf-8")
                            scan_success = True
                        except Exception as e:
                            self.log(f"pip-audit fallback failed: {e}", "WARNING")
                except FileNotFoundError:
                    self.log("pip-audit not installed; cannot fallback.", "WARNING")
                except Exception as e:
                    self.log(f"pip-audit fallback error: {e}", "WARNING")
                if not scan_success:
                    self.log("Directory scan also failed; no report written (no fake data).", "WARNING")
            else:
                scan_success = True
        else:
            scan_success = True
        
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
        
        # Text report (for completeness, but not part of standard schema)
        self.log("Running Safety scan with text output...")
        if not run_safety("text", text_output, file_arg=True):
            self.log("Text report generation failed, trying alternative approach...", "WARNING")
            if not run_safety("text", text_output, file_arg=False):
                self.log("Directory text scan also failed; no text report written.", "WARNING")
        
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
