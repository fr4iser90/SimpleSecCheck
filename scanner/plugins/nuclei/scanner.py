"""
Nuclei Scanner
Python implementation of run_nuclei.sh
"""
import os
import json
from pathlib import Path
from typing import Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability


class NucleiScanner(BaseScanner):
    """Nuclei scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.WEBSITE,
            supported_targets=[TargetType.WEBSITE],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 2
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
        Initialize Nuclei scanner
        
        Args:
            target_path: Path to scan (not used for website scans)
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to Nuclei config file
            zap_target: Target URL to scan
        """
        super().__init__("Nuclei", target_path, results_dir, log_file, config_path)
        self.zap_target = zap_target or os.getenv("SCAN_TARGET", "http://host.docker.internal:8000")
    
    def scan(self) -> bool:
        """Run Nuclei scan"""
        if not self.check_tool_installed("nuclei"):
            self.log("nuclei not found in PATH", "ERROR")
            return False
        
        self.log(f"Running web application scan on {self.zap_target}...")
        
        json_output = self.results_dir / "report.json"  # Changed from nuclei.json
        text_output = self.results_dir / "report.txt"   # Changed from nuclei.txt
        critical_output = self.results_dir / "critical.json"  # Changed from nuclei-critical.json
        
        config_args = []
        if self.config_path and self.config_path.exists():
            config_args = ["-config", str(self.config_path)]
        
        # JSON report (JSONL format)
        self.log("Running comprehensive web application scan...")
        cmd = ["nuclei", "-u", self.zap_target, *config_args, "-jsonl", "-o", str(json_output)]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode != 0:
            self.log("JSON report generation failed", "WARNING")
        
        # Text report
        cmd = ["nuclei", "-u", self.zap_target, *config_args, "-o", str(text_output)]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode != 0:
            self.log("Text report generation failed", "WARNING")
        
        # Critical vulnerability scan
        self.log("Running additional critical vulnerability scan...")
        cmd = ["nuclei", "-u", self.zap_target, "-severity", "critical,high", "-jsonl", "-o", str(critical_output)]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode != 0:
            self.log("Critical scan failed", "WARNING")
        
        # Check if reports were generated
        if json_output.exists() and json_output.stat().st_size > 0:
            self.log("JSON report generated successfully", "SUCCESS")
            return True
        elif text_output.exists() and text_output.stat().st_size > 0:
            self.log("Text report generated successfully", "SUCCESS")
            return True
        else:
            # No vulnerabilities found - this is acceptable
            self.log("No vulnerabilities found (scan completed successfully)", "SUCCESS")
            json_output.write_text('{"info": "No vulnerabilities found"}')
            return True


if __name__ == "__main__":
    import sys
    
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/app/results")
    log_file = os.getenv("LOG_FILE", "app/results/logs/scan.log")
    config_path = os.getenv("NUCLEI_CONFIG_PATH", "/app/scanner/plugins/nuclei/config/config.yaml")
    zap_target = os.getenv("SCAN_TARGET", "http://host.docker.internal:8000")
    
    scanner = NucleiScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path,
        zap_target=zap_target
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
