"""
Modern Python Orchestrator
Replaces the legacy shell-based orchestrator with dynamic, registry-based scanner execution
No hardcoded steps, no log parsing - direct step communication!
"""
import json
import os
import subprocess
import sys
import inspect
from pathlib import Path
from typing import Optional, Dict, Any, List
import ipaddress
from datetime import datetime

# Add scanner to path for imports
if "/app" not in sys.path:
    sys.path.insert(0, "/app")
if "/app/scanner" not in sys.path:
    sys.path.insert(0, "/app/scanner")

# Ensure scanner auto-discovery runs before registry usage
# Import plugins to auto-register all scanners
import scanner.plugins  # noqa: F401 - This triggers auto-registration via __init__.py

from scanner.core.scanner_registry import ScannerRegistry, ScanType, TargetType, Scanner
from scanner.core.step_registry import StepRegistry, StepStatus, Step, SubStepType
from scanner.core.step_definitions import StepDefinitionsRegistry, StepType
from scanner.core.base_scanner import set_global_step_registry
from scanner.core import scan_checkpoint as scan_cp


# Single Source of Truth: Mapping from frontend scan_type to scanner scan_types
def get_scanner_scan_types_for_frontend_type(frontend_scan_type: str) -> List[ScanType]:
    """
    Map frontend scan_type to scanner scan_types.
    
    When user selects "code" scan, we want to include:
    - CODE scanners (semgrep, codeql, etc.)
    - DEPENDENCY scanners (safety, npm_audit, etc.)
    - SECRETS scanners (gitleaks, trufflehog, etc.)
    - CONFIG scanners (terraform, checkov, etc.)
    
    This is the SINGLE SOURCE OF TRUTH for this mapping.
    """
    if frontend_scan_type == "code":
        return [ScanType.CODE, ScanType.DEPENDENCY, ScanType.SECRETS, ScanType.CONFIG]
    else:
        return [ScanType(frontend_scan_type)]


