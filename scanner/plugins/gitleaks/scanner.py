"""
GitLeaks Scanner
Python implementation of run_gitleaks.sh
"""
import os
from pathlib import Path
from typing import Optional
from scanner.core.base_scanner import BaseScanner

from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability


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
        "GITLEAKS_CONFIG_PATH": "/app/scanner/scanners/gitleaks/config/config.yaml"
    }
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None
    ):
        """
        Initialize GitLeaks scanner
        
        Args:
            target_path: Path to scan
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to GitLeaks config file
        """
        super().__init__("GitLeaks", target_path, results_dir, log_file, config_path)
    
    def scan(self) -> bool:
        """Run GitLeaks scan"""
        if not self.check_tool_installed("gitleaks"):
            self.log("gitleaks not found in PATH", "ERROR")
            return False
        
        self.log(f"Running secret detection scan on {self.target_path}...")
        
        json_output = self.results_dir / "report.json"  # Changed from gitleaks.json
        text_output = self.results_dir / "report.txt"   # Changed from gitleaks.txt
        
        config_args = []
        if self.config_path and self.config_path.exists():
            config_args = ["--config", str(self.config_path)]
        
        # JSON report
        self.log("Running secret detection scan...")
        cmd = ["gitleaks", "detect", "--source", str(self.target_path),
               "--report-path", str(json_output), "--no-git", *config_args]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode == 1:
            self.log("Secrets found during JSON scan (exit code 1)", "WARNING")
        elif result.returncode != 0:
            self.log("JSON report generation failed", "WARNING")
        
        # Text report
        self.log("Running text report generation...")
        cmd = ["gitleaks", "detect", "--source", str(self.target_path),
               "--no-git", "--verbose", *config_args]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode in (0, 1) and result.stdout:
            with open(text_output, "w", encoding="utf-8") as f:
                f.write(result.stdout)
        elif result.returncode == 1:
            text_output.write_text("Secrets found but no detailed output returned.\n")
        else:
            self.log("Text report generation failed", "WARNING")
            if not text_output.exists():
                text_output.write_text("No secrets found\n")
        
        if json_output.exists() or text_output.exists():
            self.log("GitLeaks scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("No GitLeaks report was generated!", "ERROR")
            return False


if __name__ == "__main__":
    import sys
    
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/app/results")
    log_file = os.getenv("LOG_FILE", "app/results/logs/scan.log")
    config_path = os.getenv("GITLEAKS_CONFIG_PATH", "/app/scanner/scanners/gitleaks/config/config.yaml")
    
    scanner = GitLeaksScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
