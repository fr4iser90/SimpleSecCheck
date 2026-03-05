"""
Wapiti Scanner
Python implementation of run_wapiti.sh
"""
import os
from pathlib import Path
from typing import Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability


class WapitiScanner(BaseScanner):
    """Wapiti scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.WEBSITE,
            supported_targets=[TargetType.WEBSITE],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 3
    REQUIRES_CONDITION = None
    ENV_VARS = {}
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None,
        zap_target: Optional[str] = None
    ):
        """
        Initialize Wapiti scanner
        
        Args:
            target_path: Path to scan (not used for website scans)
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to Wapiti config file (optional)
            zap_target: Target URL to scan
        """
        super().__init__("Wapiti", target_path, results_dir, log_file, config_path)
        self.zap_target = zap_target or os.getenv("SCAN_TARGET", "http://host.docker.internal:8000")
    
    def scan(self) -> bool:
        """Run Wapiti scan"""
        if not self.check_tool_installed("wapiti"):
            self.log("wapiti not found in PATH", "ERROR")
            return False
        
        self.log(f"Running web vulnerability scan on {self.zap_target}...")
        
        json_output = self.results_dir / "wapiti.json"
        text_output = self.results_dir / "wapiti.txt"
        
        # JSON report
        self.log("Running web vulnerability scan...")
        cmd = ["wapiti", "-u", self.zap_target, "-f", "json", "-o", str(json_output)]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode != 0:
            self.log("JSON report generation failed", "WARNING")
        
        # Text report
        cmd = ["wapiti", "-u", self.zap_target, "-o", str(text_output)]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode != 0:
            self.log("Text report generation failed", "WARNING")
        
        if json_output.exists() or text_output.exists():
            self.log("Wapiti scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("No Wapiti report was generated!", "ERROR")
            return False


if __name__ == "__main__":
    import sys
    
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/SimpleSecCheck/results")
    log_file = os.getenv("LOG_FILE", "SimpleSecCheck/results/logs/scan.log")
    config_path = os.getenv("WAPITI_CONFIG_PATH", "/SimpleSecCheck/scanner/scanners/wapiti/config/config.yaml")
    zap_target = os.getenv("SCAN_TARGET", "http://host.docker.internal:8000")
    
    scanner = WapitiScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path,
        zap_target=zap_target
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
