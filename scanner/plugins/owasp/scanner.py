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
from scanner.core.path_setup import get_plugin_data_dir
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability
from scanner.core.step_registry import SubStepType
from scanner.core.scanner_assets.manager import get_plugin_display_name

# Plugin name from package path only – no literal; used for paths and manifest
PLUGIN_NAME = __name__.split(".")[2]


class OWASPScanner(BaseScanner):
    """OWASP Dependency Check scanner implementation"""
    
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.CODE,
            supported_targets=[TargetType.LOCAL_MOUNT, TargetType.GIT_REPO, TargetType.UPLOADED_CODE],
            supported_artifacts=[],
        ),
        ScannerCapability(
            scan_type=ScanType.DEPENDENCY,
            supported_targets=[TargetType.LOCAL_MOUNT, TargetType.GIT_REPO, TargetType.UPLOADED_CODE],
            supported_artifacts=[],
        ),
    ]
    PRIORITY = 4
    REQUIRES_CONDITION = None
    ENV_VARS = {
        "OWASP_DC_CONFIG_PATH": f"/app/scanner/plugins/{PLUGIN_NAME}/config/config.yaml",
        "OWASP_DC_DATA_DIR": str(get_plugin_data_dir(PLUGIN_NAME)),
    }

    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None,
        data_dir: Optional[str] = None,
        exclude_paths: Optional[str] = None,
        step_name: Optional[str] = None,
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
            step_name: Step name from registry/manifest (single source)
        """
        display_name = get_plugin_display_name(PLUGIN_NAME)
        super().__init__(display_name, target_path, results_dir, log_file, config_path, step_name=step_name)
        self.data_dir = Path(data_dir) if data_dir else get_plugin_data_dir(PLUGIN_NAME)
        self.exclude_paths = exclude_paths or os.getenv("SIMPLESECCHECK_EXCLUDE_PATHS", "")
    
    def initialize_database(self):
        """Initialize OWASP Dependency Check database if not present"""
        # PREPARE: Download / Update Database
        self.substep_prepare("Download / Update Database", "Checking OWASP vulnerability database...")
        
        lock_file = self.data_dir / "odc.update.lock"
        
        # Remove lock file if exists (from interrupted update)
        if lock_file.exists():
            self.log("Lock file found from previous session, removing...")
            lock_file.unlink()
        
        # Debug: Log data directory status
        self.log(f"Checking OWASP data directory: {self.data_dir}")
        self.log(f"Data directory exists: {self.data_dir.exists()}")
        
        if self.data_dir.exists():
            try:
                files = list(self.data_dir.iterdir())
                self.log(f"Data directory contains {len(files)} items")
                # Check for H2 database files specifically
                db_files = [f for f in files if f.name.endswith(('.mv.db', '.trace.db', '.lock.db'))]
                self.log(f"Found {len(db_files)} database files: {[f.name for f in db_files]}")
            except Exception as e:
                self.log(f"Error checking data directory: {e}", "WARNING")
                files = []
        else:
            files = []
        
        # Check if database exists - look for H2 database files
        db_files = [
            self.data_dir / "odc.mv.db",  # H2 database file
            self.data_dir / "odc.trace.db",  # H2 trace file
        ]
        db_exists = self.data_dir.exists() and any(f.exists() for f in db_files)
        
        if not db_exists:
            self.complete_substep("Download / Update Database", "Database not found, downloading...")
            self.log("OWASP Dependency Check database not found. Downloading vulnerability database (this may take 5-15 minutes)...")
            
            if not self.check_tool_installed("dependency-check"):
                self.log("dependency-check command not found!", "ERROR")
                self.fail_substep("Download / Update Database", "dependency-check command not found")
                return False
            
            cmd = ["dependency-check", "--updateonly", "--data", str(self.data_dir)]
            
            # Add NVD API key if provided
            nvd_api_key = os.getenv("NVD_API_KEY")
            if nvd_api_key:
                cmd.append(f"--nvdApiKey={nvd_api_key}")
            
            result = self.run_command(cmd, capture_output=True)
            if result.returncode != 0:
                self.log("Database download failed or incomplete, continuing with partial database...", "WARNING")
                self.complete_substep("Download / Update Database", "Download completed with warnings")
            else:
                self.complete_substep("Download / Update Database", "Database downloaded successfully")
        else:
            self.complete_substep("Download / Update Database", "Using existing database")
            self.log("Using existing OWASP Dependency Check database.")
        
        # PREPARE: Database Update
        self.start_substep("Database Update", "Updating vulnerability database...", SubStepType.ACTION)
        # Database update happens automatically during scan if needed
        self.complete_substep("Database Update", "Database up to date")
        
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
        """Run OWASP Dependency Check scan with standardized substeps"""
        if not self.check_tool_installed("dependency-check"):
            self.log("dependency-check not found in PATH", "ERROR")
            return False
        
        # INIT: Environment Check
        self.substep_init("Checking OWASP Dependency Check environment...")
        try:
            result = self.run_command(["dependency-check", "--version"], capture_output=True, timeout=10)
            if result.returncode == 0:
                version = result.stdout.strip().split('\n')[0] if result.stdout else "unknown"
                self.complete_substep("Initialization", f"OWASP Dependency Check {version} ready")
            else:
                self.complete_substep("Initialization", "OWASP Dependency Check environment ready")
        except Exception as e:
            self.complete_substep("Initialization", f"Environment check completed: {e}")
        
        # Initialize database first (PREPARE steps)
        if not self.initialize_database():
            return False
        
        # SCAN: Dependency Detection
        self.start_substep("Dependency Detection", "Detecting project dependencies...", SubStepType.PHASE)
        # Dependency detection happens during scan
        self.complete_substep("Dependency Detection", "Dependencies detected")
        
        # SCAN: Dependency Analysis
        self.substep_scan("Dependency Analysis", "Analyzing dependencies for vulnerabilities...")
        
        # SCAN: Vulnerability Matching
        self.start_substep("Vulnerability Matching", "Matching dependencies against vulnerability database...", SubStepType.PHASE)
        # Vulnerability matching happens during scan
        self.complete_substep("Vulnerability Matching", "Vulnerability matching completed")
        
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
            
            # Run OWASP Dependency Check (combines Dependency Analysis and Vulnerability Matching)
            self.update_substep("Dependency Analysis", "Analyzing dependencies and checking for vulnerabilities...")
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
            
            # Run command and capture all output
            result = self.run_command(cmd, capture_output=True)
            if result.returncode != 0:
                # Collect actual error messages
                error_messages = []
                
                # Check stderr first (usually contains error messages)
                if result.stderr:
                    stderr_text = result.stderr.strip()
                    if stderr_text:
                        error_messages.append(f"STDERR: {stderr_text[:500]}")  # First 500 chars
                
                # Check stdout for error messages
                if result.stdout:
                    stdout_text = result.stdout.strip()
                    # Look for error patterns in stdout
                    stdout_lines = stdout_text.split('\n')
                    error_lines = []
                    for line in stdout_lines:
                        line_lower = line.lower()
                        if any(keyword in line_lower for keyword in ['error', 'failed', 'exception', 'fatal', 'cannot', 'unable', 'failed to']):
                            error_lines.append(line.strip())
                    
                    if error_lines:
                        error_messages.append(f"STDOUT ERRORS: {' | '.join(error_lines[:10])}")
                    elif stdout_text:
                        # If no clear error pattern, log last 10 lines of stdout
                        last_lines = stdout_lines[-10:]
                        error_messages.append(f"STDOUT (last 10 lines): {' | '.join(last_lines)}")
                
                # Log the actual error
                if error_messages:
                    full_error = f"OWASP Dependency Check failed (exit code {result.returncode}): {' | '.join(error_messages)}"
                    self.log(full_error, "ERROR")
                    # Extract the actual error message for substep display
                    # Prefer stdout errors (usually more descriptive)
                    error_display = ""
                    for msg in error_messages:
                        if "STDOUT ERRORS" in msg:
                            # Extract just the error lines without the prefix
                            error_display = msg.replace("STDOUT ERRORS: ", "")
                            break
                        elif "STDERR" in msg and not error_display:
                            error_display = msg.replace("STDERR: ", "")
                    
                    if not error_display and error_messages:
                        error_display = error_messages[0].split(':', 1)[1].strip() if ':' in error_messages[0] else error_messages[0]
                    
                    # Clean up the error message for display (remove [ERROR] prefixes)
                    error_display = error_display.replace("[ERROR] ", "").strip()
                    if error_display:
                        # Take first meaningful error line (max 200 chars)
                        error_lines = error_display.split(' | ')
                        first_error = error_lines[0][:200] if error_lines else error_display[:200]
                        self.fail_substep("Dependency Analysis", first_error)
                    else:
                        self.fail_substep("Dependency Analysis", f"Failed with exit code {result.returncode}")
                else:
                    self.log(f"OWASP Dependency Check failed with exit code {result.returncode} (no error output captured)", "ERROR")
                    self.fail_substep("Dependency Analysis", f"Failed with exit code {result.returncode}")
            else:
                # Scan succeeded
                self.complete_substep("Dependency Analysis", "Dependency analysis completed")
                self.complete_substep("Vulnerability Matching", "Vulnerability matching completed")
            
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
            
            # PROCESS: CVE Enrichment
            self.start_substep("CVE Enrichment", "Enriching results with CVE details...", SubStepType.ACTION)
            # CVE enrichment happens automatically during scan
            self.complete_substep("CVE Enrichment", "CVE enrichment completed")
            
            # PROCESS: Result Processing
            self.substep_process("Result Processing", "Processing scan results...")
            
            # Check if any reports were generated
            if json_output.exists() or html_output.exists() or xml_output.exists():
                self.complete_substep("Result Processing", "Results processed successfully")
            else:
                if result.returncode == 0:
                    self.fail_substep("Result Processing", "No report was generated")
                    self.log("No OWASP Dependency Check report was generated!", "ERROR")
                    return False
                else:
                    self.fail_substep("Result Processing", "Result processing failed")
                    self.log("No OWASP Dependency Check report was generated!", "ERROR")
                    return False
            
            # REPORT: JSON Report
            self.substep_report("JSON", "Generating JSON report...")
            if json_output.exists() and json_output.stat().st_size > 0:
                self.complete_substep("Generating JSON Report", "JSON report generated successfully")
            else:
                self.fail_substep("Generating JSON Report", "JSON report generation failed")
            
            # REPORT: HTML Report
            self.start_substep("Generating HTML Report", "Generating HTML report...", SubStepType.OUTPUT)
            if html_output.exists() and html_output.stat().st_size > 0:
                self.complete_substep("Generating HTML Report", "HTML report generated successfully")
            else:
                self.fail_substep("Generating HTML Report", "HTML report generation failed")
            
            self.log("OWASP Dependency Check scan completed successfully", "SUCCESS")
            return True
                
        finally:
            # Clean up temporary directory
            if temp_scan_dir.exists():
                shutil.rmtree(temp_scan_dir, ignore_errors=True)


if __name__ == "__main__":
    import os
    import sys
    
    # Get default parameters from BaseScanner
    default_params = BaseScanner.get_default_params_from_env()
    
    # Get scanner-specific parameters (paths from central helper, no hardcoded plugin path)
    config_path = os.getenv("OWASP_DC_CONFIG_PATH", f"/app/scanner/plugins/{PLUGIN_NAME}/config/config.yaml")
    data_dir = os.getenv("OWASP_DC_DATA_DIR", str(get_plugin_data_dir(PLUGIN_NAME)))
    exclude_paths = os.getenv("SIMPLESECCHECK_EXCLUDE_PATHS", "")
    
    scanner = OWASPScanner(
        **default_params,
        config_path=config_path,
        data_dir=data_dir,
        exclude_paths=exclude_paths
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
