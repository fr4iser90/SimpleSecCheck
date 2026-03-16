"""
Kube-bench Scanner
Python implementation of run_kube_bench.sh
"""
import os
from pathlib import Path
from typing import Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability


class KubeBenchScanner(BaseScanner):
    """Kube-bench scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.NETWORK,
            supported_targets=[TargetType.NETWORK_HOST],
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
        config_path: Optional[str] = None
    ):
        """
        Initialize Kube-bench scanner
        
        Args:
            target_path: Path to scan (not used for network scans)
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to Kube-bench config file (optional)
        """
        super().__init__("Kube-bench", target_path, results_dir, log_file, config_path)
    
    def scan(self) -> bool:
        """Run Kube-bench scan"""
        if not self.check_tool_installed("kube-bench"):
            self.log("kube-bench not found in PATH", "ERROR")
            return False
        
        self.log("Running Kubernetes compliance scan...")
        
        json_output = self.results_dir / "report.json"  # Changed from kube-bench.json
        text_output = self.results_dir / "report.txt"   # Changed from kube-bench.txt
        
        # JSON report
        self.log("Running compliance scan...")
        cmd = ["kube-bench", "--json"]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode == 0 and result.stdout:
            with open(json_output, "w", encoding="utf-8") as f:
                f.write(result.stdout)
        else:
            self.log("JSON report generation failed", "WARNING")
        
        # Text report
        self.log("Running text report generation...")
        cmd = ["kube-bench", "--version", "1.28"]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode == 0 and result.stdout:
            with open(text_output, "w", encoding="utf-8") as f:
                f.write(result.stdout)
        else:
            self.log("Text report generation failed", "WARNING")
        
        if json_output.exists() or text_output.exists():
            self.log("Kube-bench scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("No Kube-bench report was generated!", "ERROR")
            return False


if __name__ == "__main__":
    import sys
    
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/app/results")
    log_file = os.getenv("LOG_FILE", "app/results/logs/scan.log")
    config_path = os.getenv("KUBE_BENCH_CONFIG_PATH", "/app/scanner/plugins/kube_bench/config/config.yaml")
    
    scanner = KubeBenchScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