def map_scanner_scan_type_to_frontend_type(scanner_scan_type: str) -> str:
    """
    Map scanner scan_type to frontend scan_type for display.
    
    This is the SINGLE SOURCE OF TRUTH for reverse mapping.
    """
    if scanner_scan_type in ["code", "dependency", "secrets", "config"]:
        return "code"
    elif scanner_scan_type in ["image", "container"]:
        return "image"
    elif scanner_scan_type == "website":
        return "website"
    elif scanner_scan_type == "network":
        return "network"
    else:
        return scanner_scan_type


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
            # Use single source of truth for mapping
            self.scan_types = get_scanner_scan_types_for_frontend_type(scan_type_env)
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
        
        # Selected scanners: If provided, use them. Otherwise, auto-detect based on scan_type
        selected_scanners_json = os.getenv("SELECTED_SCANNERS")
        if selected_scanners_json:
            import json
            try:
                self.selected_scanners = set(json.loads(selected_scanners_json))
                self.log_message(f"Using explicitly selected scanners: {', '.join(sorted(self.selected_scanners))}")
            except (json.JSONDecodeError, TypeError) as e:
                raise ValueError(
                    f"Invalid SELECTED_SCANNERS format: {selected_scanners_json}. "
                    f"Expected JSON array of scanner names. Error: {e}"
                )
        else:
            # Auto-detect scanners based on scan_type (no fallback - this is a feature!)
            self.selected_scanners = None  # None means auto-detect based on scan_type
            self.log_message(f"No SELECTED_SCANNERS provided, will auto-detect scanners for scan_type={scan_type_env}")
        
        # Overall success tracking
        self.overall_success = True
        self.scanner_statuses: Dict[str, str] = {}
        # DB admin overrides merged at enqueue (manifest + scanner_tool_settings)
        raw_ov = os.getenv("SCANNER_TOOL_OVERRIDES_JSON", "").strip()
        self._tool_overrides: Dict[str, Any] = {}
        if raw_ov:
            try:
                self._tool_overrides = json.loads(raw_ov)
                if not isinstance(self._tool_overrides, dict):
                    self._tool_overrides = {}
            except (json.JSONDecodeError, TypeError):
                self._tool_overrides = {}
    
    def _tools_key_for_override(self, scanner: Scanner) -> str:
        """Merge map is keyed by tools_key (same as scanner_tool_settings.scanner_key)."""
        tk = (scanner.tools_key or "").strip().lower()
        return tk if tk else ""

    def _override_for_scanner(self, scanner: Scanner) -> Dict[str, Any]:
        tk = self._tools_key_for_override(scanner)
        o = self._tool_overrides.get(tk) or {}
        return o if isinstance(o, dict) else {}

    def _scanner_admin_enabled(self, scanner: Scanner) -> bool:
        if self._override_for_scanner(scanner).get("enabled") is False:
            return False
        return True

    def _merged_timeout(self, scanner: Scanner) -> int:
        o = self._override_for_scanner(scanner)
        t = o.get("timeout")
        if t is not None:
            try:
                ti = int(t)
                if ti > 0:
                    return ti
            except (TypeError, ValueError):
                pass
        if scanner.timeout and scanner.timeout > 0:
            return int(scanner.timeout)
        return 900

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
        if self.target_type in {TargetType.LOCAL_MOUNT, TargetType.GIT_REPO, TargetType.UPLOADED_CODE}:
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
        Run a scanner via its registered Python class.

        Args:
            scanner: Scanner definition

        Returns:
            True if successful, False otherwise
        """
        # Start step
        self.step_registry.start_step(scanner.name, f"Running {scanner.name} scan...")
        timeout_sec = self._merged_timeout(scanner)
        os.environ["SCANNER_TIMEOUT_SECONDS"] = str(timeout_sec)
        ov = self._override_for_scanner(scanner)
        env_backup: Dict[str, Optional[str]] = {}
        for k, v in (ov.get("env") or {}).items():
            if not k or v is None:
                continue
            env_backup[k] = os.environ.get(k)
            os.environ[str(k)] = str(v)
        try:
            self.log_message(f"--- Orchestrating {scanner.name} Scan ---")
            if not scanner.tools_key:
                self.log_message(f"[ORCHESTRATOR] Scanner {scanner.name} has no tools_key in registry, skipping.")
                self.scanner_statuses[scanner.name] = "FAILED"
                self.step_registry.fail_step(scanner.name, "No tools_key in registry")
                return False
            if not scanner.python_class:
                self.log_message(
                    f"[ORCHESTRATOR] Scanner {scanner.name} has no python_class, skipping."
                )
                self.scanner_statuses[scanner.name] = "FAILED"
                self.step_registry.fail_step(scanner.name, "No python_class on scanner")
                return False
            scanner_dir = self.tools_dir_results / scanner.tools_key
            scanner_dir.mkdir(parents=True, exist_ok=True)
            scanner_log_file = scanner_dir / "log"

            python_scanner_class = scanner.python_class
            try:
                self.log_message(f"Using Python scanner class: {python_scanner_class}")
                module_path, class_name = python_scanner_class.rsplit(".", 1)
                module = __import__(module_path, fromlist=[class_name])
                scanner_class = getattr(module, class_name)

                scanner_kwargs = {
                    "target_path": str(self.target_path),
                    "results_dir": str(scanner_dir),
                    "log_file": str(scanner_log_file),
                    "step_name": scanner.name,
                }

                sig = inspect.signature(scanner_class.__init__)
                param_names = set(sig.parameters.keys())
                param_names.discard("self")

                for param_name in param_names:
                    if param_name in scanner_kwargs:
                        continue
                    if param_name not in scanner_kwargs:
                        sig_param = sig.parameters.get(param_name)
                        if sig_param and sig_param.default != inspect.Parameter.empty:
                            if param_name == "scan_type":
                                scanner_kwargs[param_name] = "fs"
                            elif param_name == "scan_target":
                                scanner_kwargs[param_name] = os.getenv(
                                    "SCAN_TARGET", "http://host.docker.internal:8000"
                                )
                            elif param_name == "startup_delay":
                                scanner_kwargs[param_name] = 25

                scanner_kwargs = {
                    k: v
                    for k, v in scanner_kwargs.items()
                    if v is not None or k in ["target_path", "results_dir", "log_file"]
                }

                valid_kwargs = {}
                for param_name, param_value in scanner_kwargs.items():
                    if param_name in param_names:
                        valid_kwargs[param_name] = param_value
                    else:
                        self.log_message(
                            f"[WARNING] Skipping invalid parameter '{param_name}' for {scanner.name} (not in signature)"
                        )

                scanner_instance = scanner_class(**valid_kwargs)
                success = scanner_instance.run()

                scanner_dir = self.tools_dir_results / scanner.tools_key
                status_file = scanner_dir / "status.json"
                if status_file.exists():
                    try:
                        data = json.loads(status_file.read_text(encoding="utf-8"))
                        if data.get("status") == "skipped":
                            msg = data.get("message", f"{scanner.name} skipped")
                            self.log_message(f"{scanner.name} skipped: {msg}")
                            self.scanner_statuses[scanner.name] = "SKIPPED"
                            self.step_registry.skip_step(scanner.name, msg)
                            return False
                    except Exception:
                        pass

                if success:
                    self.log_message(f"{scanner.name} completed successfully (exit code 0)")
                    self.scanner_statuses[scanner.name] = "SUCCESS"
                    self.step_registry.complete_step(scanner.name, f"{scanner.name} scan completed")
                    return True
                self.log_message(f"[ORCHESTRATOR WARNING] {scanner.name} failed, but continuing scan...")
                self.scanner_statuses[scanner.name] = "FAILED"
                self.step_registry.fail_step(scanner.name, f"{scanner.name} scan failed")
                return False

            except Exception as e:
                self.log_message(
                    f"[ORCHESTRATOR WARNING] {scanner.name} Python scanner exception: {e}, but continuing scan..."
                )
                self.scanner_statuses[scanner.name] = "FAILED"
                self.step_registry.fail_step(scanner.name, f"{scanner.name} scan error: {str(e)}")
                return False
        finally:
            for k, old in env_backup.items():
                if old is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = old
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
    
    async def _collect_artifacts(self):
        """Collect all scan artifacts (SARIF, JSON, HTML, logs) for CI/CD integration"""
        import json
        import shutil
        
        self.log_message("--- Collecting Artifacts ---")
        self.step_registry.start_step("Artifact Collection", "Collecting scan artifacts...")
        
        # Create artifacts directory
        artifacts_dir = self.results_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        artifacts_manifest = {
            "scan_id": self.step_registry.scan_id,
            "collected_at": datetime.now().isoformat(),
            "artifacts": {
                "sarif": [],
                "json": [],
                "html": [],
                "logs": []
            }
        }
        
        try:
            # Collect SARIF files
            self.step_registry.start_substep("Artifact Collection", "Collecting SARIF files...", SubStepType.ACTION)
            sarif_files = list(self.results_dir.rglob("*.sarif"))
            sarif_count = 0
            for sarif_file in sarif_files:
                if sarif_file.is_file() and sarif_file.stat().st_size > 0:
                    dest = artifacts_dir / "sarif" / sarif_file.name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(sarif_file, dest)
                    artifacts_manifest["artifacts"]["sarif"].append({
                        "name": sarif_file.name,
                        "path": str(dest.relative_to(self.results_dir)),
                        "size": sarif_file.stat().st_size
                    })
                    sarif_count += 1
            self.step_registry.complete_substep("Collecting SARIF files...", f"Collected {sarif_count} SARIF file(s)")
            
            # Collect JSON files
            self.step_registry.start_substep("Artifact Collection", "Collecting JSON reports...", SubStepType.ACTION)
            json_files = list(self.results_dir.rglob("report.json"))
            json_count = 0
            for json_file in json_files:
                if json_file.is_file() and json_file.stat().st_size > 0:
                    # Preserve directory structure
                    rel_path = json_file.relative_to(self.results_dir)
                    dest = artifacts_dir / "json" / rel_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(json_file, dest)
                    artifacts_manifest["artifacts"]["json"].append({
                        "name": json_file.name,
                        "path": str(dest.relative_to(self.results_dir)),
                        "size": json_file.stat().st_size
                    })
                    json_count += 1
            self.step_registry.complete_substep("Collecting JSON reports...", f"Collected {json_count} JSON file(s)")
            
            # Collect HTML files
            self.step_registry.start_substep("Artifact Collection", "Collecting HTML reports...", SubStepType.ACTION)
            html_files = list(self.results_dir.rglob("*.html"))
            html_count = 0
            for html_file in html_files:
                if html_file.is_file() and html_file.stat().st_size > 0:
                    rel_path = html_file.relative_to(self.results_dir)
                    dest = artifacts_dir / "html" / rel_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(html_file, dest)
                    artifacts_manifest["artifacts"]["html"].append({
                        "name": html_file.name,
                        "path": str(dest.relative_to(self.results_dir)),
                        "size": html_file.stat().st_size
                    })
                    html_count += 1
            self.step_registry.complete_substep("Collecting HTML reports...", f"Collected {html_count} HTML file(s)")
            
            # Collect log files
            self.step_registry.start_substep("Artifact Collection", "Collecting log files...", SubStepType.ACTION)
            log_files = list(self.logs_dir.rglob("*.log"))
            log_count = 0
            for log_file in log_files:
                if log_file.is_file() and log_file.stat().st_size > 0:
                    rel_path = log_file.relative_to(self.results_dir)
                    dest = artifacts_dir / "logs" / rel_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(log_file, dest)
                    artifacts_manifest["artifacts"]["logs"].append({
                        "name": log_file.name,
                        "path": str(dest.relative_to(self.results_dir)),
                        "size": log_file.stat().st_size
                    })
                    log_count += 1
            self.step_registry.complete_substep("Collecting log files...", f"Collected {log_count} log file(s)")
            
            # Save artifacts manifest
            manifest_path = artifacts_dir / "artifacts.json"
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(artifacts_manifest, f, indent=2)
            
            total_artifacts = sarif_count + json_count + html_count + log_count
            self.log_message(f"Artifact collection completed: {total_artifacts} artifact(s) collected")
            self.step_registry.complete_step("Artifact Collection", f"Collected {total_artifacts} artifact(s) (SARIF: {sarif_count}, JSON: {json_count}, HTML: {html_count}, Logs: {log_count})")
            
        except Exception as e:
            self.log_message(f"[ERROR] Error collecting artifacts: {e}")
            self.step_registry.complete_step("Artifact Collection", f"Artifact collection completed (with errors: {e})")
    
    def _pre_register_all_steps(self):
        """
        Pre-register all steps as 'pending' BEFORE scan starts.
        Uses StepDefinitionsRegistry - NO HARDCODED STEPS!
        Order matches execution: Git Clone, Initialization, [Metadata], scanners..., Artifact Collection, Completion.
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
        
        # Split into "before scanners" and "after scanners" so display order matches execution order
        before_scanner = [
            s for s in step_definitions
            if s.step_type not in (StepType.ARTIFACT_COLLECTION, StepType.COMPLETION)
        ]
        after_scanner = [
            s for s in step_definitions
            if s.step_type in (StepType.ARTIFACT_COLLECTION, StepType.COMPLETION)
        ]

        total_steps = len(step_definitions) + len(scanners)
        self.log_message(f"Pre-registering {total_steps} steps from registry (Step Definitions: {len(step_definitions)}, Scanners: {len(scanners)})")

        def register_step(step_def):
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

        # Register in execution order: before-scanner steps, then scanners, then after-scanner steps
        for step_def in before_scanner:
            register_step(step_def)

        for scanner in scanners:
            if scanner.name not in self.step_registry.steps:
                self.step_registry.step_counter += 1
                scanner_step = Step(
                    number=self.step_registry.step_counter,
                    name=scanner.name,
                    status=StepStatus.PENDING,
                    message=f"Running {scanner.name} scan... (pending)",
                    started_at=None,
                    completed_at=None,
                    timeout_seconds=self._merged_timeout(scanner),
                )
                self.step_registry.steps[scanner.name] = scanner_step
                self.step_registry._write_to_log(scanner_step)

        for step_def in after_scanner:
            register_step(step_def)

        for scanner in scanners:
            if not self._scanner_admin_enabled(scanner):
                self.step_registry.skip_step(
                    scanner.name,
                    "Disabled in admin tool settings (DB override).",
                )

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
        
        # Execute steps in order from registry (EXCEPT Completion and Artifact Collection - they run AFTER scanners)
        for step_def in step_definitions:
            if step_def.step_type == StepType.GIT_CLONE:
                await self._run_git_clone()
            elif step_def.step_type == StepType.INITIALIZATION:
                self.step_registry.start_step("Initialization", "Initializing scan...")
                self.log_message("--- Initialization ---")
                self.step_registry.complete_step("Initialization", "Scan initialized")
            elif step_def.step_type == StepType.METADATA_COLLECTION:
                await self._collect_metadata()
            # Skip Completion and Artifact Collection here - they run AFTER all scanners
        
        # Run scanners (they are registered as steps but executed separately)
        if self.selected_scanners:
            self.log_message(f"Filtered to {len(scanners)} selected scanners: {', '.join([s.name for s in scanners])}")
        else:
            self.log_message(f"Running all {len(scanners)} scanners for target {self.target_type.value}")
            if len(scanners) == 0:
                self.log_message(f"[WARNING] No scanners found! Check scanner registration and capabilities.")

        checkpoint_path = self.results_dir / "checkpoint.json"
        cp = scan_cp.load_checkpoint(checkpoint_path)
        raw_ov = os.getenv("SCANNER_TOOL_OVERRIDES_JSON", "").strip()
        global_hash = scan_cp.compute_scan_config_hash(
            scan_types=[s.value for s in self.scan_types],
            target_type=self.target_type.value,
            collect_metadata=self.collect_metadata,
            selected_scanners=sorted(self.selected_scanners) if self.selected_scanners else None,
            overrides_json=raw_ov,
        )
        checkpoint_disabled = os.getenv("SCAN_CHECKPOINT_DISABLE", "").lower() in (
            "1",
            "true",
            "yes",
        )
        if not checkpoint_disabled:
            if (cp.get("scan_config_hash") or "") != global_hash:
                scan_cp.invalidate_scanner_steps(cp)
            cp["scan_config_hash"] = global_hash
            cp["pipeline_order"] = [s.tools_key or "" for s in scanners if s.tools_key]

        target_fp = scan_cp.target_fingerprint_git(self.target_path)
        if not checkpoint_disabled:
            prev_fp = (cp.get("target_fingerprint") or "").strip()
            if target_fp and prev_fp and prev_fp != target_fp:
                scan_cp.invalidate_scanner_steps(cp)
                self.log_message(
                    f"[Checkpoint] Target revision changed ({prev_fp[:8]}… → {target_fp[:8]}…), scanner checkpoints cleared"
                )
            if target_fp:
                cp["target_fingerprint"] = target_fp
            else:
                scan_cp.invalidate_scanner_steps(cp)
            scan_cp.save_checkpoint(checkpoint_path, cp)
        resumed_any = False
        executed_upstream = False

        for scanner in scanners:
            if not self._scanner_admin_enabled(scanner):
                continue
            if not scanner.tools_key:
                executed_upstream = True
                await self._run_scanner(scanner)
                continue
            scanner_dir = self.tools_dir_results / scanner.tools_key
            cfg_h = scan_cp.scanner_config_hash(
                scanner.tools_key,
                self._merged_timeout(scanner),
                self._override_for_scanner(scanner),
            )
            can_resume = (
                not checkpoint_disabled
                and bool(target_fp)
                and scanner.checkpoint is not None
            )
            if can_resume:
                skip_ok, skip_reason = scan_cp.can_skip_scanner(
                    cp=cp,
                    tools_key=scanner.tools_key,
                    checkpoint_cfg=scanner.checkpoint,
                    scanner_dir=scanner_dir,
                    config_hash=cfg_h,
                    current_global_hash=global_hash,
                    executed_upstream=executed_upstream,
                )
                if skip_ok:
                    self.step_registry.start_step(
                        scanner.name, f"Restoring {scanner.name} from checkpoint..."
                    )
                    self.log_message(
                        f"[Checkpoint] {scanner.name} skipped (verified); reason={skip_reason or 'ok'}"
                    )
                    self.step_registry.complete_step(
                        scanner.name,
                        "Restored from checkpoint (artifact + config verified)",
                    )
                    self.scanner_statuses[scanner.name] = "SUCCESS"
                    resumed_any = True
                    cp["resumed"] = True
                    scan_cp.save_checkpoint(checkpoint_path, cp)
                    continue
            executed_upstream = True
            ran_ok = await self._run_scanner(scanner)
            if ran_ok and scanner.checkpoint and not checkpoint_disabled:
                scan_cp.record_scanner_completed(
                    cp,
                    scanner.tools_key,
                    scanner.checkpoint,
                    scanner_dir,
                    global_hash,
                    cfg_h,
                )
                scan_cp.save_checkpoint(checkpoint_path, cp)
        
        # Run Artifact Collection step AFTER all scanners (before Completion)
        artifact_collection_step_def = None
        for step_def in step_definitions:
            if step_def.step_type == StepType.ARTIFACT_COLLECTION:
                artifact_collection_step_def = step_def
                break
        
        if artifact_collection_step_def:
            await self._collect_artifacts()
        
        # Run Completion step AFTER Artifact Collection (correct order!)
        completion_step_def = None
        for step_def in step_definitions:
            if step_def.step_type == StepType.COMPLETION:
                completion_step_def = step_def
                break
        
        if completion_step_def:
            self.step_registry.start_step("Completion", "Finalizing scan...")
            self._generate_html_report()
            self.log_message("SimpleSecCheck Scan Completed")
            if not checkpoint_disabled:
                try:
                    cp_done = scan_cp.load_checkpoint(checkpoint_path)
                    cp_done["status"] = "completed"
                    cp_done["resumed"] = bool(cp_done.get("resumed") or resumed_any)
                    scan_cp.save_checkpoint(checkpoint_path, cp_done)
                except Exception:
                    pass
            if self.overall_success:
                self.step_registry.complete_step("Completion", "Scan completed successfully")
            else:
                self.step_registry.complete_step("Completion", "Scan completed with some errors")
        
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
            except (PermissionError, OSError) as e:
                raise ValueError(f"Cannot read asset files in {asset_path}: {e}")
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
    """List all available scanners and write directly to database."""
    import json
    import sys
    import logging
    from pathlib import Path
    from datetime import datetime
    
    # Configure logging based on LOG_LEVEL environment variable
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='[%(levelname)s] %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        from scanner.core.scanner_registry import ScannerRegistry, ScanType
        from scanner.core.scanner_assets.manager import ScannerAssetsManager
        
        # Trigger auto-discovery
        import scanner.plugins  # noqa: F401
        
        scanners = ScannerRegistry.get_all_scanners()
        
        # Get database URL
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logger.error("DATABASE_URL not set, cannot write scanners to database")
            sys.exit(1)
        
        # Convert postgresql:// to postgresql+asyncpg:// if needed
        if database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        # Connect to database
        import asyncpg
        try:
            # Parse connection string
            if database_url.startswith("postgresql+asyncpg://"):
                database_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
            
            conn = await asyncpg.connect(database_url)
            logger.info("Connected to database for scanner sync")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            sys.exit(1)
        
        # Load assets and metadata from manifests (no scanner names in core)
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
                # Use single source of truth for mapping
                frontend_type = map_scanner_scan_type_to_frontend_type(scan_type)
                scan_types.append(frontend_type)
            
            # Remove duplicates
            scan_types = list(set(scan_types))
            
            # Get manifest for this plugin (metadata and assets)
            manifest = (
                manifests.get(scanner_obj.tools_key)
                if (manifests and scanner_obj.tools_key)
                else None
            )
            description = manifest.description if manifest and manifest.description else f"Security scanner: {scanner_obj.name}"
            categories = manifest.categories if manifest and manifest.categories else ["Security Scanning"]
            icon = manifest.icon if manifest and manifest.icon else "🔧"
            
            try:
                mt = getattr(scanner_obj, "timeout", None)
                exec_timeout = int(mt) if mt and int(mt) > 0 else 900
            except (TypeError, ValueError):
                exec_timeout = 900
            scanner_data = {
                "name": scanner_obj.name,
                "scan_types": scan_types,
                "priority": scanner_obj.priority,
                "requires_condition": scanner_obj.requires_condition,
                "enabled": scanner_obj.enabled,
                "description": description,
                "categories": categories,
                "icon": icon,
                "execution_timeout": exec_timeout,
                "tools_key": getattr(scanner_obj, "tools_key", None),
            }
            
            if manifest:
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
        
        # Write scanners directly to database
        now = datetime.utcnow()
        synced_count = 0
        
        try:
            for scanner_data in scanner_list:
                # Extract metadata (description, categories, assets)
                # Icons are NOT stored in DB - they remain in frontend code only
                mt = int(scanner_data.get("execution_timeout") or 900)
                metadata = {
                    "description": scanner_data.get("description"),
                    "categories": scanner_data.get("categories", []),
                    "assets": scanner_data.get("assets", []),
                    "execution": {"timeout": mt},
                    "tools_key": scanner_data.get("tools_key"),
                }
                
                # Check if scanner exists
                existing = await conn.fetchrow(
                    "SELECT id FROM scanners WHERE name = $1",
                    scanner_data["name"]
                )
                
                if existing:
                    # Update existing scanner
                    await conn.execute(
                        """
                        UPDATE scanners 
                        SET scan_types = $1, 
                            priority = $2, 
                            requires_condition = $3, 
                            enabled = $4,
                            scanner_metadata = $5,
                            last_discovered_at = $6,
                            updated_at = $7
                        WHERE name = $8
                        """,
                        json.dumps(scanner_data["scan_types"]),
                        scanner_data["priority"],
                        scanner_data.get("requires_condition"),
                        scanner_data.get("enabled", True),
                        json.dumps(metadata),
                        now,
                        now,
                        scanner_data["name"]
                    )
                else:
                    # Insert new scanner
                    import uuid
                    scanner_id = uuid.uuid4()
                    await conn.execute(
                        """
                        INSERT INTO scanners (id, name, scan_types, priority, requires_condition, enabled, scanner_metadata, last_discovered_at, created_at, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                        """,
                        scanner_id,
                        scanner_data["name"],
                        json.dumps(scanner_data["scan_types"]),
                        scanner_data["priority"],
                        scanner_data.get("requires_condition"),
                        scanner_data.get("enabled", True),
                        json.dumps(metadata),
                        now,
                        now,
                        now
                    )
                synced_count += 1
            
            await conn.close()
            logger.info(f"Successfully synced {synced_count} scanners to database")
            sys.exit(0)
            
        except Exception as db_error:
            await conn.close()
            logger.error(f"Failed to write scanners to database: {db_error}")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Failed to list scanners: {e}", exc_info=True)
        sys.exit(1)


async def main():
    """Main entry point for orchestrator"""
    import sys
    
    # Check for --help flag
    if len(sys.argv) > 1 and (sys.argv[1] == "--help" or sys.argv[1] == "-h"):
        from scanner.core.help import print_help
        print_help()
        return
    
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
    
    # Auto-generate SCAN_ID for standalone usage (when not provided)
    # Worker-provided scans MUST have SCAN_ID set, but for standalone CLI usage we can auto-generate
    if not scan_id:
        # Generate auto ID for standalone usage
        from datetime import datetime
        import uuid
        scan_id = f"scan-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8]}"
        print(f"[Orchestrator] No SCAN_ID provided, auto-generating: {scan_id}")
        print(f"[Orchestrator] Note: For Worker-based scans, SCAN_ID must be provided!")
    
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
    
    # Set global StepRegistry for scanner access
    set_global_step_registry(step_registry)
    
    # Create orchestrator
    orchestrator = ScanOrchestrator(step_registry)
    
    # Run scan
    exit_code = await orchestrator.run_scan()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
