"""
Modern Python Orchestrator
Replaces security-check.sh with dynamic, registry-based scanner execution
No hardcoded steps, no log parsing - direct step communication!
"""
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Add scanner to path for imports
sys.path.insert(0, "/SimpleSecCheck")

try:
    from scanner.core.scanner_registry import ScannerRegistry, ScanType, Scanner
    from scanner.core.step_registry import StepRegistry, StepStatus
except ImportError:
    # Fallback for direct execution
    from core.scanner_registry import ScannerRegistry, ScanType, Scanner
    from core.step_registry import StepRegistry, StepStatus


class ScanOrchestrator:
    """Modern orchestrator using Scanner Registry and Step Registry"""
    
    def __init__(self, step_registry: StepRegistry):
        """
        Initialize orchestrator
        
        Args:
            step_registry: Step registry for step tracking
        """
        self.step_registry = step_registry
        self.base_dir = Path("/SimpleSecCheck")
        self.tools_dir = self.base_dir / "scripts" / "tools"
        self.target_path = Path(os.getenv("TARGET_PATH_IN_CONTAINER", "/target"))
        self.results_dir = Path(os.getenv("RESULTS_DIR_IN_CONTAINER", "/SimpleSecCheck/results"))
        self.logs_dir = Path(os.getenv("LOGS_DIR_IN_CONTAINER", "/SimpleSecCheck/logs"))
        self.log_file = self.logs_dir / "scan.log"
        
        # Ensure directories exist
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Scan configuration
        self.scan_type = ScanType(os.getenv("SCAN_TYPE", "code"))
        self.collect_metadata = os.getenv("COLLECT_METADATA", "false").lower() == "true"
        
        # Overall success tracking
        self.overall_success = True
        self.scanner_statuses: Dict[str, str] = {}
    
    def log_message(self, message: str):
        """Log message to scan.log"""
        import datetime
        log_line = f"[SimpleSecCheck Orchestrator] ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ({os.getpid()}) {message}"
        print(log_line)
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"{log_line}\n")
        except Exception as e:
            print(f"[Orchestrator] Error writing to log: {e}")
    
    def _get_conditions(self) -> Dict[str, Any]:
        """Get conditions for conditional scanners"""
        conditions = {}
        
        # Check for native mobile apps (only for code scans)
        if self.scan_type == ScanType.CODE:
            try:
                from scanner.core.project_detector import detect_native_app
                result = detect_native_app(str(self.target_path))
                conditions["IS_NATIVE"] = result.get("has_native", False)
            except Exception as e:
                self.log_message(f"[WARNING] Could not detect native apps: {e}")
                conditions["IS_NATIVE"] = False
        
        # Check for container image scanners
        conditions["CLAIR_IMAGE"] = os.getenv("CLAIR_IMAGE", "")
        conditions["ANCHORE_IMAGE"] = os.getenv("ANCHORE_IMAGE", "")
        
        return conditions
    
    async def _run_scanner(self, scanner: Scanner) -> bool:
        """
        Run a scanner script (Bash) or Python scanner class
        
        Args:
            scanner: Scanner definition
        
        Returns:
            True if successful, False otherwise
        """
        # Start step
        self.step_registry.start_step(scanner.name, f"Running {scanner.name} scan...")
        self.log_message(f"--- Orchestrating {scanner.name} Scan ---")
        
        # Prepare environment
        env = os.environ.copy()
        env["TARGET_PATH"] = str(self.target_path)
        env["RESULTS_DIR"] = str(self.results_dir)
        env["LOG_FILE"] = str(self.log_file)
        
        # Add scanner-specific environment variables
        if scanner.env_vars:
            for key, value in scanner.env_vars.items():
                env[key] = value
        
        # Handle conditional environment variables
        if scanner.requires_condition == "CLAIR_IMAGE":
            env["CLAIR_IMAGE"] = os.getenv("CLAIR_IMAGE", "")
        elif scanner.requires_condition == "ANCHORE_IMAGE":
            env["ANCHORE_IMAGE"] = os.getenv("ANCHORE_IMAGE", "")
        
        # Check if Python scanner class exists (new approach)
        python_scanner_class = scanner.env_vars.get("PYTHON_SCANNER_CLASS") if scanner.env_vars else None
        
        if python_scanner_class:
            # Use Python scanner class
            try:
                self.log_message(f"Using Python scanner class: {python_scanner_class}")
                module_path, class_name = python_scanner_class.rsplit(".", 1)
                module = __import__(module_path, fromlist=[class_name])
                scanner_class = getattr(module, class_name)
                
                # Build scanner arguments from env_vars
                scanner_kwargs = {
                    "target_path": str(self.target_path),
                    "results_dir": str(self.results_dir),
                    "log_file": str(self.log_file),
                }
                
                # Add config_path if available (check all possible config keys)
                config_key = None
                for key in ["CONFIG_PATH", "SEMGREP_RULES_PATH", "TRIVY_CONFIG_PATH", 
                            "SAFETY_CONFIG_PATH", "OWASP_DC_CONFIG_PATH", "CODEQL_CONFIG_PATH",
                            "SNYK_CONFIG_PATH", "SONARQUBE_CONFIG_PATH", "TERRAFORM_SECURITY_CONFIG_PATH",
                            "CHECKOV_CONFIG_PATH", "TRUFFLEHOG_CONFIG_PATH", "GITLEAKS_CONFIG_PATH",
                            "DETECT_SECRETS_CONFIG_PATH", "NPM_AUDIT_CONFIG_PATH", "ESLINT_CONFIG_PATH",
                            "BRAKEMAN_CONFIG_PATH", "BANDIT_CONFIG_PATH", "ZAP_CONFIG_PATH",
                            "NUCLEI_CONFIG_PATH", "WAPITI_CONFIG_PATH", "NIKTO_CONFIG_PATH",
                            "BURP_CONFIG_PATH", "KUBE_HUNTER_CONFIG_PATH", "KUBE_BENCH_CONFIG_PATH",
                            "DOCKER_BENCH_CONFIG_PATH", "CLAIR_CONFIG_PATH", "ANCHORE_CONFIG_PATH"]:
                    if key in scanner.env_vars:
                        config_key = key
                        break
                
                if config_key:
                    scanner_kwargs["config_path"] = scanner.env_vars[config_key]
                
                # Add scanner-specific parameters
                exclude_paths = os.getenv("SIMPLESECCHECK_EXCLUDE_PATHS", "")
                
                if scanner.name == "Trivy":
                    scanner_kwargs["scan_type"] = os.getenv("TRIVY_SCAN_TYPE", "fs")
                    scanner_kwargs["exclude_paths"] = exclude_paths
                elif scanner.name == "OWASP Dependency Check":
                    scanner_kwargs["data_dir"] = scanner.env_vars.get("OWASP_DC_DATA_DIR")
                    scanner_kwargs["exclude_paths"] = exclude_paths
                elif scanner.name == "Semgrep":
                    scanner_kwargs["rules_path"] = scanner.env_vars.get("SEMGREP_RULES_PATH")
                    scanner_kwargs["exclude_paths"] = exclude_paths
                elif scanner.name == "CodeQL":
                    scanner_kwargs["queries_path"] = scanner.env_vars.get("CODEQL_QUERIES_PATH")
                elif scanner.name in ["Detect-secrets", "npm audit", "ESLint", "Checkov"]:
                    scanner_kwargs["exclude_paths"] = exclude_paths
                elif scanner.name in ["ZAP", "Nuclei", "Wapiti", "Nikto", "Burp"]:
                    scanner_kwargs["zap_target"] = os.getenv("ZAP_TARGET", "http://host.docker.internal:8000")
                    if scanner.name == "ZAP":
                        scanner_kwargs["startup_delay"] = int(os.getenv("ZAP_STARTUP_DELAY", "25"))
                elif scanner.name == "Clair":
                    scanner_kwargs["clair_image"] = os.getenv("CLAIR_IMAGE", "")
                elif scanner.name == "Anchore":
                    scanner_kwargs["anchore_image"] = os.getenv("ANCHORE_IMAGE", "")
                
                # Instantiate and run scanner
                scanner_instance = scanner_class(**scanner_kwargs)
                
                success = scanner_instance.run()
                
                if success:
                    self.log_message(f"{scanner.name} completed successfully (exit code 0)")
                    self.scanner_statuses[scanner.name] = "SUCCESS"
                    self.step_registry.complete_step(scanner.name, f"{scanner.name} scan completed")
                    return True
                else:
                    self.log_message(f"[ORCHESTRATOR ERROR] {scanner.name} failed")
                    self.scanner_statuses[scanner.name] = "FAILED"
                    self.step_registry.fail_step(scanner.name, f"{scanner.name} scan failed")
                    self.overall_success = False
                    return False
                    
            except Exception as e:
                self.log_message(f"[ORCHESTRATOR ERROR] {scanner.name} Python scanner exception: {e}")
                self.scanner_statuses[scanner.name] = "FAILED"
                self.step_registry.fail_step(scanner.name, f"{scanner.name} scan error: {str(e)}")
                self.overall_success = False
                return False
        
        # Fallback to Bash script (legacy)
        script_path = Path(scanner.script_path)
        
        if not script_path.exists():
            self.log_message(f"[ORCHESTRATOR ERROR] {scanner.name} script not found: {script_path}")
            self.scanner_statuses[scanner.name] = "FAILED"
            self.step_registry.fail_step(scanner.name, f"Script not found: {script_path}")
            self.overall_success = False
            return False
        
        self.log_message(f"Executing {script_path}...")
        
        # Execute scanner script
        try:
            result = subprocess.run(
                ["/bin/bash", str(script_path)],
                env=env,
                cwd=str(self.base_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=3600  # 1 hour timeout per scanner
            )
            
            # Write output to log
            if result.stdout:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(result.stdout)
            
            if result.returncode == 0:
                self.log_message(f"{scanner.name} completed successfully (exit code 0)")
                self.scanner_statuses[scanner.name] = "SUCCESS"
                self.step_registry.complete_step(scanner.name, f"{scanner.name} scan completed")
                return True
            else:
                self.log_message(f"[ORCHESTRATOR ERROR] {scanner.name} failed with exit code {result.returncode}")
                self.scanner_statuses[scanner.name] = "FAILED"
                self.step_registry.fail_step(scanner.name, f"{scanner.name} scan failed")
                self.overall_success = False
                return False
                
        except subprocess.TimeoutExpired:
            self.log_message(f"[ORCHESTRATOR ERROR] {scanner.name} timed out after 1 hour")
            self.scanner_statuses[scanner.name] = "FAILED"
            self.step_registry.fail_step(scanner.name, f"{scanner.name} scan timed out")
            self.overall_success = False
            return False
        except Exception as e:
            self.log_message(f"[ORCHESTRATOR ERROR] {scanner.name} exception: {e}")
            self.scanner_statuses[scanner.name] = "FAILED"
            self.step_registry.fail_step(scanner.name, f"{scanner.name} scan error: {str(e)}")
            self.overall_success = False
            return False
        finally:
            self.log_message(f"--- {scanner.name} Scan Orchestration Finished ---")
    
    async def _collect_metadata(self):
        """Collect scan metadata if enabled"""
        if not self.collect_metadata:
            return
        
        self.log_message("--- Collecting Metadata ---")
        self.step_registry.start_step("Metadata Collection", "Collecting scan metadata...")
        
        try:
            from scanner.core.scan_metadata import collect_scan_metadata, save_metadata
            
            # Get finding policy
            finding_policy = os.getenv("FINDING_POLICY_FILE_IN_CONTAINER", "")
            if not finding_policy:
                finding_policy = None
            
            # Get CI mode
            ci_mode = os.getenv("CI_MODE", "false").lower() == "true"
            
            # Get target paths
            target_path_host = os.getenv("TARGET_PATH_HOST", "")
            original_target_path = os.getenv("ORIGINAL_TARGET_PATH", "")
            
            # For CI mode, use original repository path
            metadata_target_path_host = original_target_path if original_target_path else target_path_host
            if not metadata_target_path_host:
                metadata_target_path_host = None
            
            # Collect metadata
            metadata = collect_scan_metadata(
                target_path=str(self.target_path),
                target_path_host=metadata_target_path_host,
                scan_type=self.scan_type.value,
                results_dir=str(self.results_dir),
                finding_policy=finding_policy,
                ci_mode=ci_mode
            )
            
            # Save metadata
            if save_metadata(metadata, str(self.results_dir)):
                self.log_message("Metadata collected and saved successfully")
                self.step_registry.complete_step("Metadata Collection", "Metadata collection completed")
            else:
                self.log_message("[WARNING] Failed to save metadata")
                self.step_registry.complete_step("Metadata Collection", "Metadata collection completed (with warnings)")
                
        except Exception as e:
            self.log_message(f"[ERROR] Error collecting metadata: {e}")
            self.step_registry.complete_step("Metadata Collection", "Metadata collection completed (with errors)")
    
    async def run_scan(self) -> int:
        """
        Run the complete scan
        
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        self.log_message("SimpleSecCheck Scan Started")
        self.log_message(f"Scan Type: {self.scan_type.value}")
        self.log_message(f"Target Path: {self.target_path}")
        self.log_message(f"Results Dir: {self.results_dir}")
        
        # Step 1: Initialization
        self.step_registry.start_step("Initialization", "Initializing scan...")
        self.log_message("--- Initialization ---")
        # Initialization logic here (if needed)
        self.step_registry.complete_step("Initialization", "Scan initialized")
        
        # Step 2: Get scanners for this scan type
        conditions = self._get_conditions()
        scanners = ScannerRegistry.get_scanners_for_type(self.scan_type, conditions)
        
        self.log_message(f"Found {len(scanners)} scanners for {self.scan_type.value} scan")
        
        # Step 3: Run all scanners
        for scanner in scanners:
            await self._run_scanner(scanner)
        
        # Step 4: Collect metadata (if enabled)
        if self.collect_metadata:
            await self._collect_metadata()
        
        # Step 5: Completion
        self.step_registry.start_step("Completion", "Finalizing scan...")
        if self.overall_success:
            self.log_message("SimpleSecCheck Scan Completed Successfully")
            self.step_registry.complete_step("Completion", "Scan completed successfully")
            return 0
        else:
            self.log_message("SimpleSecCheck Scan Completed with Errors")
            self.step_registry.complete_step("Completion", "Scan completed with errors")
            return 1


async def main():
    """Main entry point for orchestrator"""
    import sys
    
    # Get scan_id from environment or generate
    scan_id = os.getenv("SCAN_ID", "")
    if not scan_id:
        from datetime import datetime
        scan_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Get results directory
    results_dir = Path(os.getenv("RESULTS_DIR_IN_CONTAINER", "/SimpleSecCheck/results"))
    
    # Create step registry (without WebSocket manager for now - will be added in integration)
    step_registry = StepRegistry(scan_id, results_dir, websocket_manager=None)
    
    # Create orchestrator
    orchestrator = ScanOrchestrator(step_registry)
    
    # Run scan
    exit_code = await orchestrator.run_scan()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
