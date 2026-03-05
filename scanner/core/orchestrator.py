"""
Modern Python Orchestrator
Replaces the legacy shell-based orchestrator with dynamic, registry-based scanner execution
No hardcoded steps, no log parsing - direct step communication!
"""
import os
import subprocess
import sys
import inspect
from pathlib import Path
from typing import Optional, Dict, Any
import ipaddress

# Add scanner to path for imports
if "/SimpleSecCheck" not in sys.path:
    sys.path.insert(0, "/SimpleSecCheck")
if "/SimpleSecCheck/scanner" not in sys.path:
    sys.path.insert(0, "/SimpleSecCheck/scanner")

# Ensure scanner auto-discovery runs before registry usage
try:
    import scanner.scanners  # noqa: F401
except Exception:
    pass

try:
    from scanner.core.scanner_registry import ScannerRegistry, ScanType, TargetType, Scanner
    from scanner.core.step_registry import StepRegistry, StepStatus, Step
except ImportError:
    # Fallback for direct execution
    from core.scanner_registry import ScannerRegistry, ScanType, TargetType, Scanner
    from core.step_registry import StepRegistry, StepStatus, Step


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
        self.logs_dir = self.results_dir / "logs"
        self.log_file = self.logs_dir / "scan.log"
        
        # Ensure directories exist
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Scan configuration
        scan_type_env = os.getenv("SCAN_TYPE")
        self.scan_types = [ScanType(scan_type_env)] if scan_type_env else None
        self.target_type = self._resolve_target_type()
        self.collect_metadata = os.getenv("COLLECT_METADATA", "false").lower() == "true"
        
        # Selected scanners (optional - if empty, run all scanners)
        selected_scanners_json = os.getenv("SELECTED_SCANNERS")
        if selected_scanners_json:
            import json
            try:
                self.selected_scanners = set(json.loads(selected_scanners_json))
                self.log_message(f"Selected scanners: {', '.join(sorted(self.selected_scanners))}")
            except (json.JSONDecodeError, TypeError):
                self.log_message(f"[WARNING] Invalid SELECTED_SCANNERS format: {selected_scanners_json}, running all scanners")
                self.selected_scanners = None
        else:
            self.selected_scanners = None  # None means run all scanners
        
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

    def _resolve_target_type(self) -> TargetType:
        """Resolve target type from environment or auto-detect."""
        target_type_env = os.getenv("TARGET_TYPE", "").strip().lower()
        if target_type_env:
            return TargetType(target_type_env)

        scan_target = os.getenv("SCAN_TARGET", "").strip()
        if scan_target:
            if scan_target.startswith(("http://", "https://")):
                os.environ["TARGET_TYPE"] = TargetType.WEBSITE.value
                return TargetType.WEBSITE

            # Detect host:port or IP for network scans
            host_candidate = scan_target
            port = None
            if ":" in scan_target and scan_target.count(":") == 1:
                host_candidate, port_part = scan_target.split(":", 1)
                if port_part.isdigit():
                    port = int(port_part)
            try:
                ipaddress.ip_address(host_candidate)
                os.environ["TARGET_TYPE"] = TargetType.NETWORK_HOST.value
                return TargetType.NETWORK_HOST
            except ValueError:
                if port is not None:
                    os.environ["TARGET_TYPE"] = TargetType.NETWORK_HOST.value
                    return TargetType.NETWORK_HOST

            # Default non-URL target: assume docker image
            os.environ["TARGET_TYPE"] = TargetType.DOCKER_IMAGE.value
            return TargetType.DOCKER_IMAGE

        os.environ["TARGET_TYPE"] = TargetType.LOCAL_CODE.value
        return TargetType.LOCAL_CODE
    
    def _get_conditions(self) -> Dict[str, Any]:
        """Get conditions for conditional scanners"""
        conditions = {}
        
        # Check for native mobile apps (only for code scans)
        if self.target_type in {TargetType.LOCAL_CODE, TargetType.GIT_REPO}:
            try:
                from scanner.core.project_detector import detect_native_app
                result = detect_native_app(str(self.target_path))
                conditions["IS_NATIVE"] = result.get("has_native", False)
            except Exception as e:
                self.log_message(f"[WARNING] Could not detect native apps: {e}")
                conditions["IS_NATIVE"] = False
        
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
        
        # Check if Python scanner class exists (new approach)
        python_scanner_class = scanner.python_class
        
        if python_scanner_class:
            # Use Python scanner class
            try:
                self.log_message(f"Using Python scanner class: {python_scanner_class}")
                module_path, class_name = python_scanner_class.rsplit(".", 1)
                module = __import__(module_path, fromlist=[class_name])
                scanner_class = getattr(module, class_name)
                
                # Build scanner arguments dynamically using inspect
                # This allows adding new scanners without modifying the orchestrator!
                scanner_kwargs = {
                    "target_path": str(self.target_path),
                    "results_dir": str(self.results_dir),
                    "log_file": str(self.log_file),
                }
                
                # Get the __init__ signature to see what parameters the scanner accepts
                sig = inspect.signature(scanner_class.__init__)
                param_names = set(sig.parameters.keys())
                
                # Remove 'self' from parameter names
                param_names.discard('self')
                
                # Für jeden Parameter in der Signatur: Suche passende env_var
                for param_name in param_names:
                    # Skip bereits gesetzte Parameter
                    if param_name in scanner_kwargs:
                        continue
                    
                    # Default values (nur wenn Parameter optional ist und nicht gefunden wurde)
                    if param_name not in scanner_kwargs:
                        sig_param = sig.parameters.get(param_name)
                        if sig_param and sig_param.default != inspect.Parameter.empty:
                            # Parameter hat Default-Wert, also optional - setze Defaults
                            if param_name == "scan_type":
                                scanner_kwargs[param_name] = "fs"
                            elif param_name == "zap_target":
                                scanner_kwargs[param_name] = "http://host.docker.internal:8000"
                            elif param_name == "startup_delay":
                                scanner_kwargs[param_name] = 25
                
                # Filter out None values (optional parameters that weren't provided)
                scanner_kwargs = {k: v for k, v in scanner_kwargs.items() if v is not None or k in ["target_path", "results_dir", "log_file"]}
                
                # CRITICAL FIX: Only pass parameters that actually exist in the scanner signature
                # Filter out any parameters that don't exist in the signature
                valid_kwargs = {}
                for param_name, param_value in scanner_kwargs.items():
                    if param_name in param_names:
                        valid_kwargs[param_name] = param_value
                    else:
                        # Log warning if we're trying to pass an invalid parameter
                        self.log_message(f"[WARNING] Skipping invalid parameter '{param_name}' for {scanner.name} (not in signature)")
                
                # Instantiate and run scanner
                scanner_instance = scanner_class(**valid_kwargs)
                
                success = scanner_instance.run()
                
                if success:
                    self.log_message(f"{scanner.name} completed successfully (exit code 0)")
                    self.scanner_statuses[scanner.name] = "SUCCESS"
                    self.step_registry.complete_step(scanner.name, f"{scanner.name} scan completed")
                    return True
                else:
                    self.log_message(f"[ORCHESTRATOR WARNING] {scanner.name} failed, but continuing scan...")
                    self.scanner_statuses[scanner.name] = "FAILED"
                    self.step_registry.fail_step(scanner.name, f"{scanner.name} scan failed")
                    # Don't set overall_success = False - allow scan to complete even if one scanner fails
                    # The scan will still generate a summary with partial results
                    return False  # Return False but continue with other scanners
                    
            except Exception as e:
                self.log_message(f"[ORCHESTRATOR WARNING] {scanner.name} Python scanner exception: {e}, but continuing scan...")
                self.scanner_statuses[scanner.name] = "FAILED"
                self.step_registry.fail_step(scanner.name, f"{scanner.name} scan error: {str(e)}")
                # Don't set overall_success = False - allow scan to complete even if one scanner fails
                return False  # Return False but continue with other scanners
        
        # Fallback to Bash script (legacy)
        script_path = Path(scanner.script_path)
        
        if not script_path.exists():
            self.log_message(f"[ORCHESTRATOR WARNING] {scanner.name} script not found: {script_path}, but continuing scan...")
            self.scanner_statuses[scanner.name] = "FAILED"
            self.step_registry.fail_step(scanner.name, f"Script not found: {script_path}")
            # Don't set overall_success = False - allow scan to complete even if one scanner fails
            return False  # Return False but continue with other scanners
        
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
                self.log_message(f"[ORCHESTRATOR WARNING] {scanner.name} failed with exit code {result.returncode}, but continuing scan...")
                self.scanner_statuses[scanner.name] = "FAILED"
                self.step_registry.fail_step(scanner.name, f"{scanner.name} scan failed")
                # Don't set overall_success = False - allow scan to complete even if one scanner fails
                return False  # Return False but continue with other scanners
                
        except subprocess.TimeoutExpired:
            self.log_message(f"[ORCHESTRATOR WARNING] {scanner.name} timed out after 1 hour, but continuing scan...")
            self.scanner_statuses[scanner.name] = "FAILED"
            self.step_registry.fail_step(scanner.name, f"{scanner.name} scan timed out")
            # Don't set overall_success = False - allow scan to complete even if one scanner fails
            return False  # Return False but continue with other scanners
        except Exception as e:
            self.log_message(f"[ORCHESTRATOR WARNING] {scanner.name} exception: {e}, but continuing scan...")
            self.scanner_statuses[scanner.name] = "FAILED"
            self.step_registry.fail_step(scanner.name, f"{scanner.name} scan error: {str(e)}")
            # Don't set overall_success = False - allow scan to complete even if one scanner fails
            return False  # Return False but continue with other scanners
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
            scan_type_value = self.scan_types[0].value if self.scan_types else "all"
            metadata = collect_scan_metadata(
                target_path=str(self.target_path),
                target_path_host=metadata_target_path_host,
                scan_type=scan_type_value,
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
    
    def _pre_register_all_steps(self):
        """
        Pre-register all steps as 'pending' BEFORE scan starts.
        This ensures frontend knows total_steps immediately.
        """
        # Check if Git Clone step already exists (written before orchestrator starts)
        git_clone_step = self.step_registry.get_step("Git Clone")
        has_git_clone = git_clone_step is not None
        
        if has_git_clone:
            self.log_message(f"Git Clone step already registered as Step {git_clone_step.number}")
        else:
            self.log_message("No Git Clone step found")
        
        # Get conditions and scanners
        conditions = self._get_conditions()
        scanners = ScannerRegistry.get_scanners_for_target(self.target_type, self.scan_types, conditions)
        
        # Filter by selected scanners if specified
        if self.selected_scanners:
            scanners = [s for s in scanners if s.name in self.selected_scanners]
        
        # Calculate total steps (with filtered scanners)
        total_steps = ScannerRegistry.get_total_steps(
            target_type=self.target_type,
            scan_types=self.scan_types,
            has_git_clone=has_git_clone,
            collect_metadata=self.collect_metadata,
            conditions=conditions
        )
        # Adjust total_steps if scanners are filtered
        if self.selected_scanners:
            all_scanners = ScannerRegistry.get_scanners_for_target(self.target_type, self.scan_types, conditions)
            total_steps = total_steps - (len(all_scanners) - len(scanners))
        
        self.log_message(f"Pre-registering {total_steps} steps (Git Clone: {has_git_clone}, Scanners: {len(scanners)}, Metadata: {self.collect_metadata})")
        
        # Pre-register all steps as 'pending' (except Git Clone which is already registered)
        # If Git Clone exists, step_counter is already set to 1, so Initialization will be Step 2
        # If no Git Clone, step_counter is 0, so Initialization will be Step 1
        
        # Register Initialization
        if "Initialization" not in self.step_registry.steps:
            self.step_registry.step_counter += 1
            init_step = Step(
                number=self.step_registry.step_counter,
                name="Initialization",
                status=StepStatus.PENDING,
                message="Initializing scan...",
                started_at=None,
                completed_at=None
            )
            self.step_registry.steps["Initialization"] = init_step
            self.step_registry._write_to_log(init_step)
        
        # Register all scanner steps (or selected ones)
        for scanner in scanners:
            if scanner.name not in self.step_registry.steps:
                self.step_registry.step_counter += 1
                scanner_step = Step(
                    number=self.step_registry.step_counter,
                    name=scanner.name,
                    status=StepStatus.PENDING,
                    message=f"Running {scanner.name} scan... (pending)",
                    started_at=None,
                    completed_at=None
                )
                self.step_registry.steps[scanner.name] = scanner_step
                self.step_registry._write_to_log(scanner_step)
        
        # Register Metadata Collection (if enabled)
        if self.collect_metadata and "Metadata Collection" not in self.step_registry.steps:
            self.step_registry.step_counter += 1
            metadata_step = Step(
                number=self.step_registry.step_counter,
                name="Metadata Collection",
                status=StepStatus.PENDING,
                message="Collecting metadata... (pending)",
                started_at=None,
                completed_at=None
            )
            self.step_registry.steps["Metadata Collection"] = metadata_step
            self.step_registry._write_to_log(metadata_step)
        
        # Register Completion
        if "Completion" not in self.step_registry.steps:
            self.step_registry.step_counter += 1
            completion_step = Step(
                number=self.step_registry.step_counter,
                name="Completion",
                status=StepStatus.PENDING,
                message="Finalizing scan... (pending)",
                started_at=None,
                completed_at=None
            )
            self.step_registry.steps["Completion"] = completion_step
            self.step_registry._write_to_log(completion_step)
        
        # Send initial update to frontend with all steps
        asyncio.create_task(self.step_registry._send_update())
        
        self.log_message(f"Pre-registered {len(self.step_registry.steps)} steps. Total: {self.step_registry.step_counter}")
    
    async def run_scan(self) -> int:
        """
        Run the complete scan
        
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        self.log_message("SimpleSecCheck Scan Started")
        scan_type_display = ",".join([s.value for s in self.scan_types]) if self.scan_types else "all"
        self.log_message(f"Scan Type(s): {scan_type_display}")
        self.log_message(f"Target Type: {self.target_type.value}")
        self.log_message(f"Target Path: {self.target_path}")
        self.log_message(f"Results Dir: {self.results_dir}")
        
        # CRITICAL: Pre-register ALL steps BEFORE starting scan
        # This ensures frontend knows total_steps immediately
        self._pre_register_all_steps()
        
        # Step: Initialization
        self.step_registry.start_step("Initialization", "Initializing scan...")
        self.log_message("--- Initialization ---")
        # Initialization logic here (if needed)
        self.step_registry.complete_step("Initialization", "Scan initialized")
        
        # Get scanners for this scan type
        conditions = self._get_conditions()
        scanners = ScannerRegistry.get_scanners_for_target(self.target_type, self.scan_types, conditions)
        
        # Filter by selected scanners if specified
        if self.selected_scanners:
            scanners = [s for s in scanners if s.name in self.selected_scanners]
            self.log_message(f"Filtered to {len(scanners)} selected scanners: {', '.join([s.name for s in scanners])}")
        else:
            self.log_message(f"Running all {len(scanners)} scanners for target {self.target_type.value}")
        
        # Run all scanners (or selected ones)
        for scanner in scanners:
            await self._run_scanner(scanner)
        
        # Collect metadata (if enabled)
        if self.collect_metadata:
            await self._collect_metadata()
        
        # Completion
        self.step_registry.start_step("Completion", "Finalizing scan...")
        
        # Generate HTML report
        self._generate_html_report()
        
        # Always complete successfully if at least some scanners ran
        # (even if some failed, we still want a summary)
        self.log_message("SimpleSecCheck Scan Completed")
        if self.overall_success:
            self.step_registry.complete_step("Completion", "Scan completed successfully")
        else:
            self.step_registry.complete_step("Completion", "Scan completed with some errors")
        # Always return 0 to allow summary generation
        return 0
    
    def _generate_html_report(self):
        """Generate HTML report after scan completion"""
        html_report_script = self.base_dir / "scanner" / "reporting" / "generate-html-report.py"
        html_report_output = self.results_dir / "security-summary.html"
        
        if not html_report_script.exists():
            self.log_message(f"[WARNING] HTML report script not found: {html_report_script}")
            return
        
        self.log_message(f"Generating HTML report: {html_report_output}")
        
        # Set environment variables for the script
        import os
        env = os.environ.copy()
        env["OUTPUT_FILE"] = str(html_report_output)
        env["RESULTS_DIR"] = str(self.results_dir)
        if self.scan_types:
            env["SCAN_TYPE"] = self.scan_types[0].value
        env["TARGET_TYPE"] = self.target_type.value
        env["PYTHONUNBUFFERED"] = "1"
        
        try:
            result = subprocess.run(
                ["python3", str(html_report_script)],
                env=env,
                cwd=str(self.base_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=300  # 5 minute timeout for report generation
            )
            
            # Write output to log
            if result.stdout:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(result.stdout)
            
            if result.returncode == 0:
                self.log_message(f"HTML report generated successfully: {html_report_output}")
            else:
                self.log_message(f"[WARNING] HTML report generation failed with exit code {result.returncode} (non-critical)")
        except subprocess.TimeoutExpired:
            self.log_message("[WARNING] HTML report generation timed out (non-critical)")
        except Exception as e:
            self.log_message(f"[WARNING] HTML report generation error: {e} (non-critical)")


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
