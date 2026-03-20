"""
Detect-secrets Scanner
Python implementation of run_detect_secrets.sh
"""
import os
import shlex
from pathlib import Path
from typing import List, Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability


class DetectSecretsScanner(BaseScanner):
    """Detect-secrets scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.SECRETS,
            supported_targets=[TargetType.LOCAL_MOUNT, TargetType.GIT_REPO, TargetType.UPLOADED_CODE],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 18
    REQUIRES_CONDITION = None
    ENV_VARS = {
        "DETECT_SECRETS_CONFIG_PATH": "/app/scanner/plugins/detect_secrets/config/config.yaml"
    }
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None,
        exclude_paths: Optional[str] = None,
        step_name: Optional[str] = None,
    ):
        """
        Initialize Detect-secrets scanner.
        step_name: From registry/manifest (single source).
        """
        super().__init__("Detect-secrets", target_path, results_dir, log_file, config_path, step_name=step_name)
        self.exclude_paths = exclude_paths or os.getenv("SIMPLESECCHECK_EXCLUDE_PATHS", "")
    
    def get_exclude_args(self) -> List[str]:
        """Get detect-secrets exclude arguments"""
        exclude_args = []
        
        if self.exclude_paths:
            for path in self.exclude_paths.split(","):
                path = path.strip()
                if path:
                    exclude_args.extend(["--exclude-files", f".*/{path}/.*"])
        
        return exclude_args
    
    def scan(self) -> bool:
        """Run Detect-secrets scan"""
        if not self.check_tool_installed("detect-secrets"):
            self.log("detect-secrets not found in PATH", "ERROR")
            return False
        
        self.log(f"Running secret detection scan on {self.target_path}...")
        
        json_output = self.results_dir / "report.json"  # Changed from detect-secrets.json
        text_output = self.results_dir / "report.txt"   # Changed from detect-secrets.txt
        
        exclude_args = self.get_exclude_args()
        extra = shlex.split(os.getenv("DETECT_SECRETS_EXTRA_ARGS", "").strip())
        
        # JSON report
        self.log("Running secret detection scan...")
        cmd = ["detect-secrets", "scan", "--all-files", *exclude_args, *extra, str(self.target_path)]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode == 0 and result.stdout:
            with open(json_output, "w", encoding="utf-8") as f:
                f.write(result.stdout)
        else:
            self.log("JSON report generation failed; no report written.", "WARNING")
        
        # Text report (same command, different output)
        self.log("Running text report generation...")
        result = self.run_command(cmd, capture_output=True)
        if result.returncode == 0 and result.stdout:
            with open(text_output, "w", encoding="utf-8") as f:
                f.write(result.stdout)
        else:
            self.log("Text report generation failed; no text report written.", "WARNING")
        
        if json_output.exists() or text_output.exists():
            self.log("Detect-secrets scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("No detect-secrets report was generated!", "ERROR")
            return False


if __name__ == "__main__":
    import sys
    
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/app/results")
    log_file = os.getenv("LOG_FILE", "app/results/logs/scan.log")
    config_path = os.getenv("DETECT_SECRETS_CONFIG_PATH", "/app/scanner/plugins/detect_secrets/config/config.yaml")
    exclude_paths = os.getenv("SIMPLESECCHECK_EXCLUDE_PATHS", "")
    
    scanner = DetectSecretsScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path,
        exclude_paths=exclude_paths
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
