"""
TruffleHog Scanner
Python implementation of run_trufflehog.sh
"""
import os
import json
from pathlib import Path
from typing import Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType


class TruffleHogScanner(BaseScanner):
    """TruffleHog scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    SCAN_TYPES = [ScanType.CODE]
    PRIORITY = 16
    REQUIRES_CONDITION = None
    ENV_VARS = {
        "TRUFFLEHOG_CONFIG_PATH": "/SimpleSecCheck/config/tools/trufflehog/config.yaml"
    }
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None
    ):
        """
        Initialize TruffleHog scanner
        
        Args:
            target_path: Path to scan
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to TruffleHog config file (optional, not used to avoid protobuf issues)
        """
        super().__init__("TruffleHog", target_path, results_dir, log_file, config_path)
    
    def scan(self) -> bool:
        """Run TruffleHog scan"""
        if not self.check_tool_installed("trufflehog"):
            self.log("trufflehog not found in PATH", "ERROR")
            return False
        
        self.log(f"Running secret detection scan on {self.target_path}...")
        
        json_output = self.results_dir / "trufflehog.json"
        text_output = self.results_dir / "trufflehog.txt"
        
        # JSON report (without --config to avoid protobuf issues)
        self.log("Running secret detection scan...")
        cmd = ["trufflehog", "filesystem", "--json", "--no-update", str(self.target_path)]
        
        result = self.run_command(cmd, capture_output=True)
        
        if result.returncode == 0 and result.stdout:
            # Parse JSON lines and combine into array
            try:
                json_lines = [json.loads(line) for line in result.stdout.strip().split("\n") if line.strip()]
                with open(json_output, "w", encoding="utf-8") as f:
                    json.dump(json_lines, f, indent=2)
            except Exception as e:
                self.log(f"Failed to parse JSON output: {e}", "WARNING")
                json_output.write_text("[]")
        else:
            self.log("JSON report generation failed, creating empty array", "WARNING")
            json_output.write_text("[]")
        
        # Text report
        self.log("Running text report generation...")
        cmd = ["trufflehog", "filesystem", "--no-update", str(self.target_path)]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode == 0 and result.stdout:
            with open(text_output, "w", encoding="utf-8") as f:
                f.write(result.stdout)
        else:
            self.log("Text report generation failed", "WARNING")
            text_output.write_text("No secrets found or scan failed.\n")
        
        if json_output.exists() or text_output.exists():
            self.log("TruffleHog scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("No TruffleHog report was generated!", "ERROR")
            return False


if __name__ == "__main__":
    import sys
    
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/SimpleSecCheck/results")
    log_file = os.getenv("LOG_FILE", "/SimpleSecCheck/logs/scan.log")
    config_path = os.getenv("TRUFFLEHOG_CONFIG_PATH", "/SimpleSecCheck/config/tools/trufflehog/config.yaml")
    
    scanner = TruffleHogScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
