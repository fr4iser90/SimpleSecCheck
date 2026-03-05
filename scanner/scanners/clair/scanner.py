"""
Clair Scanner
Python implementation of run_clair.sh
"""
import os
import json
from pathlib import Path
from typing import Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability


class ClairScanner(BaseScanner):
    """Clair scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.IMAGE,
            supported_targets=[TargetType.DOCKER_IMAGE],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 30
    ENV_VARS = {}
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None,
        clair_image: Optional[str] = None,
        scan_type: Optional[str] = None,
        scan_target: Optional[str] = None
    ):
        """
        Initialize Clair scanner
        
        Args:
            target_path: Path to scan (not used for container scans)
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to Clair config file (optional)
            clair_image: Container image to scan
        """
        default_config = "/SimpleSecCheck/scanner/scanners/clair/config/config.yaml"
        resolved_config = config_path or os.getenv("CLAIR_CONFIG_PATH", default_config)
        super().__init__("Clair", target_path, results_dir, log_file, resolved_config)
        self.target_type = (os.getenv("TARGET_TYPE", "")).lower()
        self.scan_target = scan_target or os.getenv("SCAN_TARGET", "")
        self.clair_image = clair_image or self.scan_target
    
    def scan(self) -> bool:
        """Run Clair scan"""
        if self.target_type and self.target_type != TargetType.DOCKER_IMAGE.value:
            self.log("TARGET_TYPE is not docker_image, skipping Clair scan.", "INFO")
            return True

        if not self.clair_image:
            self.log("No container image specified (SCAN_TARGET empty), skipping Clair scan.", "WARNING")
            return True

        if not self.check_tool_installed("clair"):
            self.log("clair not found in PATH", "ERROR")
            return False
        
        self.log(f"Running container image vulnerability scan on {self.clair_image}...")
        
        json_output = self.results_dir / "clair.json"
        text_output = self.results_dir / "clair.txt"
        
        # Note: Clair requires external PostgreSQL setup
        self.log("Clair requires external PostgreSQL setup.", "WARNING")
        self.log("Please ensure Clair server is running separately.", "WARNING")
        
        # Create placeholder output since Clair requires complex setup
        placeholder = {
            "vulnerabilities": [],
            "note": "Clair requires PostgreSQL database setup. Please use Trivy for container scanning."
        }
        
        with open(json_output, "w", encoding="utf-8") as f:
            json.dump(placeholder, f, indent=2)
        
        text_output.write_text("Clair requires PostgreSQL database setup. Please use Trivy for container scanning.\n")
        
        self.log("Placeholder report generated (Clair requires PostgreSQL setup)", "WARNING")
        return True


if __name__ == "__main__":
    import sys
    
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/SimpleSecCheck/results")
    log_file = os.getenv("LOG_FILE", "SimpleSecCheck/results/logs/scan.log")
    config_path = os.getenv("CLAIR_CONFIG_PATH", "/SimpleSecCheck/scanner/scanners/clair/config/config.yaml")
    clair_image = os.getenv("SCAN_TARGET", "")
    scanner = ClairScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path,
        clair_image=clair_image,
        scan_target=clair_image
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
