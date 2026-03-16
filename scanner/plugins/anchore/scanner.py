"""
Anchore Scanner
Python implementation of run_anchore.sh
"""
import os
from pathlib import Path
from typing import Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability


class AnchoreScanner(BaseScanner):
    """Anchore scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.IMAGE,
            supported_targets=[TargetType.CONTAINER_REGISTRY],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 31
    ENV_VARS = {}
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None,
        anchore_image: Optional[str] = None,
        scan_type: Optional[str] = None,
        scan_target: Optional[str] = None
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
        default_config = "/app/scanner/plugins/anchore/config/config.yaml"
        resolved_config = config_path or os.getenv("ANCHORE_CONFIG_PATH", default_config)
        super().__init__("Anchore", target_path, results_dir, log_file, resolved_config)
        self.target_type = (os.getenv("TARGET_TYPE", "")).lower()
        self.scan_target = scan_target or os.getenv("SCAN_TARGET", "")
        self.anchore_image = anchore_image or self.scan_target
    
    def scan(self) -> bool:
        """Run Anchore scan"""
        if self.target_type and self.target_type != TargetType.CONTAINER_REGISTRY.value:
            self.log("TARGET_TYPE is not container_registry, skipping Anchore scan.", "INFO")
            return True

        if not self.anchore_image:
            self.log("No container image specified (SCAN_TARGET empty), skipping Anchore scan.", "WARNING")
            return True

        if not self.check_tool_installed("grype"):
            self.log("grype not found in PATH", "ERROR")
            return False
        
        self.log(f"Running container image vulnerability scan on {self.anchore_image}...")
        
        json_output = self.results_dir / "report.json"  # Changed from anchore.json
        text_output = self.results_dir / "report.txt"   # Changed from anchore.txt
        
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
    results_dir = os.getenv("RESULTS_DIR", "/app/results")
    log_file = os.getenv("LOG_FILE", "app/results/logs/scan.log")
    config_path = os.getenv("ANCHORE_CONFIG_PATH", "/app/scanner/plugins/anchore/config/config.yaml")
    anchore_image = os.getenv("SCAN_TARGET", "")
    scanner = AnchoreScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path,
        anchore_image=anchore_image,
        scan_target=anchore_image
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
