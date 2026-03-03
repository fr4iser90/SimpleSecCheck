"""
Anchore Scanner
Python implementation of run_anchore.sh
"""
import os
from pathlib import Path
from typing import Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType


class AnchoreScanner(BaseScanner):
    """Anchore scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    SCAN_TYPES = [ScanType.CODE]
    PRIORITY = 31
    REQUIRES_CONDITION = "ANCHORE_IMAGE"
    ENV_VARS = {
        "ANCHORE_CONFIG_PATH": "/SimpleSecCheck/config/tools/anchore/config.yaml"
    }
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None,
        anchore_image: Optional[str] = None
    ):
        """
        Initialize Anchore scanner
        
        Args:
            target_path: Path to scan (not used for container scans)
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to Anchore config file
            anchore_image: Container image to scan
        """
        super().__init__("Anchore", target_path, results_dir, log_file, config_path)
        self.anchore_image = anchore_image or os.getenv("ANCHORE_IMAGE", "")
    
    def scan(self) -> bool:
        """Run Anchore scan"""
        if not self.check_tool_installed("grype"):
            self.log("grype not found in PATH", "ERROR")
            return False
        
        if not self.anchore_image:
            self.log("No container image specified, skipping Anchore scan.", "WARNING")
            return True
        
        self.log(f"Running container image vulnerability scan on {self.anchore_image}...")
        
        json_output = self.results_dir / "anchore.json"
        text_output = self.results_dir / "anchore.txt"
        
        config_args = []
        if self.config_path and self.config_path.exists():
            config_args = ["--config", str(self.config_path)]
        
        # JSON report
        self.log("Running container image vulnerability scan...")
        cmd = ["grype", *config_args, "--output", "json", self.anchore_image]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode == 0 and result.stdout:
            with open(json_output, "w", encoding="utf-8") as f:
                f.write(result.stdout)
        else:
            self.log("Scan failed, continuing...", "WARNING")
        
        # Text report
        cmd = ["grype", *config_args, self.anchore_image]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode == 0 and result.stdout:
            with open(text_output, "w", encoding="utf-8") as f:
                f.write(result.stdout)
        else:
            self.log("Text output generation failed, continuing...", "WARNING")
        
        if json_output.exists():
            self.log("Anchore scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("No Anchore report was generated!", "ERROR")
            return False


if __name__ == "__main__":
    import sys
    
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/SimpleSecCheck/results")
    log_file = os.getenv("LOG_FILE", "/SimpleSecCheck/logs/scan.log")
    config_path = os.getenv("ANCHORE_CONFIG_PATH", "/SimpleSecCheck/config/tools/anchore/config.yaml")
    anchore_image = os.getenv("ANCHORE_IMAGE", "")
    
    scanner = AnchoreScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path,
        anchore_image=anchore_image
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
