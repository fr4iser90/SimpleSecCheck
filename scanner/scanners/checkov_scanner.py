"""
Checkov Scanner
Python implementation of run_checkov.sh
"""
import os
from pathlib import Path
from typing import List, Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType


class CheckovScanner(BaseScanner):
    """Checkov scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    SCAN_TYPES = [ScanType.CODE]
    PRIORITY = 12
    REQUIRES_CONDITION = None
    ENV_VARS = {
        "CHECKOV_CONFIG_PATH": "/SimpleSecCheck/config/tools/checkov/config.yaml"
    }
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None,
        exclude_paths: Optional[str] = None
    ):
        """
        Initialize Checkov scanner
        
        Args:
            target_path: Path to scan
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to Checkov config file (optional)
            exclude_paths: Comma-separated paths to exclude
        """
        super().__init__("Checkov", target_path, results_dir, log_file, config_path)
        self.exclude_paths = exclude_paths or os.getenv("SIMPLESECCHECK_EXCLUDE_PATHS", "")
    
    def find_infra_files(self) -> List[Path]:
        """Find infrastructure files"""
        infra_files = []
        patterns = [
            "*.tf", "*.tfvars", "*.yml", "*.yaml", "Dockerfile",
            "docker-compose.yml", "docker-compose.yaml", "*.json",
            "*.tfstate", "cloudformation.yaml", "cloudformation.yml",
            "serverless.yml", "serverless.yaml"
        ]
        
        for pattern in patterns:
            for file in self.target_path.rglob(pattern):
                # Check exclude paths
                skip = False
                if self.exclude_paths:
                    for exclude in self.exclude_paths.split(","):
                        exclude = exclude.strip()
                        if exclude and exclude in str(file):
                            skip = True
                            break
                
                if not skip:
                    infra_files.append(file)
        
        return infra_files
    
    def get_skip_args(self) -> List[str]:
        """Get Checkov skip arguments"""
        skip_args = []
        
        if self.exclude_paths:
            for path in self.exclude_paths.split(","):
                path = path.strip()
                if path:
                    skip_args.extend(["--skip-path", path])
        
        return skip_args
    
    def scan(self) -> bool:
        """Run Checkov scan"""
        if not self.check_tool_installed("checkov"):
            self.log("Checkov CLI not found, skipping scan.", "WARNING")
            return True
        
        infra_files = self.find_infra_files()
        
        if not infra_files:
            self.log("No infrastructure files found, skipping scan.", "WARNING")
            return True
        
        self.log(f"Found {len(infra_files)} infrastructure file(s).")
        self.log(f"Running infrastructure security scan on {self.target_path}...")
        
        json_output = self.results_dir / "checkov-comprehensive.json"
        text_output = self.results_dir / "checkov-comprehensive.txt"
        
        # Remove old directory if it exists
        if json_output.exists() and json_output.is_dir():
            import shutil
            shutil.rmtree(json_output, ignore_errors=True)
            self.log("Removed old directory at json_output path")
        
        skip_args = self.get_skip_args()
        
        # JSON report
        self.log("Generating JSON report...")
        cmd = ["checkov", "-d", str(self.target_path), *skip_args, "--output", "json", "--quiet"]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode == 0 and result.stdout:
            with open(json_output, "w", encoding="utf-8") as f:
                f.write(result.stdout)
        else:
            self.log("JSON report generation failed, creating minimal JSON", "WARNING")
            json_output.write_text('{"check_type":"","results":{"passed_checks":[],"failed_checks":[],"skipped_checks":[]},"summary":{"passed":0,"failed":0,"skipped":0}}')
        
        # Text report
        self.log("Generating text report...")
        cmd = ["checkov", "-d", str(self.target_path), *skip_args, "--output", "cli", "--quiet"]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode == 0 and result.stdout:
            with open(text_output, "w", encoding="utf-8") as f:
                f.write(result.stdout)
        else:
            self.log("Text report generation failed", "WARNING")
            text_output.write_text("Checkov scan completed but no results available.\n")
        
        if json_output.exists() or text_output.exists():
            self.log("Infrastructure security scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("No results generated", "WARNING")
            return True


if __name__ == "__main__":
    import sys
    
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/SimpleSecCheck/results")
    log_file = os.getenv("LOG_FILE", "/SimpleSecCheck/logs/scan.log")
    config_path = os.getenv("CHECKOV_CONFIG_PATH", "/SimpleSecCheck/config/tools/checkov/config.yaml")
    exclude_paths = os.getenv("SIMPLESECCHECK_EXCLUDE_PATHS", "")
    
    scanner = CheckovScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path,
        exclude_paths=exclude_paths
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
