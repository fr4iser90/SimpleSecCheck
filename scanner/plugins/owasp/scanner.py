"""
OWASP Dependency Check Scanner
Python implementation of run_owasp_dependency_check.sh
"""
import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability


class OWASPScanner(BaseScanner):
    """OWASP Dependency Check scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        # Code scanning (can scan source code for vulnerabilities)
        ScannerCapability(
            scan_type=ScanType.CODE,
            supported_targets=[TargetType.LOCAL_MOUNT, TargetType.GIT_REPO, TargetType.UPLOADED_CODE],
            supported_artifacts=[],
        ),
        # Dependency scanning (primary use case)
        ScannerCapability(
            scan_type=ScanType.DEPENDENCY,
            supported_targets=[TargetType.LOCAL_MOUNT, TargetType.GIT_REPO, TargetType.UPLOADED_CODE],
            supported_artifacts=[],
        ),
    ]
    PRIORITY = 4
    REQUIRES_CONDITION = None
    ENV_VARS = {
        "OWASP_DC_CONFIG_PATH": "/app/scanner/scanners/owasp/config/config.yaml",
        "OWASP_DC_DATA_DIR": "/app/scanner/scanners/owasp/data"
    }
    # SCANNER_NAME wird automatisch aus manifest.yaml geladen
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None,
        data_dir: Optional[str] = None,
        exclude_paths: Optional[str] = None
    ):
        """
        Initialize OWASP Dependency Check scanner
        
        Args:
            target_path: Path to scan
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to OWASP config file
            data_dir: Directory for OWASP data and cache
            exclude_paths: Comma-separated paths to exclude
        """
        super().__init__("OWASP Dependency Check", target_path, results_dir, log_file, config_path)
        self.data_dir = Path(data_dir) if data_dir else Path("/app/scanner/scanners/owasp/data")
        self.exclude_paths = exclude_paths or os.getenv("SIMPLESECCHECK_EXCLUDE_PATHS", "")
    
    def initialize_database(self):
        """Initialize OWASP Dependency Check database if not present"""
        lock_file = self.data_dir / "odc.update.lock"
        
        # Remove lock file if exists (from interrupted update)
        if lock_file.exists():
            self.log("Lock file found from previous session, removing...")
            lock_file.unlink()
        
        # Check if database exists
        if not self.data_dir.exists() or not any(self.data_dir.iterdir()):
            self.log("OWASP Dependency Check database not found. Downloading vulnerability database (this may take 5-15 minutes)...")
            
            if not self.check_tool_installed("dependency-check"):
                self.log("dependency-check command not found!", "ERROR")
                return False
            
            cmd = ["dependency-check", "--updateonly", "--data", str(self.data_dir)]
            
            # Add NVD API key if provided
            nvd_api_key = os.getenv("NVD_API_KEY")
            if nvd_api_key:
                cmd.append(f"--nvdApiKey={nvd_api_key}")
            
            result = self.run_command(cmd, capture_output=True, timeout=1800)  # 30 min timeout
            if result.returncode != 0:
                self.log("Database download failed or incomplete, continuing with partial database...", "WARNING")
        else:
            self.log("Using existing OWASP Dependency Check database.")
        
        return True
    
    def get_exclude_args(self) -> List[str]:
        """Get OWASP exclude arguments"""
        exclude_args = []
        
        if self.exclude_paths:
            for path in self.exclude_paths.split(","):
                path = path.strip()
                if path:
                    exclude_args.extend(["--exclude", f"**/{path}/**"])
        
        return exclude_args
    
    def scan(self) -> bool:
        """Run OWASP Dependency Check scan"""
        if not self.check_tool_installed("dependency-check"):
            self.log("dependency-check not found in PATH", "ERROR")
            return False
        
        # Initialize database first
        if not self.initialize_database():
            return False
        
        self.log(f"Running dependency vulnerability scan on {self.target_path}...")
        
        # Create temporary directory for scan results
        temp_scan_dir = Path(tempfile.mkdtemp(prefix="owasp-dc-scan-"))
        
        try:
            json_output = self.results_dir / "report.json"  # Changed from owasp-dependency-check.json
            html_output = self.results_dir / "report.html"  # Changed from owasp-dependency-check.html
            xml_output = self.results_dir / "report.xml"   # Changed from owasp-dependency-check.xml
            
            # Check if NVD_API_KEY is provided
            nvd_flag = []
            nvd_api_key = os.getenv("NVD_API_KEY")
            if nvd_api_key:
                self.log("Using provided NVD_API_KEY for enhanced vulnerability data...")
                nvd_flag = [f"--nvdApiKey={nvd_api_key}"]
            else:
                self.log("No NVD_API_KEY provided, using public data rate limit...")
                self.log("Consider setting NVD_API_KEY environment variable to avoid rate limiting", "WARNING")
            
            exclude_args = self.get_exclude_args()
            
            # Run OWASP Dependency Check
            self.log("Running comprehensive dependency vulnerability scan...")
            cmd = [
                "dependency-check",
                "--project", "SimpleSecCheck-Dependency-Scan",
                "--scan", str(self.target_path),
                "--format", "JSON",
                "--format", "HTML",
                "--format", "XML",
                "--out", str(temp_scan_dir),
                "--data", str(self.data_dir),
                "--noupdate",
                *nvd_flag,
                *exclude_args
            ]
            
            # Run with suppressed output (errors still logged)
            result = self.run_command(cmd, capture_output=True, timeout=3600)  # 1 hour timeout
            if result.returncode != 0:
                self.log("Scan completed with warnings (rate limits may apply)...", "WARNING")
            
            # Copy results to results directory
            temp_json = temp_scan_dir / "dependency-check-report.json"
            temp_html = temp_scan_dir / "dependency-check-report.html"
            temp_xml = temp_scan_dir / "dependency-check-report.xml"
            
            if temp_json.exists():
                shutil.copy2(temp_json, json_output)
                self.log(f"JSON report copied to {json_output}")
            
            if temp_html.exists():
                shutil.copy2(temp_html, html_output)
                self.log(f"HTML report copied to {html_output}")
            
            if temp_xml.exists():
                shutil.copy2(temp_xml, xml_output)
                self.log(f"XML report copied to {xml_output}")
            
            # Check if any reports were generated
            if json_output.exists() or html_output.exists() or xml_output.exists():
                self.log("OWASP Dependency Check scan completed successfully", "SUCCESS")
                return True
            else:
                self.log("No OWASP Dependency Check report was generated!", "ERROR")
                return False
                
        finally:
            # Clean up temporary directory
            if temp_scan_dir.exists():
                shutil.rmtree(temp_scan_dir, ignore_errors=True)


if __name__ == "__main__":
    import sys
    
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/app/results")
    log_file = os.getenv("LOG_FILE", "app/results/logs/scan.log")
    config_path = os.getenv("OWASP_DC_CONFIG_PATH", "/app/scanner/scanners/owasp/config/config.yaml")
    data_dir = os.getenv("OWASP_DC_DATA_DIR", "/app/scanner/scanners/owasp/data")
    exclude_paths = os.getenv("SIMPLESECCHECK_EXCLUDE_PATHS", "")
    
    scanner = OWASPScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path,
        data_dir=data_dir,
        exclude_paths=exclude_paths
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
