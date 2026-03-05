"""
Semgrep Scanner
Python implementation of run_semgrep.sh
"""
import os
import subprocess
from pathlib import Path
from typing import List, Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability


class SemgrepScanner(BaseScanner):
    """Semgrep scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.CODE,
            supported_targets=[TargetType.LOCAL_CODE, TargetType.GIT_REPO],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 1
    REQUIRES_CONDITION = None
    ENV_VARS = {
        "SEMGREP_RULES_PATH": "/SimpleSecCheck/scanner/scanners/semgrep/rules"
    }
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        rules_path: Optional[str] = None,
        exclude_paths: Optional[str] = None
    ):
        """
        Initialize Semgrep scanner
        
        Args:
            target_path: Path to scan
            results_dir: Results directory
            log_file: Log file path
            rules_path: Path to Semgrep rules (directory or file)
            exclude_paths: Comma-separated paths to exclude
        """
        super().__init__("Semgrep", target_path, results_dir, log_file)
        self.rules_path = Path(rules_path) if rules_path else Path("/SimpleSecCheck/scanner/scanners/semgrep/rules")
        self.exclude_paths = exclude_paths or os.getenv("SIMPLESECCHECK_EXCLUDE_PATHS", "")
    
    def get_exclude_args(self) -> List[str]:
        """Get Semgrep exclude arguments"""
        if not self.exclude_paths:
            return []
        
        exclude_args = []
        for path in self.exclude_paths.split(","):
            path = path.strip()
            if path:
                exclude_args.extend(["--exclude", path])
        
        return exclude_args
    
    def get_config_args(self) -> List[str]:
        """Get Semgrep config arguments"""
        config_args = []
        
        if self.rules_path.exists():
            if self.rules_path.is_dir():
                # Directory: add all YAML files
                self.log(f"Found rules directory, adding all YAML files...")
                for rule_file in self.rules_path.rglob("*.yml"):
                    config_args.extend(["--config", str(rule_file)])
                    self.log(f"Adding rule file: {rule_file}")
                for rule_file in self.rules_path.rglob("*.yaml"):
                    config_args.extend(["--config", str(rule_file)])
                    self.log(f"Adding rule file: {rule_file}")
            elif self.rules_path.is_file():
                # Single file
                config_args.extend(["--config", str(self.rules_path)])
        else:
            self.log(f"Rules path not found: {self.rules_path}, using auto rules only", "WARNING")
        
        # Always add auto rules
        config_args.append("--config")
        config_args.append("auto")
        
        return config_args
    
    def scan(self) -> bool:
        """Run Semgrep scan"""
        if not self.check_tool_installed("semgrep"):
            self.log("semgrep not found in PATH", "ERROR")
            return False
        
        self.log(f"Running code scan on {self.target_path} using rules from {self.rules_path}...")
        
        json_output = self.results_dir / "semgrep.json"
        text_output = self.results_dir / "semgrep.txt"
        
        # Build command
        config_args = self.get_config_args()
        exclude_args = self.get_exclude_args()
        
        # JSON report
        self.log("Generating JSON report...")
        cmd = [
            "semgrep",
            "--disable-version-check",
            *config_args,
            str(self.target_path),
            *exclude_args,
            "--json",
            "-o", str(json_output),
            "--severity=ERROR",
            "--severity=WARNING",
            "--severity=INFO"
        ]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode != 0:
            self.log(f"JSON report generation failed with exit code {result.returncode}", "ERROR")
        
        # Text report
        self.log("Generating text report...")
        cmd = [
            "semgrep",
            "--disable-version-check",
            *config_args,
            str(self.target_path),
            *exclude_args,
            "--text",
            "-o", str(text_output),
            "--severity=ERROR",
            "--severity=WARNING",
            "--severity=INFO"
        ]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode != 0:
            self.log(f"Text report generation failed with exit code {result.returncode}", "ERROR")
        
        # Additional security-focused deep scan
        self.log("Running additional security-focused deep scan...")
        security_json = self.results_dir / "semgrep-security-deep.json"
        cmd = [
            "semgrep",
            "--disable-version-check",
            "--config", "p/security-audit",
            "--config", "p/secrets",
            "--config", "p/owasp-top-ten",
            str(self.target_path),
            *exclude_args,
            "--json",
            "-o", str(security_json)
        ]
        
        # Non-critical, don't fail on error
        try:
            self.run_command(cmd, capture_output=True, timeout=600)
        except Exception as e:
            self.log(f"Security deep scan failed: {e}", "WARNING")
        
        # Check if reports were generated
        if json_output.exists() and json_output.stat().st_size > 0:
            self.log("Semgrep scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("Semgrep scan completed but no results generated", "WARNING")
            return True  # Don't fail if no findings


if __name__ == "__main__":
    import os
    import sys
    
    # Get environment variables
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/SimpleSecCheck/results")
    log_file = os.getenv("LOG_FILE", "SimpleSecCheck/results/logs/scan.log")
    rules_path = os.getenv("SEMGREP_RULES_PATH", "/SimpleSecCheck/scanner/scanners/semgrep/rules")
    exclude_paths = os.getenv("SIMPLESECCHECK_EXCLUDE_PATHS", "")
    
    # Create scanner and run
    scanner = SemgrepScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        rules_path=rules_path,
        exclude_paths=exclude_paths
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
