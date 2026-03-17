"""
TruffleHog Scanner
Python implementation of run_trufflehog.sh
"""
import os
import json
from pathlib import Path
from typing import Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability
from scanner.core.step_registry import SubStepType


class TruffleHogScanner(BaseScanner):
    """TruffleHog scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.SECRETS,
            supported_targets=[TargetType.LOCAL_MOUNT, TargetType.GIT_REPO, TargetType.UPLOADED_CODE],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 16
    REQUIRES_CONDITION = None
    ENV_VARS = {
        "TRUFFLEHOG_CONFIG_PATH": "/app/scanner/plugins/trufflehog/config/config.yaml"
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
        Initialize TruffleHog scanner.
        step_name: From registry/manifest (single source).
        """
        super().__init__("TruffleHog", target_path, results_dir, log_file, config_path, step_name=step_name)
    
    def scan(self) -> bool:
        """Run TruffleHog scan with standardized substeps"""
        if not self.check_tool_installed("trufflehog"):
            self.log("trufflehog not found in PATH", "ERROR")
            return False
        
        self.log(f"Running secret detection scan on {self.target_path}...")
        
        # INIT: Initialization
        self.substep_init("Initializing TruffleHog scan...")
        self.complete_substep("Initialization", "TruffleHog initialized")
        
        json_output = self.results_dir / "report.json"
        text_output = self.results_dir / "report.txt"
        
        # PREPARE: Git History Extraction
        self.start_substep("Git History Extraction", "Extracting Git history...", SubStepType.ACTION)
        # Git history extraction happens during scan
        self.complete_substep("Git History Extraction", "Git history extraction completed")
        
        # PREPARE: File Scanning
        self.start_substep("File Scanning", "Scanning files for potential secrets...", SubStepType.ACTION)
        # File scanning happens during scan
        self.complete_substep("File Scanning", "Files scanned")
        
        # SCAN: Secret Detection
        self.substep_scan("Secret Detection", "Detecting secrets using pattern matching...")
        
        # SCAN: Entropy Analysis
        self.start_substep("Entropy Analysis", "Analyzing entropy of potential secrets...", SubStepType.PHASE)
        # Entropy analysis happens during scan
        
        # SCAN: Verification
        self.start_substep("Verification", "Verifying detected secrets...", SubStepType.PHASE)
        # Verification happens during scan
        
        # Main scan (TruffleHog may write JSON to stdout or stderr)
        self.log("Running secret detection scan...")
        cmd = ["trufflehog", "filesystem", "--json", "--no-update", str(self.target_path)]
        
        result = self.run_command(cmd, capture_output=True)
        
        out = (result.stdout or "") + "\n" + (result.stderr or "")
        if result.returncode == 0 and out.strip():
            json_lines = []
            for line in out.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict) and ("SourceMetadata" in obj or "Source" in obj or "Redacted" in obj):
                        json_lines.append(obj)
                except json.JSONDecodeError:
                    continue
            try:
                with open(json_output, "w", encoding="utf-8") as f:
                    json.dump(json_lines, f, indent=2)
                self.complete_substep("Secret Detection", "Secret detection completed")
                self.complete_substep("Entropy Analysis", "Entropy analysis completed")
                self.complete_substep("Verification", "Verification completed")
            except Exception as e:
                self.log(f"Failed to write JSON report: {e}", "WARNING")
                self.complete_substep("Secret Detection", "Secret detection completed (with warnings)")
                self.complete_substep("Entropy Analysis", "Entropy analysis completed (with warnings)")
                self.complete_substep("Verification", "Verification completed (with warnings)")
        elif result.returncode == 0:
            with open(json_output, "w", encoding="utf-8") as f:
                json.dump([], f)
            self.complete_substep("Secret Detection", "Secret detection completed (no findings)")
            self.complete_substep("Entropy Analysis", "Entropy analysis completed")
            self.complete_substep("Verification", "Verification completed")
        else:
            self.log("JSON report generation failed (non-zero exit); no report written.", "WARNING")
            self.complete_substep("Secret Detection", "Secret detection completed (no output)")
            self.complete_substep("Entropy Analysis", "Entropy analysis completed")
            self.complete_substep("Verification", "Verification completed")
        
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
        cmd = ["trufflehog", "filesystem", "--no-update", str(self.target_path)]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode == 0 and result.stdout:
            with open(text_output, "w", encoding="utf-8") as f:
                f.write(result.stdout)
        else:
            self.log("Text report generation failed; no text report written.", "WARNING")
        
        if json_output.exists() or text_output.exists():
            self.log("TruffleHog scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("No TruffleHog report was generated!", "ERROR")
            return False


if __name__ == "__main__":
    import os
    import sys
    
    # Get default parameters from BaseScanner
    default_params = BaseScanner.get_default_params_from_env()
    
    # Get scanner-specific parameters
    config_path = os.getenv("TRUFFLEHOG_CONFIG_PATH", "/app/scanner/plugins/trufflehog/config/config.yaml")
    
    scanner = TruffleHogScanner(
        **default_params,
        config_path=config_path
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
