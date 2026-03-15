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
from datetime import datetime

# Add scanner to path for imports
if "/app" not in sys.path:
    sys.path.insert(0, "/app")
if "/app/scanner" not in sys.path:
    sys.path.insert(0, "/app/scanner")

# Ensure scanner auto-discovery runs before registry usage
# Import plugins to auto-register all scanners
try:
    import scanner.plugins  # noqa: F401 - This triggers auto-registration via __init__.py
except Exception as e:
    print(f"[Orchestrator] Warning: Could not import scanner.plugins: {e}")
    # Fallback to old scanners import
    try:
        import scanner.scanners  # noqa: F401
    except Exception:
        pass

try:
    from scanner.core.scanner_registry import ScannerRegistry, ScanType, TargetType, Scanner
    from scanner.core.step_registry import StepRegistry, StepStatus, Step
    from scanner.core.step_definitions import StepDefinitionsRegistry, StepType
except ImportError:
    # Fallback for direct execution
    from core.scanner_registry import ScannerRegistry, ScanType, TargetType, Scanner
    from core.step_registry import StepRegistry, StepStatus, Step
    from core.step_definitions import StepDefinitionsRegistry, StepType


class ScanOrchestrator:
    """Modern orchestrator using Scanner Registry and Step Registry"""
    
    def __init__(self, step_registry: StepRegistry):
        """
        Initialize orchestrator
        
        Args:
            step_registry: Step registry for step tracking
        """
        self.step_registry = step_registry
        self.base_dir = Path("/app")
        self.tools_dir = self.base_dir / "scripts" / "tools"
        self.target_path = Path(os.getenv("TARGET_PATH_IN_CONTAINER", "/target"))
        
        # Get scan_id from step_registry (set by main() or worker)
        # step_registry.scan_id is the source of truth - it's set in main() before creating orchestrator
        scan_id = step_registry.scan_id
        
        # Use results_dir from step_registry (already scan-specific: /app/results/{scan_id})
        # This ensures consistency - step_registry and orchestrator use the same directory
        self.results_dir = step_registry.results_dir
        
        # Create subdirectories for organized structure
        self.metadata_dir = self.results_dir / "metadata"
        self.summary_dir = self.results_dir / "summary"
        self.tools_dir_results = self.results_dir / "tools"
        self.logs_dir = self.results_dir / "logs"
        self.log_file = self.logs_dir / "scan.log"
        
        # Ensure all directories exist
        for dir_path in [self.results_dir, self.metadata_dir, self.summary_dir, self.tools_dir_results, self.logs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Scan configuration
        scan_type_env = os.getenv("SCAN_TYPE")
        if not scan_type_env:
            raise ValueError(
                "SCAN_TYPE environment variable is required but not set! "
                "Backend must set scan_type and Worker must pass it to container via SCAN_TYPE env var."
            )
        try:
            self.scan_types = [ScanType(scan_type_env)]
        except ValueError as e:
            raise ValueError(
                f"Invalid SCAN_TYPE value: '{scan_type_env}'. "
                f"Valid values: {[s.value for s in ScanType]}. "
                f"Backend must set a valid scan_type."
            ) from e
        self.target_type = self._resolve_target_type()
        
        # collect_metadata
        collect_metadata_env = os.getenv("COLLECT_METADATA")
        if collect_metadata_env is None:
            raise ValueError(
                "COLLECT_METADATA environment variable is required but not set! "
                "Backend must set collect_metadata and Worker must pass it to container via COLLECT_METADATA env var."
            )
        self.collect_metadata = collect_metadata_env.lower() == "true"
        
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
        """Resolve target type from environment variable.
        
        Backend sets TARGET_TYPE environment variable.
        Worker passes TARGET_TYPE from queue message to container.
        """
        target_type_env = os.getenv("TARGET_TYPE", "").strip()
        if not target_type_env:
            raise ValueError(
                "TARGET_TYPE environment variable is required but not set! "
                "Backend must determine target_type (e.g., git_repo, local_mount, etc.) "
                "and Worker must pass it to container via TARGET_TYPE env var."
            )
        
        try:
            return TargetType(target_type_env.lower())
        except ValueError as e:
            raise ValueError(
                f"Invalid TARGET_TYPE value: '{target_type_env}'. "
                f"Valid values: {[t.value for t in TargetType]}. "
                f"Backend must set a valid target_type."
            ) from e
    
    def _get_conditions(self) -> Dict[str, Any]:
        """Get conditions for conditional scanners"""
        conditions = {}
        
        # Check for native mobile apps (only for code scans)
        if self.target_type in {TargetType.LOCAL_MOUNT, TargetType.GIT_REPO}:
            try:
                from scanner.core.project_detector import detect_native_app
                result = detect_native_app(str(self.target_path))
                conditions["IS_NATIVE"] = result.get("has_native", False)
            except Exception as e:
                self.log_message(f"[WARNING] Could not detect native apps: {e}")
                conditions["IS_NATIVE"] = False
        
        return conditions
    
    async def _run_git_clone(self) -> bool:
        """Clone Git repository for git_repo target type.
        
        No fallbacks - only uses provided data:
        - SCAN_TARGET: Git repository URL (required)
        - GIT_BRANCH: Branch name (optional, only used if provided)
        """
        scan_target = os.getenv("SCAN_TARGET", "").strip()
        if not scan_target:
            error_msg = "SCAN_TARGET environment variable is required for git_repo target type but not set. Backend must set target_url and Worker must pass it to container via SCAN_TARGET env var."
            self.log_message(f"[ERROR] {error_msg}")
            self.step_registry.start_step("Git Clone", "Git clone failed")
            self.step_registry.complete_step("Git Clone", error_msg)
            raise ValueError(error_msg)
        
        # Get branch from environment variable (optional - only use if provided)
        git_branch = os.getenv("GIT_BRANCH", "").strip()
        
        self.step_registry.start_step("Git Clone", f"Cloning {scan_target}...")
        self.log_message("--- Git Clone ---")
        self.log_message(f"Repository: {scan_target}")
        if git_branch:
            self.log_message(f"Branch: {git_branch}")
        self.log_message(f"Target Path: {self.target_path}")
        
        try:
            # Ensure target directory exists
            self.target_path.mkdir(parents=True, exist_ok=True)
            
            # Clone repository
            clone_cmd = ["git", "clone", "--depth", "1"]
            if git_branch:
                clone_cmd.extend(["-b", git_branch])
            clone_cmd.extend([scan_target, str(self.target_path)])
            
            self.log_message(f"Executing: {' '.join(clone_cmd)}")
            
            result = subprocess.run(
                clone_cmd,
                capture_output=True,
                text=True,
                timeout=300,
                check=False
            )
            
            if result.returncode == 0:
                branch_info = f" (branch: {git_branch})" if git_branch else ""
                self.log_message(f"Successfully cloned repository to {self.target_path}{branch_info}")
                self.step_registry.complete_step("Git Clone", f"Repository cloned successfully{branch_info}")
                return True
            else:
                error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
                self.log_message(f"[ERROR] Git clone failed: {error_msg}")
                self.step_registry.complete_step("Git Clone", f"Git clone failed: {error_msg}")
                return False
                
        except subprocess.TimeoutExpired:
            error_msg = "Git clone timed out after 5 minutes"
            self.log_message(f"[ERROR] {error_msg}")
            self.step_registry.complete_step("Git Clone", error_msg)
            return False
        except Exception as e:
            error_msg = f"Git clone error: {e}"
            self.log_message(f"[ERROR] {error_msg}")
            self.step_registry.complete_step("Git Clone", error_msg)
            return False
    
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
        
        # Create scanner-specific directory in tools/
        scanner_name_lower = scanner.name.lower()
        scanner_dir = self.tools_dir_results / scanner_name_lower
        scanner_dir.mkdir(parents=True, exist_ok=True)
        scanner_log_file = scanner_dir / "log"
        
        # Prepare environment
        env = os.environ.copy()
        env["TARGET_PATH"] = str(self.target_path)
        env["RESULTS_DIR"] = str(scanner_dir)  # Scanner writes to its own directory
        env["LOG_FILE"] = str(scanner_log_file)  # Scanner has its own log
        
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
                    "results_dir": str(scanner_dir),  # Scanner-specific directory
                    "log_file": str(scanner_log_file),  # Scanner-specific log
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
            scan_type_value = self.scan_types[0].value
            metadata = collect_scan_metadata(
                target_path=str(self.target_path),
                target_path_host=metadata_target_path_host,
                scan_type=scan_type_value,
                results_dir=str(self.metadata_dir),  # Save to metadata/ subdirectory
                finding_policy=finding_policy,
                ci_mode=ci_mode
            )
            
            # Save metadata to metadata/scan.json
            if save_metadata(metadata, str(self.metadata_dir)):
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
        Uses StepDefinitionsRegistry - NO HARDCODED STEPS!
        """
        # Get conditions and scanners
        conditions = self._get_conditions()
        scanners = ScannerRegistry.get_scanners_for_target(self.target_type, self.scan_types, conditions)
        
        # Filter by selected scanners if specified
        if self.selected_scanners:
            scanners = [s for s in scanners if s.name in self.selected_scanners]
        
        # Get step definitions from registry (NO HARDCODING!)
        step_definitions = StepDefinitionsRegistry.get_steps_for_scan(
            target_type=self.target_type.value,
            collect_metadata=self.collect_metadata,
            scanner_count=len(scanners)
        )
        
        total_steps = len(step_definitions) + len(scanners)
        self.log_message(f"Pre-registering {total_steps} steps from registry (Step Definitions: {len(step_definitions)}, Scanners: {len(scanners)})")
        
        # Register all step definitions from registry
        for step_def in step_definitions:
            if step_def.name not in self.step_registry.steps:
                self.step_registry.step_counter += 1
                step = Step(
                    number=self.step_registry.step_counter,
                    name=step_def.name,
                    status=StepStatus.PENDING,
                    message=f"{step_def.name}... (pending)",
                    started_at=None,
                    completed_at=None
                )
                self.step_registry.steps[step_def.name] = step
                self.step_registry._write_to_log(step)
        
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
        scan_type_display = ",".join([s.value for s in self.scan_types])
        self.log_message(f"Scan Type(s): {scan_type_display}")
        self.log_message(f"Target Type: {self.target_type.value}")
        self.log_message(f"Target Path: {self.target_path}")
        self.log_message(f"Results Dir: {self.results_dir}")
        
        # CRITICAL: Pre-register ALL steps BEFORE starting scan
        # This ensures frontend knows total_steps immediately
        self._pre_register_all_steps()
        
        # Get step definitions from registry (NO HARDCODING!)
        conditions = self._get_conditions()
        scanners = ScannerRegistry.get_scanners_for_target(self.target_type, self.scan_types, conditions)
        if self.selected_scanners:
            scanners = [s for s in scanners if s.name in self.selected_scanners]
        
        step_definitions = StepDefinitionsRegistry.get_steps_for_scan(
            target_type=self.target_type.value,
            collect_metadata=self.collect_metadata,
            scanner_count=len(scanners)
        )
        
        # Execute steps in order from registry
        for step_def in step_definitions:
            if step_def.step_type == StepType.GIT_CLONE:
                await self._run_git_clone()
            elif step_def.step_type == StepType.INITIALIZATION:
                self.step_registry.start_step("Initialization", "Initializing scan...")
                self.log_message("--- Initialization ---")
                self.step_registry.complete_step("Initialization", "Scan initialized")
            elif step_def.step_type == StepType.METADATA_COLLECTION:
                await self._collect_metadata()
            elif step_def.step_type == StepType.COMPLETION:
                self.step_registry.start_step("Completion", "Finalizing scan...")
                self._generate_html_report()
                self.log_message("SimpleSecCheck Scan Completed")
                if self.overall_success:
                    self.step_registry.complete_step("Completion", "Scan completed successfully")
                else:
                    self.step_registry.complete_step("Completion", "Scan completed with some errors")
        
        # Run scanners (they are registered as steps but executed separately)
        if self.selected_scanners:
            self.log_message(f"Filtered to {len(scanners)} selected scanners: {', '.join([s.name for s in scanners])}")
        else:
            self.log_message(f"Running all {len(scanners)} scanners for target {self.target_type.value}")
            if len(scanners) == 0:
                self.log_message(f"[WARNING] No scanners found! Check scanner registration and capabilities.")
        
        for scanner in scanners:
            await self._run_scanner(scanner)
        
        # Always return 0 to allow summary generation
        return 0
    
    def _generate_html_report(self):
        """Generate HTML report after scan completion"""
        html_report_script = self.base_dir / "scanner" / "output" / "generate-html-report.py"
        html_report_output = self.summary_dir / "summary.html"  # Save to summary/ subdirectory
        
        if not html_report_script.exists():
            self.log_message(f"[WARNING] HTML report script not found: {html_report_script}")
            return
        
        self.log_message(f"Generating HTML report: {html_report_output}")
        
        # Set environment variables for the script
        import os
        env = os.environ.copy()
        env["OUTPUT_FILE"] = str(html_report_output)
        env["RESULTS_DIR"] = str(self.results_dir)  # Pass base results_dir for script to find tools/
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


def _get_asset_last_updated(container_path: str) -> Optional[Dict[str, Any]]:
    """
    Get last updated timestamp for an asset by checking filesystem.
    
    Returns dict with updated_at (ISO string), age_seconds, and age_human,
    or None if asset path doesn't exist or can't be read.
    """
    from datetime import datetime
    
    try:
        asset_path = Path(container_path)
        if not asset_path.exists():
            return None
        
        # Get mtime of directory or newest file in directory
        if asset_path.is_file():
            mtime = asset_path.stat().st_mtime
        elif asset_path.is_dir():
            # Find newest file in directory (recursive)
            newest_mtime = 0
            try:
                for file_path in asset_path.rglob("*"):
                    if file_path.is_file():
                        file_mtime = file_path.stat().st_mtime
                        if file_mtime > newest_mtime:
                            newest_mtime = file_mtime
                mtime = newest_mtime if newest_mtime > 0 else asset_path.stat().st_mtime
            except (PermissionError, OSError):
                # Fallback to directory mtime if we can't read files
                mtime = asset_path.stat().st_mtime
        else:
            return None
        
        # Calculate age
        updated_at = datetime.fromtimestamp(mtime)
        now = datetime.now()
        age_delta = now - updated_at
        age_seconds = int(age_delta.total_seconds())
        
        # Format human-readable age
        if age_seconds < 60:
            age_human = f"{age_seconds}s ago"
        elif age_seconds < 3600:
            age_human = f"{age_seconds // 60}m ago"
        elif age_seconds < 86400:
            age_human = f"{age_seconds // 3600}h ago"
        elif age_seconds < 604800:
            age_human = f"{age_seconds // 86400}d ago"
        else:
            age_human = f"{age_seconds // 604800}w ago"
        
        return {
            "updated_at": updated_at.isoformat(),
            "age_seconds": age_seconds,
            "age_human": age_human
        }
    except Exception:
        # If anything fails, return None (asset not found or can't be read)
        return None


async def list_scanners():
    """List all available scanners with their capabilities and assets."""
    import json
    import sys
    from pathlib import Path
    
    try:
        from scanner.core.scanner_registry import ScannerRegistry, ScanType
        from scanner.core.scanner_assets.manager import ScannerAssetsManager
        
        # Trigger auto-discovery
        import scanner.plugins  # noqa: F401
        
        scanners = ScannerRegistry.get_all_scanners()
        
        # Load assets from manifests
        scanners_root = Path("/app/scanner/plugins")
        assets_manager = None
        manifests = {}
        if scanners_root.exists():
            try:
                assets_manager = ScannerAssetsManager(scanners_root)
                manifests = assets_manager.load_manifests()
            except Exception as e:
                # Assets loading is optional - continue without them
                pass
        
        scanner_list = []
        for scanner_obj in scanners:
            # Extract scan types from capabilities
            scan_types = []
            for cap in scanner_obj.capabilities:
                scan_type = cap.scan_type.value
                # Map to frontend scan types
                if scan_type in ["code", "dependency", "secrets", "config"]:
                    scan_types.append("code")
                elif scan_type in ["image", "container"]:
                    scan_types.append("image")
                elif scan_type == "website":
                    scan_types.append("website")
                elif scan_type == "network":
                    scan_types.append("network")
            
            # Remove duplicates
            scan_types = list(set(scan_types))
            
            scanner_data = {
                "name": scanner_obj.name,
                "scan_types": scan_types,
                "priority": scanner_obj.priority,
                "requires_condition": scanner_obj.requires_condition,
                "enabled": scanner_obj.enabled
            }
            
            # Add assets if available
            if manifests and scanner_obj.name.lower() in manifests:
                manifest = manifests[scanner_obj.name.lower()]
                assets = []
                for asset in manifest.assets:
                    asset_dict = {
                        "id": asset.id,
                        "type": asset.type,
                        "description": asset.description,
                        "mount": {
                            "host_subpath": asset.mount.host_subpath,
                            "container_path": asset.mount.container_path,
                        }
                    }
                    if asset.update:
                        asset_dict["update"] = {
                            "enabled": asset.update.enabled,
                            "command": asset.update.command,
                        }
                    else:
                        asset_dict["update"] = None
                    
                    # Calculate last_updated from filesystem
                    last_updated = _get_asset_last_updated(asset.mount.container_path)
                    asset_dict["last_updated"] = last_updated
                    
                    assets.append(asset_dict)
                scanner_data["assets"] = assets
            
            scanner_list.append(scanner_data)
        
        # Sort by priority
        scanner_list.sort(key=lambda x: x["priority"])
        
        # Output as JSON
        print(json.dumps({"scanners": scanner_list}, indent=2))
        sys.exit(0)
        
    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2), file=sys.stderr)
        sys.exit(1)


async def main():
    """Main entry point for orchestrator"""
    import sys
    
    # Check for --list flag
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        await list_scanners()
        return
    
    # Only run scan if explicitly requested via SCAN_ID or SCAN_TARGET
    # TARGET_PATH_IN_CONTAINER alone is not enough - it's just a mount point
    scan_id = os.getenv("SCAN_ID", "")
    scan_target = os.getenv("SCAN_TARGET", "")
    
    # If no scan parameters are provided, exit without running scan
    if not scan_id and not scan_target:
        # Silent exit - container is just running, no scan requested
        sys.exit(0)
    
    # CRITICAL: SCAN_ID is REQUIRED - do not generate fallback!
    # Worker MUST provide SCAN_ID via environment variable
    # Without SCAN_ID, we cannot create scan-specific directories
    if not scan_id:
        print("[Orchestrator] ERROR: SCAN_ID environment variable is required but not set!")
        print("[Orchestrator] Worker must provide SCAN_ID when starting scanner container.")
        print("[Orchestrator] Cannot create scan-specific results directory without SCAN_ID.")
        sys.exit(1)
    
    # Get base results directory (orchestrator will append scan_id)
    base_results_dir = Path(os.getenv("RESULTS_DIR_IN_CONTAINER", "/app/results"))
    
    # Build scan-specific results directory
    # CRITICAL: Always use scan_id to create isolated directory structure
    # Results directory structure: /app/results/{scan_id}/logs/steps.log
    # This keeps results/ clean - only contains {scan_id}/ folders, nothing else!
    scan_results_dir = base_results_dir / scan_id
    
    # Create step registry (without WebSocket manager for now - will be added in integration)
    # Pass scan-specific directory to StepRegistry
    step_registry = StepRegistry(scan_id, scan_results_dir, websocket_manager=None)
    
    # Create orchestrator
    orchestrator = ScanOrchestrator(step_registry)
    
    # Run scan
    exit_code = await orchestrator.run_scan()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
