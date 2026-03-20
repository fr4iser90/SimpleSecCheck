"""
Burp Suite Scanner
Python implementation of run_burp.sh
"""
import os
import json
import shlex
from pathlib import Path
from typing import Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability


class BurpScanner(BaseScanner):
    """Burp Suite scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.WEBSITE,
            supported_targets=[TargetType.WEBSITE],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 5
    REQUIRES_CONDITION = None
    ENV_VARS = {}
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None,
        scan_target: Optional[str] = None
    ):
        """
        Initialize Burp Suite scanner

        Args:
            target_path: Path to scan (not used for website scans)
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to Burp Suite config file
            scan_target: Target URL to scan (web application)
        """
        super().__init__("Burp Suite", target_path, results_dir, log_file, config_path)
        self.scan_target = scan_target or os.getenv("SCAN_TARGET", "http://host.docker.internal:8000")
        self.burp_jar = Path("/opt/burp/burp-suite.jar")
    
    def scan(self) -> bool:
        """Run Burp Suite scan"""
        if not self.burp_jar.exists():
            self.log("Burp Suite not found at /opt/burp/burp-suite.jar", "ERROR")
            return False
        
        if not self.check_tool_installed("java"):
            self.log("java not found in PATH", "ERROR")
            return False
        
        self.log(f"Running web application security scan on {self.scan_target}...")
        
        json_output = self.results_dir / "report.json"  # Changed from burp.json
        text_output = self.results_dir / "report.txt"   # Changed from burp.txt
        
        config_args = []
        if self.config_path and self.config_path.exists():
            config_args = ["-c", str(self.config_path)]
        
        # JSON report
        self.log("Running web application security scan...")
        cmd = ["java", "-jar", str(self.burp_jar), *config_args, "-u", self.scan_target, "-o", str(json_output)]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode != 0:
            self.log("JSON report generation failed", "WARNING")
        
        # Text report
        cmd = ["java", "-jar", str(self.burp_jar), *config_args, *burp_extra, "-u", self.scan_target, "-o", str(text_output)]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode != 0:
            self.log("Text report generation failed", "WARNING")
        
        if not json_output.exists() and not text_output.exists():
            self.log("Burp Suite produced no report (manual configuration may be required); no fake report written.", "WARNING")
        
        if json_output.exists() or text_output.exists():
            self.log("Burp Suite scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("No Burp Suite report was generated!", "ERROR")
            return False


if __name__ == "__main__":
    import sys
    
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/app/results")
    log_file = os.getenv("LOG_FILE", "app/results/logs/scan.log")
    config_path = os.getenv("BURP_CONFIG_PATH", "/app/scanner/plugins/burp/config/config.yaml")
    scan_target = os.getenv("SCAN_TARGET", "http://host.docker.internal:8000")
    
    scanner = BurpScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path,
        scan_target=scan_target
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
