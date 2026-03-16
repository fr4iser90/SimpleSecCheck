"""
ZAP Scanner
Python implementation of run_zap.sh
"""
import os
import shutil
from pathlib import Path
from typing import Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability


class ZAPScanner(BaseScanner):
    """ZAP scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.WEBSITE,
            supported_targets=[TargetType.WEBSITE],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 1
    REQUIRES_CONDITION = None
    ENV_VARS = {
        "ZAP_CONFIG_PATH": "/app/scanner/plugins/zap/config/baseline.conf"
    }
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None,
        zap_target: Optional[str] = None,
        startup_delay: int = 25
    ):
        """
        Initialize ZAP scanner
        
        Args:
            target_path: Path to scan (not used for website scans)
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to ZAP config file (optional)
            zap_target: Target URL to scan
            startup_delay: Delay in seconds to wait for target to be ready
        """
        super().__init__("ZAP", target_path, results_dir, log_file, config_path)
        self.zap_target = zap_target or os.getenv("SCAN_TARGET", "http://host.docker.internal:8000")
        self.startup_delay = startup_delay or int(os.getenv("ZAP_STARTUP_DELAY", "25"))
    
    def check_target_reachable(self) -> bool:
        """Check if target is reachable"""
        if not self.check_tool_installed("curl"):
            self.log("curl not found. Skipping target reachability check.", "WARNING")
            return True
        
        self.log(f"Checking reachability of ZAP target {self.zap_target} with curl...")
        cmd = ["curl", "--output", "/dev/null", "--silent", "--head", "--fail", "--max-time", "15", self.zap_target]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode == 0:
            self.log(f"Successfully connected to {self.zap_target}.", "SUCCESS")
            return True
        else:
            self.log(f"Failed to connect to {self.zap_target}. ZAP scan may fail or produce limited results. Proceeding anyway...", "WARNING")
            return False
    
    def find_zap_baseline_script(self) -> Optional[Path]:
        """Find zap-baseline.py script"""
        import shutil
        zap_script = shutil.which("zap-baseline.py")
        if zap_script:
            return Path(zap_script)
        return None
    
    def scan(self) -> bool:
        """Run ZAP scan"""
        if not self.check_tool_installed("python3"):
            self.log("python3 is not installed or not in PATH. ZAP scan cannot run.", "ERROR")
            return False
        
        zap_baseline = self.find_zap_baseline_script()
        if not zap_baseline:
            self.log("zap-baseline.py not found. ZAP scan cannot run.", "ERROR")
            return False
        
        self.log(f"Using ZAP baseline script at: {zap_baseline}")
        
        # Wait for target to be ready
        if self.startup_delay > 0:
            import time
            self.log(f"Waiting {self.startup_delay} seconds for target application ({self.zap_target}) to start...")
            time.sleep(self.startup_delay)
        
        # Check target reachability
        self.check_target_reachable()
        
        # Set environment variables
        os.environ.setdefault("ZAP_PATH", "/opt/ZAP_2.16.1")
        os.environ.setdefault("JAVA_HOME", "/usr/lib/jvm/java-17-openjdk-amd64")
        os.environ["ZAP_OPTIONS"] = "-config api.disablekey=true -config spider.maxDuration=10 -config scanner.maxDuration=30 -config scanner.maxRuleTimeInMs=60000"
        
        self.log(f"[ZAP ENV] ZAP_PATH={os.environ['ZAP_PATH']}, JAVA_HOME={os.environ['JAVA_HOME']}")
        self.log(f"[ZAP] Starting DEEP baseline scan on {self.zap_target} with aggressive policies...")
        
        xml_output = self.results_dir / "report.xml"  # Changed from zap-report.xml
        html_output = self.results_dir / "report.html"  # Changed from html-report.html
        
        # Remove pre-existing reports
        if xml_output.exists():
            xml_output.unlink()
        if html_output.exists():
            html_output.unlink()
        
        # XML report
        self.log("[ZAP CMD XML] Executing DEEP scan...")
        cmd = ["python3", str(zap_baseline), "-d", "-t", self.zap_target, "-x", "report.xml", "-J", "-a"]  # Changed from zap-report.xml
        
        result = self.run_command(cmd, cwd=self.results_dir, capture_output=True)
        if result.returncode != 0:
            self.log(f"[ZAP CMD XML WARN] zap-baseline.py for XML exited with {result.returncode}.", "WARNING")
        
        # HTML report
        self.log("[ZAP CMD HTML] Executing DEEP scan...")
        cmd = ["python3", str(zap_baseline), "-d", "-t", self.zap_target, "-f", "html", "-o", "report.html", "-J", "-a"]  # Changed from zap-report.html
        
        result = self.run_command(cmd, cwd=self.results_dir, capture_output=True)
        if result.returncode != 0:
            self.log(f"[ZAP CMD HTML WARN] zap-baseline.py for HTML exited with {result.returncode}.", "WARNING")
        
        # Check if reports were created
        xml_found = xml_output.exists()
        html_found = html_output.exists()
        
        # Fallback: search common ZAP directories
        if not xml_found:
            common_dirs = [Path("/home/zap/.ZAP/"), Path("/zap/wrk/"), Path("/tmp/")]
            for search_dir in common_dirs:
                if search_dir.exists():
                    found_xml = list(search_dir.rglob("zap-report.xml"))
                    if found_xml:
                        shutil.copy2(found_xml[0], xml_output)
                        xml_found = True
                        self.log(f"Found XML report in {found_xml[0]}, copied to {xml_output}")
                        break
        
        if not html_found:
            common_dirs = [Path("/home/zap/.ZAP/"), Path("/zap/wrk/"), Path("/tmp/")]
            for search_dir in common_dirs:
                if search_dir.exists():
                    found_html = list(search_dir.rglob("zap-report.html"))
                    if found_html:
                        shutil.copy2(found_html[0], html_output)
                        html_found = True
                        self.log(f"Found HTML report in {found_html[0]}, copied to {html_output}")
                        break
        
        if xml_found or html_found:
            self.log("ZAP scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("No ZAP report was generated!", "ERROR")
            return False


if __name__ == "__main__":
    import sys
    
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/app/results")
    log_file = os.getenv("LOG_FILE", "app/results/logs/scan.log")
    config_path = os.getenv("ZAP_CONFIG_PATH", "/app/scanner/plugins/zap/config/baseline.conf")
    zap_target = os.getenv("SCAN_TARGET", "http://host.docker.internal:8000")
    startup_delay = int(os.getenv("ZAP_STARTUP_DELAY", "25"))
    
    scanner = ZAPScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path,
        zap_target=zap_target,
        startup_delay=startup_delay
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
