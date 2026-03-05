"""
Trivy Scanner
Python implementation of run_trivy.sh
"""
import os
from pathlib import Path
from typing import List, Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability


class TrivyScanner(BaseScanner):
    """Trivy scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.DEPENDENCY,
            supported_targets=[TargetType.LOCAL_CODE, TargetType.GIT_REPO],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 2
    REQUIRES_CONDITION = None
    ENV_VARS = {
        "TRIVY_CONFIG_PATH": "/app/scanner/scanners/trivy/config/config.yaml"
    }
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None,
        scan_type: str = "fs",
        exclude_paths: Optional[str] = None
    ):
        """
        Initialize Trivy scanner
        
        Args:
            target_path: Path to scan
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to Trivy config file
            scan_type: Type of scan ('fs' for filesystem, 'image' for image)
            exclude_paths: Comma-separated paths to exclude
        """
        super().__init__("Trivy", target_path, results_dir, log_file, config_path)
        self.scan_type = scan_type or os.getenv("TRIVY_SCAN_TYPE", "fs")
        self.exclude_paths = exclude_paths or os.getenv("SIMPLESECCHECK_EXCLUDE_PATHS", "")
    
    def get_skip_args(self) -> List[str]:
        """Get Trivy skip arguments"""
        skip_args = ["--skip-files", "**/*.log", "--skip-dirs", "*/node_modules"]
        
        if self.exclude_paths:
            for path in self.exclude_paths.split(","):
                path = path.strip()
                if path:
                    skip_args.extend(["--skip-dirs", f"*/{path}"])
        
        return skip_args
    
    def get_config_args(self) -> List[str]:
        """Get Trivy config arguments"""
        if self.config_path and self.config_path.exists():
            return ["--config", str(self.config_path)]
        else:
            self.log(f"Config file not found at {self.config_path}. Running with Trivy defaults.", "WARNING")
            return []
    
    def scan(self) -> bool:
        """Run Trivy scan"""
        if not self.check_tool_installed("trivy"):
            self.log("trivy not found in PATH", "ERROR")
            return False
        
        self.log(f"Running DEEP {self.scan_type} scan on {self.target_path}...")
        
        json_output = self.results_dir / "trivy.json"
        text_output = self.results_dir / "trivy.txt"
        secrets_output = self.results_dir / "trivy-secrets-config.json"
        
        config_args = self.get_config_args()
        skip_args = self.get_skip_args()
        
        # JSON report
        self.log("Running comprehensive vulnerability scan...")
        cmd = [
            "trivy",
            self.scan_type,
            *config_args,
            "--format", "json",
            "-o", str(json_output),
            "--severity", "HIGH,CRITICAL,MEDIUM,LOW",
            "--scanners", "vuln,secret,config",
            *skip_args,
            str(self.target_path)
        ]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode != 0:
            self.log(f"JSON report generation failed with exit code {result.returncode}", "ERROR")
        
        # Text report
        self.log("Generating detailed text report...")
        cmd = [
            "trivy",
            self.scan_type,
            *config_args,
            "--format", "table",
            "-o", str(text_output),
            "--severity", "HIGH,CRITICAL,MEDIUM,LOW",
            "--scanners", "vuln,secret,config",
            *skip_args,
            str(self.target_path)
        ]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode != 0:
            self.log(f"Text report generation failed with exit code {result.returncode}", "ERROR")
        
        # Additional secrets/config scan
        self.log("Running additional secrets and misconfiguration scan...")
        cmd = [
            "trivy",
            self.scan_type,
            "--scanners", "secret,config",
            "--format", "json",
            "-o", str(secrets_output),
            *skip_args,
            str(self.target_path)
        ]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode != 0:
            self.log(f"Secrets/config scan failed with exit code {result.returncode}", "WARNING")
        
        # Check if reports were generated
        if json_output.exists() or text_output.exists():
            self.log("Trivy scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("Trivy scan completed but no results generated", "ERROR")
            return False


if __name__ == "__main__":
    import sys
    
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/app/results")
    log_file = os.getenv("LOG_FILE", "app/results/logs/scan.log")
    config_path = os.getenv("TRIVY_CONFIG_PATH", "/app/scanner/scanners/trivy/config/config.yaml")
    scan_type = os.getenv("TRIVY_SCAN_TYPE", "fs")
    exclude_paths = os.getenv("SIMPLESECCHECK_EXCLUDE_PATHS", "")
    
    scanner = TrivyScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path,
        scan_type=scan_type,
        exclude_paths=exclude_paths
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
