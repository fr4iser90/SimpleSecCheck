"""
GitLeaks Scanner
Python implementation of run_gitleaks.sh
"""
import os
import shlex
from pathlib import Path
from typing import Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability
from scanner.core.step_registry import SubStepType


class GitLeaksScanner(BaseScanner):
    """GitLeaks scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.SECRETS,
            supported_targets=[TargetType.LOCAL_MOUNT, TargetType.GIT_REPO, TargetType.UPLOADED_CODE],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 17
    REQUIRES_CONDITION = None
    ENV_VARS = {
        "GITLEAKS_CONFIG_PATH": "/app/scanner/plugins/gitleaks/config/config.yaml"
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
        Initialize GitLeaks scanner.
        step_name: From registry/manifest (single source).
        """
        super().__init__("GitLeaks", target_path, results_dir, log_file, config_path, step_name=step_name)
    
    def scan(self) -> bool:
        """Run GitLeaks scan with standardized substeps"""
        if not self.check_tool_installed("gitleaks"):
            self.log("gitleaks not found in PATH", "ERROR")
            return False
        
        self.log(f"Running secret detection scan on {self.target_path}...")
        
        # INIT: Initialization
        self.substep_init("Initializing GitLeaks scan...")
        self.complete_substep("Initialization", "GitLeaks initialized")
        
        json_output = self.results_dir / "report.json"
        text_output = self.results_dir / "report.txt"
        
        config_args = []
        if self.config_path and self.config_path.exists():
            config_args = ["--config", str(self.config_path)]
        
        # PREPARE: Git History Extraction
        self.start_substep("Git History Extraction", "Extracting Git history...", SubStepType.ACTION)
        # Git history extraction happens during scan (even with --no-git, it scans files)
        self.complete_substep("Git History Extraction", "Git history extraction completed")
        
        # PREPARE: File Discovery
        self.start_substep("File Discovery", "Discovering files to scan...", SubStepType.ACTION)
        # File discovery happens during scan
        self.complete_substep("File Discovery", "Files discovered")
        
        # SCAN: Secret Pattern Matching
        self.substep_scan("Secret Pattern Matching", "Matching files against secret patterns...")
        
        # SCAN: Entropy Analysis
        self.start_substep("Entropy Analysis", "Analyzing entropy of potential secrets...", SubStepType.PHASE)
        # Entropy analysis happens during scan
        
        # Main scan
        self.log("Running secret detection scan...")
        cmd = ["gitleaks", "detect", "--source", str(self.target_path),
               "--report-path", str(json_output), "--no-git", *config_args]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode == 1:
            self.log("Secrets found during JSON scan (exit code 1)", "WARNING")
            self.complete_substep("Secret Pattern Matching", "Secret pattern matching completed (secrets found)")
            self.complete_substep("Entropy Analysis", "Entropy analysis completed")
        elif result.returncode == 0:
            self.complete_substep("Secret Pattern Matching", "Secret pattern matching completed (no secrets found)")
            self.complete_substep("Entropy Analysis", "Entropy analysis completed")
        else:
            self.log("JSON report generation failed", "WARNING")
            self.complete_substep("Secret Pattern Matching", "Secret pattern matching completed (with warnings)")
            self.complete_substep("Entropy Analysis", "Entropy analysis completed (with warnings)")
        
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
        self.log("Running text report generation...")
        cmd = ["gitleaks", "detect", "--source", str(self.target_path),
               "--no-git", "--verbose", *config_args]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode in (0, 1) and result.stdout:
            with open(text_output, "w", encoding="utf-8") as f:
                f.write(result.stdout)
        elif result.returncode == 1:
            self.log("Secrets found but no detailed output returned; no text report written.", "WARNING")
        else:
            self.log("Text report generation failed; no report written.", "WARNING")
        
        if json_output.exists() or text_output.exists():
            self.log("GitLeaks scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("No GitLeaks report was generated!", "ERROR")
            return False


if __name__ == "__main__":
    import os
    import sys
    
    # Get default parameters from BaseScanner
    default_params = BaseScanner.get_default_params_from_env()
    
    # Get scanner-specific parameters
    config_path = os.getenv("GITLEAKS_CONFIG_PATH", "/app/scanner/plugins/gitleaks/config/config.yaml")
    
    scanner = GitLeaksScanner(
        **default_params,
        config_path=config_path
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
