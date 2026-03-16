"""
npm audit Scanner
Python implementation of run_npm_audit.sh
"""
import os
import json
from pathlib import Path
from typing import List, Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability


class NpmAuditScanner(BaseScanner):
    """npm audit scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.DEPENDENCY,
            supported_targets=[TargetType.LOCAL_MOUNT, TargetType.GIT_REPO, TargetType.UPLOADED_CODE],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 21
    REQUIRES_CONDITION = None
    ENV_VARS = {
        "NPM_AUDIT_CONFIG_PATH": "/app/scanner/plugins/npm_audit/config/config.yaml"
    }
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None,
        exclude_paths: Optional[str] = None
    ):
        """
        Initialize npm audit scanner
        
        Args:
            target_path: Path to scan
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to npm audit config file (optional)
            exclude_paths: Comma-separated paths to exclude
        """
        super().__init__("npm audit", target_path, results_dir, log_file, config_path)
        self.exclude_paths = exclude_paths or os.getenv("SIMPLESECCHECK_EXCLUDE_PATHS", "")
    
    def find_package_json_files(self) -> List[Path]:
        """Find package.json files (excluding node_modules)"""
        package_files = []
        
        for package_json in self.target_path.rglob("package.json"):
            # Skip node_modules
            if "node_modules" in str(package_json):
                continue
            
            # Check exclude paths
            skip = False
            if self.exclude_paths:
                for exclude in self.exclude_paths.split(","):
                    exclude = exclude.strip()
                    if exclude and exclude != "node_modules" and exclude in str(package_json):
                        skip = True
                        break
            
            if not skip:
                package_files.append(package_json)
        
        return package_files
    
    def scan(self) -> bool:
        """Run npm audit scan"""
        if not self.check_tool_installed("npm"):
            self.log("npm command not found, skipping npm audit scan.", "WARNING")
            return True
        
        self.log(f"Running npm dependency security scan on {self.target_path}...")
        
        package_files = self.find_package_json_files()
        
        if not package_files:
            self.log("No package.json files found, skipping scan.", "WARNING")
            return True
        
        self.log(f"Found {len(package_files)} package.json file(s).")
        
        json_output = self.results_dir / "report.json"  # Changed from npm-audit.json
        text_output = self.results_dir / "report.txt"   # Changed from npm-audit.txt
        
        # Scan first package.json (npm audit audits all dependencies)
        first_package = package_files[0]
        package_dir = first_package.parent
        
        self.log(f"Scanning directory: {package_dir}")
        
        # JSON report
        cmd = ["npm", "audit", "--json"]
        result = self.run_command(cmd, cwd=package_dir, capture_output=True)
        
        if result.returncode == 0 and result.stdout:
            with open(json_output, "w", encoding="utf-8") as f:
                f.write(result.stdout)
        else:
            self.log("JSON report generation failed; no report written.", "WARNING")
        
        # Text report
        cmd = ["npm", "audit"]
        result = self.run_command(cmd, cwd=package_dir, capture_output=True)
        
        if result.returncode == 0 and result.stdout:
            with open(text_output, "w", encoding="utf-8") as f:
                f.write(result.stdout)
        else:
            self.log("Text report generation failed; no text report written.", "WARNING")
        
        if json_output.exists() or text_output.exists():
            self.log(f"Scan completed. Found {len(package_files)} package.json files.", "SUCCESS")
            return True
        else:
            self.log("No npm audit report was generated!", "ERROR")
            return False


if __name__ == "__main__":
    import sys
    
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/app/results")
    log_file = os.getenv("LOG_FILE", "app/results/logs/scan.log")
    config_path = os.getenv("NPM_AUDIT_CONFIG_PATH", "/app/scanner/plugins/npm_audit/config/config.yaml")
    exclude_paths = os.getenv("SIMPLESECCHECK_EXCLUDE_PATHS", "")
    
    scanner = NpmAuditScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path,
        exclude_paths=exclude_paths
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
