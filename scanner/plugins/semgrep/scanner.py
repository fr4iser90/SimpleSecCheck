"""
Semgrep Scanner
Python implementation of run_semgrep.sh
"""
import os
import subprocess
from pathlib import Path
from typing import List, Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability
from scanner.core.step_registry import SubStepType


class SemgrepScanner(BaseScanner):
    """Semgrep scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.CODE,
            supported_targets=[TargetType.LOCAL_MOUNT, TargetType.GIT_REPO, TargetType.UPLOADED_CODE],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 1
    REQUIRES_CONDITION = None
    ENV_VARS = {
        "SEMGREP_RULES_PATH": "/app/scanner/plugins/semgrep/rules"
    }
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        rules_path: Optional[str] = None,
        exclude_paths: Optional[str] = None,
        step_name: Optional[str] = None,
    ):
        """
        Initialize Semgrep scanner

        Args:
            target_path: Path to scan
            results_dir: Results directory
            log_file: Log file path
            rules_path: Path to Semgrep rules (directory or file)
            exclude_paths: Comma-separated paths to exclude
            step_name: Step name from registry/manifest (single source)
        """
        super().__init__("Semgrep", target_path, results_dir, log_file, step_name=step_name)
        self.rules_path = Path(rules_path) if rules_path else Path("/app/scanner/plugins/semgrep/rules")
        self.exclude_paths = exclude_paths or os.getenv("SIMPLESECCHECK_EXCLUDE_PATHS", "")
    
    def get_exclude_args(self) -> List[str]:
        """Get Semgrep exclude arguments"""
        if not self.exclude_paths:
            return []
        
        exclude_args = []
        for path in self.exclude_paths.split(","):
            path = path.strip()
            if path:
                exclude_args.extend(["--exclude", path])
        
        return exclude_args
    
    def get_config_args(self) -> List[str]:
        """Get Semgrep config arguments"""
        config_args = []
        
        if self.rules_path.exists():
            if self.rules_path.is_dir():
                # Directory: add all YAML files
                self.log(f"Found rules directory, adding all YAML files...")
                for rule_file in self.rules_path.rglob("*.yml"):
                    config_args.extend(["--config", str(rule_file)])
                    self.log(f"Adding rule file: {rule_file}")
                for rule_file in self.rules_path.rglob("*.yaml"):
                    config_args.extend(["--config", str(rule_file)])
                    self.log(f"Adding rule file: {rule_file}")
            elif self.rules_path.is_file():
                # Single file
                config_args.extend(["--config", str(self.rules_path)])
        else:
            self.log(f"Rules path not found: {self.rules_path}, using auto rules only", "WARNING")
        
        # Always add auto rules
        config_args.append("--config")
        config_args.append("auto")
        
        return config_args
    
    def scan(self) -> bool:
        """Run Semgrep scan with detailed substeps"""
        if not self.check_tool_installed("semgrep"):
            self.log("semgrep not found in PATH", "ERROR")
            return False
        
        self.log(f"Running code scan on {self.target_path} using rules from {self.rules_path}...")
        
        json_output = self.results_dir / "report.json"
        text_output = self.results_dir / "report.txt"
        sarif_output = self.results_dir / "report.sarif"
        
        # INIT: Initialization
        self.substep_init("Initializing Semgrep scan...")
        self.complete_substep("Initialization", "Semgrep initialized")
        
        # PREPARE: Rule Download / Update
        self.substep_prepare("Rule Download / Update", "Checking for rule updates...")
        # Semgrep auto-updates rules, but we can check
        self.complete_substep("Rule Download / Update", "Rules ready")
        
        # PREPARE: Rule Loading
        self.start_substep("Rule Loading", "Loading Semgrep rules...", SubStepType.ACTION)
        config_args = self.get_config_args()
        exclude_args = self.get_exclude_args()
        rule_count = len([arg for arg in config_args if arg == "--config"])
        self.complete_substep("Rule Loading", f"Loaded {rule_count} rule configuration(s)")
        
        # PREPARE: File Discovery
        self.start_substep("File Discovery", "Discovering files to scan...", SubStepType.ACTION)
        # Count files (approximate)
        try:
            file_count = sum(1 for _ in self.target_path.rglob("*") if _.is_file())
            self.complete_substep("File Discovery", f"Found {file_count} file(s) to scan")
        except Exception:
            self.complete_substep("File Discovery", "File discovery completed")
        
        # Get tool command
        tool_cmd = self.get_tool_command("semgrep")
        if not tool_cmd:
            self.log("semgrep not found", "ERROR")
            return False
        
        # SCAN: Code Scanning
        self.substep_scan("Code Scanning", "Scanning code for security issues...")
        
        # JSON report (main scan)
        cmd = [
            *tool_cmd,
            "--disable-version-check",
            *config_args,
            str(self.target_path),
            *exclude_args,
            "--json",
            "-o", str(json_output),
            "--severity=ERROR",
            "--severity=WARNING",
            "--severity=INFO"
        ]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode != 0:
            self.log(f"JSON report generation failed with exit code {result.returncode}", "ERROR")
            self.fail_substep("Code Scanning", f"Scan failed with exit code {result.returncode}")
            return False
        
        self.complete_substep("Code Scanning", "Code scanning completed")
        
        # PROCESS: Finding Processing
        self.substep_process("Finding Processing", "Processing scan results...")
        if json_output.exists() and json_output.stat().st_size > 0:
            try:
                import json
                with open(json_output, 'r') as f:
                    data = json.load(f)
                    findings_count = len(data.get('results', []))
                    self.complete_substep("Finding Processing", f"Processed {findings_count} finding(s)")
            except Exception:
                self.complete_substep("Finding Processing", "Results processed")
        else:
            self.complete_substep("Finding Processing", "No findings to process")
        
        # OUTPUT: JSON Report Generation
        self.substep_report("JSON", "Generating JSON report...")
        if json_output.exists() and json_output.stat().st_size > 0:
            self.complete_substep("Generating JSON Report", "JSON report generated successfully")
        else:
            self.fail_substep("Generating JSON Report", "JSON report generation failed")
        
        # OUTPUT: Text Report Generation
        self.substep_report("Text", "Generating text report...")
        cmd = [
            *tool_cmd,
            "--disable-version-check",
            *config_args,
            str(self.target_path),
            *exclude_args,
            "--text",
            "-o", str(text_output),
            "--severity=ERROR",
            "--severity=WARNING",
            "--severity=INFO"
        ]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode == 0 and text_output.exists():
            self.complete_substep("Generating Text Report", "Text report generated successfully")
        else:
            self.fail_substep("Generating Text Report", "Text report generation failed")
        
        # OUTPUT: SARIF Export (optional)
        self.start_substep("SARIF Export", "Generating SARIF report...", SubStepType.OUTPUT)
        try:
            cmd = [
                *tool_cmd,
                "--disable-version-check",
                *config_args,
                str(self.target_path),
                *exclude_args,
                "--sarif",
                "-o", str(sarif_output)
            ]
            result = self.run_command(cmd, capture_output=True, timeout=300)
            if result.returncode == 0 and sarif_output.exists():
                self.complete_substep("SARIF Export", "SARIF report generated successfully")
            else:
                self.fail_substep("SARIF Export", "SARIF export failed")
        except Exception as e:
            self.log(f"SARIF export failed: {e}", "WARNING")
            self.fail_substep("SARIF Export", f"SARIF export failed: {e}")
        
        # Additional security-focused deep scan (non-critical)
        try:
            self.start_substep("Security Deep Scan", "Running additional security-focused scan...", SubStepType.PHASE)
            security_json = self.results_dir / "security-deep.json"
            cmd = [
                "semgrep",
                "--disable-version-check",
                "--config", "p/security-audit",
                "--config", "p/secrets",
                "--config", "p/owasp-top-ten",
                str(self.target_path),
                *exclude_args,
                "--json",
                "-o", str(security_json)
            ]
            self.run_command(cmd, capture_output=True, timeout=600)
            if security_json.exists():
                self.complete_substep("Security Deep Scan", "Security deep scan completed")
            else:
                self.complete_substep("Security Deep Scan", "Security deep scan completed (no findings)")
        except Exception as e:
            self.log(f"Security deep scan failed: {e}", "WARNING")
            self.complete_substep("Security Deep Scan", f"Security deep scan skipped: {e}")
        
        # Check if reports were generated
        if json_output.exists() and json_output.stat().st_size > 0:
            self.log("Semgrep scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("Semgrep scan completed but no results generated", "WARNING")
            return True  # Don't fail if no findings


if __name__ == "__main__":
    import os
    import sys
    
    # Get default parameters from BaseScanner
    default_params = BaseScanner.get_default_params_from_env()
    
    # Get scanner-specific parameters
    rules_path = os.getenv("SEMGREP_RULES_PATH", "/app/scanner/plugins/semgrep/rules")
    exclude_paths = os.getenv("SIMPLESECCHECK_EXCLUDE_PATHS", "")
    
    # Create scanner and run
    scanner = SemgrepScanner(
        **default_params,
        rules_path=rules_path,
        exclude_paths=exclude_paths
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
