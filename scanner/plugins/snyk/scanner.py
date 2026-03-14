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


class SnykScanner(BaseScanner):
    """Snyk scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.DEPENDENCY,
            supported_targets=[TargetType.LOCAL_MOUNT, TargetType.GIT_REPO, TargetType.UPLOADED_CODE],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 6
    REQUIRES_CONDITION = None
    ENV_VARS = {
        "SNYK_CONFIG_PATH": "/app/scanner/scanners/snyk/config/config.yaml"
    }
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None
    ):
        """
        Initialize Snyk scanner
        
        Args:
            target_path: Path to scan
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to Snyk config file (optional)
        """
        super().__init__("Snyk", target_path, results_dir, log_file, config_path)
        self.snyk_token = os.getenv("SNYK_TOKEN", "")
    
    def create_empty_reports(self, reason: str = "No SNYK_TOKEN provided"):
        """Create empty reports when Snyk is skipped"""
        json_output = self.results_dir / "snyk.json"
        text_output = self.results_dir / "snyk.txt"
        
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
        """Run Snyk scan"""
        if not self.check_tool_installed("snyk"):
            self.log("snyk not found in PATH", "ERROR")
            return False
        
        if not self.snyk_token:
            self.log("No SNYK_TOKEN provided, skipping Snyk scan...", "WARNING")
            self.log("Snyk requires authentication. Set SNYK_TOKEN environment variable to use Snyk.")
            self.create_empty_reports("No SNYK_TOKEN provided")
            return True
        
        self.log("Using provided SNYK_TOKEN for authentication...")
        self.log(f"Running Snyk vulnerability scan on {self.target_path}...")
        
        json_output = self.results_dir / "snyk.json"
        text_output = self.results_dir / "snyk.txt"
        
        # Change to target directory
        try:
            os.chdir(self.target_path)
        except Exception as e:
            self.log(f"Cannot access target directory: {e}", "ERROR")
            return False
        
        # JSON report
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
            else:
                self.log("Alternative JSON scan also failed, creating minimal report...", "WARNING")
                empty_json = {
                    "vulnerabilities": [],
                    "summary": {"total_packages": 0, "vulnerable_packages": 0, "total_vulnerabilities": 0},
                    "error": "Snyk scan failed"
                }
                with open(json_output, "w", encoding="utf-8") as f:
                    json.dump(empty_json, f, indent=2)
        
        # Text report
        self.log("Running Snyk test with text output...")
        cmd = ["snyk", "test", f"--token={self.snyk_token}"]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode == 0 and result.stdout:
            with open(text_output, "w", encoding="utf-8") as f:
                f.write(result.stdout)
        else:
            self.log("Text report generation failed, creating minimal report...", "WARNING")
            with open(text_output, "w", encoding="utf-8") as f:
                f.write("Snyk Scan Results\n")
                f.write("=================\n")
                f.write("Snyk scan failed or no vulnerabilities found.\n")
                f.write(f"Scan completed at: {datetime.now().isoformat()}\n")
        
        # Verbose scan
        self.log("Running additional verbose scan...")
        cmd = ["snyk", "test", f"--token={self.snyk_token}", "--verbose"]
        result = self.run_command(cmd, capture_output=True)
        if result.returncode == 0 and result.stdout:
            with open(text_output, "a", encoding="utf-8") as f:
                f.write("\n\nVerbose Output:\n")
                f.write("===============\n")
                f.write(result.stdout)
        
        # Snyk monitor (non-critical)
        self.log("Running Snyk monitor for cloud integration...")
        cmd = ["snyk", "monitor", f"--token={self.snyk_token}"]
        result = self.run_command(cmd, capture_output=True)
        if result.returncode != 0:
            self.log("Snyk monitor failed.", "WARNING")
        
        if json_output.exists() or text_output.exists():
            self.log("Snyk scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("No Snyk report was generated!", "ERROR")
            return False


if __name__ == "__main__":
    import sys
    
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/app/results")
    log_file = os.getenv("LOG_FILE", "app/results/logs/scan.log")
    config_path = os.getenv("SNYK_CONFIG_PATH", "/app/scanner/scanners/snyk/config/config.yaml")
    
    scanner = SnykScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
