"""
Bandit Scanner
Python implementation of run_bandit.sh
"""
import os
import json
import shlex
from pathlib import Path
from typing import Optional
from datetime import datetime
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability


class BanditScanner(BaseScanner):
    """Bandit scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.CODE,
            supported_targets=[TargetType.LOCAL_MOUNT, TargetType.GIT_REPO, TargetType.UPLOADED_CODE],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 24
    REQUIRES_CONDITION = None
    ENV_VARS = {
        "BANDIT_CONFIG_PATH": "/app/scanner/plugins/bandit/config/config.yaml"
    }
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None
    ):
        """
        Initialize Bandit scanner
        
        Args:
            target_path: Path to scan
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to Bandit config file (optional)
        """
        super().__init__("Bandit", target_path, results_dir, log_file, config_path)
    
    def find_python_files(self) -> int:
        """Count Python files"""
        return len(list(self.target_path.rglob("*.py")))

    def create_empty_reports(self):
        """Create empty reports when no Python files found"""
        json_output = self.results_dir / "report.json"  # Changed from bandit.json
        text_output = self.results_dir / "report.txt"   # Changed from bandit.txt

        empty_json = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "metrics": {
                "_totals": {
                    "loc": 0,
                    "nosec": 0,
                    "skipped_tests": 0,
                    "tests": 0
                }
            },
            "results": []
        }

        with open(json_output, "w", encoding="utf-8") as f:
            json.dump(empty_json, f, indent=2)

        with open(text_output, "w", encoding="utf-8") as f:
            f.write("Bandit Scan Results\n")
            f.write("===================\n")
            f.write("No Python files found.\n")
            f.write(f"Scan completed at: {datetime.now().isoformat()}\n")

    def scan(self) -> bool:
        """Run Bandit scan"""
        if not self.check_tool_installed("bandit"):
            self.log("Bandit CLI not found. Skipping Bandit scan.", "WARNING")
            return True

        python_files = self.find_python_files()

        if python_files == 0:
            self.log("No Python files found", "WARNING")
            self.create_empty_reports()
            return True

        self.log(f"Found {python_files} Python file(s) to scan...")
        self.log(f"Running Python security scan on {self.target_path}...")

        json_output = self.results_dir / "report.json"  # Changed from bandit.json
        text_output = self.results_dir / "report.txt"   # Changed from bandit.txt

        extra = shlex.split(os.getenv("BANDIT_EXTRA_ARGS", "").strip())

        # JSON report
        cmd = ["bandit", "-r", str(self.target_path), *extra, "-f", "json", "-o", str(json_output)]

        result = self.run_command(cmd, capture_output=True)
        if result.returncode != 0:
            self.log("JSON report generation encountered issues", "WARNING")

        # Text report
        cmd = ["bandit", "-r", str(self.target_path), *extra]

        result = self.run_command(cmd, capture_output=True)
        if result.returncode == 0 and result.stdout:
            with open(text_output, "w", encoding="utf-8") as f:
                f.write(result.stdout)
        else:
            self.log("Text report generation encountered issues", "WARNING")

        # Check if JSON file was created and contains results
        if json_output.exists():
            try:
                with open(json_output, 'r', encoding='utf-8') as f:
                    bandit_data = json.load(f)

                # If JSON file exists but has no results, create empty results array
                if 'results' not in bandit_data:
                    bandit_data['results'] = []
                    with open(json_output, 'w', encoding='utf-8') as f:
                        json.dump(bandit_data, f, indent=2)
            except Exception:
                pass

        if json_output.exists() or text_output.exists():
            self.log("Bandit scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("No Bandit results generated", "WARNING")
            return True


if __name__ == "__main__":
    import sys
    
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/app/results")
    log_file = os.getenv("LOG_FILE", "app/results/logs/scan.log")
    config_path = os.getenv("BANDIT_CONFIG_PATH", "/app/scanner/plugins/bandit/config/config.yaml")
    
    scanner = BanditScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
