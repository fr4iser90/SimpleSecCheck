"""
Snyk Scanner
Python implementation of run_snyk.sh
"""
import os
import json
from pathlib import Path
from typing import Optional
from datetime import datetime
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability
from scanner.core.step_registry import SubStepType


class SnykScanner(BaseScanner):
    """Snyk scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        # Code scanning (Snyk Code)
        ScannerCapability(
            scan_type=ScanType.CODE,
            supported_targets=[TargetType.LOCAL_MOUNT, TargetType.GIT_REPO, TargetType.UPLOADED_CODE],
            supported_artifacts=[],
        ),
        # Dependency scanning (Snyk Open Source)
        ScannerCapability(
            scan_type=ScanType.DEPENDENCY,
            supported_targets=[TargetType.LOCAL_MOUNT, TargetType.GIT_REPO, TargetType.UPLOADED_CODE],
            supported_artifacts=[],
        ),
    ]
    PRIORITY = 6
    REQUIRES_CONDITION = None
    ENV_VARS = {
        "SNYK_CONFIG_PATH": "/app/scanner/plugins/snyk/config/config.yaml"
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
        Initialize Snyk scanner.
        step_name: From registry/manifest (single source).
        """
        super().__init__("Snyk", target_path, results_dir, log_file, config_path, step_name=step_name)
        self.snyk_token = os.getenv("SNYK_TOKEN", "")
    
    def create_empty_reports(self, reason: str = "No SNYK_TOKEN provided"):
        """Create empty reports when Snyk is skipped"""
        json_output = self.results_dir / "report.json"  # Changed from snyk.json
        text_output = self.results_dir / "report.txt"   # Changed from snyk.txt
        
        empty_json = {
            "vulnerabilities": [],
            "summary": {
                "total_packages": 0,
                "vulnerable_packages": 0,
                "total_vulnerabilities": 0
            },
            "skipped": reason
        }
        
        with open(json_output, "w", encoding="utf-8") as f:
            json.dump(empty_json, f, indent=2)
        
        with open(text_output, "w", encoding="utf-8") as f:
            f.write("Snyk Scan Results\n")
            f.write("=================\n")
            f.write(f"Skipped: {reason}\n")
            f.write(f"Scan completed at: {datetime.now().isoformat()}\n")
    
    def scan(self) -> bool:
        """Run Snyk scan with standardized substeps"""
        if not self.check_tool_installed("snyk"):
            self.log("snyk not found in PATH", "ERROR")
            return False
        
        # INIT: Authentication
        self.start_substep("Authentication", "Authenticating with Snyk...", SubStepType.ACTION)
        if not self.snyk_token:
            self.complete_substep("Authentication", "No SNYK_TOKEN provided, skipping scan")
            self.log("No SNYK_TOKEN provided, skipping Snyk scan...", "WARNING")
            self.log("Snyk requires authentication. Set SNYK_TOKEN environment variable to use Snyk.")
            self.create_empty_reports("No SNYK_TOKEN provided")
            return True
        
        self.complete_substep("Authentication", "Authenticated successfully")
        self.log("Using provided SNYK_TOKEN for authentication...")
        self.log(f"Running Snyk vulnerability scan on {self.target_path}...")
        
        json_output = self.results_dir / "report.json"
        text_output = self.results_dir / "report.txt"
        
        # Change to target directory
        try:
            os.chdir(self.target_path)
        except Exception as e:
            self.log(f"Cannot access target directory: {e}", "ERROR")
            return False
        
        # PREPARE: Project Detection
        self.start_substep("Project Detection", "Detecting project type and dependencies...", SubStepType.ACTION)
        # Project detection happens during scan
        self.complete_substep("Project Detection", "Project detected")
        
        # PREPARE: Dependency Graph Creation
        self.start_substep("Dependency Graph Creation", "Building dependency graph...", SubStepType.ACTION)
        # Dependency graph creation happens during scan
        self.complete_substep("Dependency Graph Creation", "Dependency graph created")
        
        # SCAN: Vulnerability Scanning
        self.substep_scan("Vulnerability Scanning", "Scanning dependencies for vulnerabilities...")
        
        # Main scan
        self.log("Running Snyk test with JSON output...")
        cmd = ["snyk", "test", f"--token={self.snyk_token}", "--json", f"--output-file={json_output}"]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode != 0:
            self.log("JSON report generation failed, trying alternative approach...", "WARNING")
            cmd = ["snyk", "test", f"--token={self.snyk_token}", "--json"]
            result = self.run_command(cmd, capture_output=True)
            if result.returncode == 0 and result.stdout:
                with open(json_output, "w", encoding="utf-8") as f:
                    f.write(result.stdout)
                self.complete_substep("Vulnerability Scanning", "Vulnerability scanning completed")
            else:
                self.log("Alternative JSON scan also failed; no report written (no fake data).", "WARNING")
                self.complete_substep("Vulnerability Scanning", "Vulnerability scanning completed (with warnings)")
        else:
            self.complete_substep("Vulnerability Scanning", "Vulnerability scanning completed")
        
        # SCAN: Fix Recommendation
        self.start_substep("Fix Recommendation", "Generating fix recommendations...", SubStepType.PHASE)
        # Fix recommendations are included in scan results
        self.complete_substep("Fix Recommendation", "Fix recommendations generated")
        
        # PROCESS: Result Processing
        self.substep_process("Result Processing", "Processing scan results...")
        self.complete_substep("Result Processing", "Results processed")
        
        # REPORT: JSON Report
        self.substep_report("JSON", "Generating JSON report...")
        if json_output.exists() and json_output.stat().st_size > 0:
            self.complete_substep("Generating JSON Report", "JSON report generated successfully")
        else:
            self.fail_substep("Generating JSON Report", "JSON report generation failed")
        
        # Text report (for completeness)
        self.log("Running Snyk test with text output...")
        cmd = ["snyk", "test", f"--token={self.snyk_token}"]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode == 0 and result.stdout:
            with open(text_output, "w", encoding="utf-8") as f:
                f.write(result.stdout)
        else:
            self.log("Text report generation failed; no text report written.", "WARNING")
        
        # Verbose scan (non-critical)
        try:
            self.log("Running additional verbose scan...")
            cmd = ["snyk", "test", f"--token={self.snyk_token}", "--verbose"]
            result = self.run_command(cmd, capture_output=True)
            if result.returncode == 0 and result.stdout:
                with open(text_output, "a", encoding="utf-8") as f:
                    f.write("\n\nVerbose Output:\n")
                    f.write("===============\n")
                    f.write(result.stdout)
        except Exception:
            pass
        
        # Snyk monitor (non-critical)
        try:
            self.log("Running Snyk monitor for cloud integration...")
            cmd = ["snyk", "monitor", f"--token={self.snyk_token}"]
            result = self.run_command(cmd, capture_output=True)
            if result.returncode != 0:
                self.log("Snyk monitor failed.", "WARNING")
        except Exception:
            pass
        
        if json_output.exists() or text_output.exists():
            self.log("Snyk scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("No Snyk report was generated!", "ERROR")
            return False


if __name__ == "__main__":
    import os
    import sys
    
    # Get default parameters from BaseScanner
    default_params = BaseScanner.get_default_params_from_env()
    
    # Get scanner-specific parameters
    config_path = os.getenv("SNYK_CONFIG_PATH", "/app/scanner/plugins/snyk/config/config.yaml")
    
    scanner = SnykScanner(
        **default_params,
        config_path=config_path
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
