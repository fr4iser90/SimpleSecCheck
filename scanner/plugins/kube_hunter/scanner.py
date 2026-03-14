"""
Kube-hunter Scanner
Python implementation of run_kube_hunter.sh
"""
import os
from pathlib import Path
from typing import Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability


class KubeHunterScanner(BaseScanner):
    """Kube-hunter scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.NETWORK,
            supported_targets=[TargetType.NETWORK_HOST],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 1
    REQUIRES_CONDITION = None
    ENV_VARS = {
        "KUBE_HUNTER_CONFIG_PATH": "/app/scanner/scanners/kube_hunter/config/config.yaml"
    }
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None
    ):
        """
        Initialize Kube-hunter scanner
        
        Args:
            target_path: Path to scan (not used for network scans)
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to Kube-hunter config file (optional)
        """
        super().__init__("Kube-hunter", target_path, results_dir, log_file, config_path)
    
    def scan(self) -> bool:
        """Run Kube-hunter scan"""
        if not self.check_tool_installed("kube-hunter"):
            self.log("kube-hunter not found in PATH", "ERROR")
            return False
        
        self.log("Running Kubernetes cluster security scan...")
        
        json_output = self.results_dir / "kube-hunter.json"
        text_output = self.results_dir / "kube-hunter.txt"
        
        # JSON report (with timeout to avoid hanging)
        self.log("Running cluster security scan...")
        cmd = ["kube-hunter", "--remote", "localhost", "--report", "json"]
        
        result = self.run_command(cmd, capture_output=True, timeout=10)
        if result.returncode == 0 and result.stdout:
            with open(json_output, "w", encoding="utf-8") as f:
                f.write(result.stdout)
        else:
            self.log("JSON report generation failed or timed out", "WARNING")
        
        # Text report (with timeout)
        self.log("Running text report generation...")
        cmd = ["kube-hunter", "--remote", "localhost", "--report", "plain"]
        
        result = self.run_command(cmd, capture_output=True, timeout=10)
        if result.returncode == 0 and result.stdout:
            with open(text_output, "w", encoding="utf-8") as f:
                f.write(result.stdout)
        else:
            self.log("Text report generation failed or timed out", "WARNING")
        
        if json_output.exists() or text_output.exists():
            self.log("Kube-hunter scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("No Kube-hunter report was generated!", "ERROR")
            return False


if __name__ == "__main__":
    import sys
    
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/app/results")
    log_file = os.getenv("LOG_FILE", "app/results/logs/scan.log")
    config_path = os.getenv("KUBE_HUNTER_CONFIG_PATH", "/app/scanner/scanners/kube_hunter/config/config.yaml")
    
    scanner = KubeHunterScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
