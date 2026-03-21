"""
Base Scanner Class
Common functionality for all scanner implementations
"""
import os
import signal
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
from scanner.core.scanner_registry import ScanType, TargetType, ArtifactType, ScannerCapability
from scanner.core.step_registry import SubStepType
from scanner.core.manifest_exit_codes import (
    lookup_exit_description,
    plugin_manifest_path_from_class,
)
from abc import ABC, abstractmethod

# Global StepRegistry instance (set by orchestrator)
_global_step_registry = None


def scan_log_verbose() -> bool:
    """When true, mirror tool stdout/stderr to console. Default: quiet console, full detail in per-tool log files."""
    return os.environ.get("SSC_SCAN_LOG_VERBOSE", "").strip().lower() in ("1", "true", "yes")


def set_global_step_registry(step_registry):
    """Set global StepRegistry instance for scanner access"""
    global _global_step_registry
    _global_step_registry = step_registry


def get_global_step_registry():
    """Get global StepRegistry instance"""
    return _global_step_registry


class BaseScanner(ABC):
    """Base class for all scanners - provides common functionality"""
    
    # Metadaten als Klassenattribute - werden von Subklassen überschrieben
    CAPABILITIES: List[ScannerCapability] = []  # Liste von ScannerCapability
    PRIORITY: int = 0  # Execution order (lower = earlier)
    REQUIRES_CONDITION: Optional[str] = None  # Optional condition (e.g., "IS_NATIVE")
    SCRIPT_PATH: Optional[str] = None  # Path to Bash fallback script
    ENV_VARS: Dict[str, str] = {}  # Default environment variables
    
    def __init__(
        self,
        name: str,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None,
        step_name: Optional[str] = None,
    ):
        """
        Initialize scanner.

        Args:
            name: Display name (e.g. "Semgrep") – fallback when step_name not set.
            target_path: Path to scan target.
            results_dir: Directory for results.
            log_file: Path to log file.
            config_path: Optional path to config file.
            step_name: Step name from registry/manifest (single source). Used for step/substep
                registration so the same step number is used as the orchestrator’s pre-registered step.
        """
        self.name = step_name if step_name is not None else name
        self.target_path = Path(target_path)
        self.results_dir = Path(results_dir)
        self.log_file = Path(log_file)
        self.config_path = Path(config_path) if config_path else None
        
        # Ensure directories exist
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self._manifest_exit_note_logged = False

    def log(self, message: str, level: str = "INFO"):
        """Log message to log file and stdout"""
        prefix = f"[{self.name}]"
        
        if level == "ERROR":
            formatted = f"{prefix} [ERROR] {message}"
        elif level == "WARNING":
            formatted = f"{prefix} [WARNING] {message}"
        elif level == "SUCCESS":
            formatted = f"{prefix} [SUCCESS] {message}"
        else:
            formatted = f"{prefix} {message}"
        
        print(formatted)
        
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"{formatted}\n")
        except Exception as e:
            print(f"[{self.name}] Error writing to log: {e}")

    def _log_output_tail(self, text: Optional[str], label: str, max_lines: int = 40) -> None:
        """Append a tail of stdout/stderr to console (used when command fails in quiet mode)."""
        if not text or not text.strip():
            return
        lines = [ln for ln in text.strip().split("\n") if ln.strip()]
        if not lines:
            return
        tail = lines[-max_lines:]
        self.log(f"{label} (last {len(tail)} lines):", "WARNING")
        for line in tail:
            self.log(f"  {line}", "WARNING")
    
    def get_timeout(self) -> int:
        """Timeout seconds from ``SCANNER_TIMEOUT_SECONDS`` (set by orchestrator from manifest only)."""
        raw = os.getenv("SCANNER_TIMEOUT_SECONDS")
        if raw is None or not str(raw).strip():
            raise RuntimeError(
                "SCANNER_TIMEOUT_SECONDS is not set. "
                "The orchestrator must set it from the plugin manifest before running a scanner."
            )
        try:
            t = int(raw)
        except (ValueError, TypeError) as e:
            raise RuntimeError(
                f"SCANNER_TIMEOUT_SECONDS must be a positive integer, got {raw!r}"
            ) from e
        if t <= 0:
            raise RuntimeError(f"SCANNER_TIMEOUT_SECONDS must be positive, got {t}")
        return t
    
    def run_command(
        self,
        cmd: List[str],
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        capture_output: bool = True,
        use_process_group: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        Run a command and log output
        
        Args:
            cmd: Command to run
            cwd: Working directory
            env: Environment variables
            timeout: Timeout in seconds (None = use SCANNER_TIMEOUT_SECONDS from manifest)
            capture_output: Whether to capture stdout/stderr
            use_process_group: If True, use setsid + killpg on timeout (default). Set False for
                tools like Checkov where process groups break multiprocessing.
        
        Returns:
            CompletedProcess result
        """
        if timeout is None:
            timeout = self.get_timeout()
        if scan_log_verbose():
            self.log(f"Running command: {' '.join(cmd)}")
        else:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(f"\n--- Running: {' '.join(cmd)} ---\n")
            except OSError:
                pass
        
        process = None
        try:
            # Process group: kill all children on timeout. Optional: Checkov passes False (setsid breaks it).
            process = subprocess.Popen(
                cmd,
                cwd=str(cwd) if cwd else None,
                env=env or os.environ.copy(),
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
                text=True,
                preexec_fn=os.setsid if (hasattr(os, 'setsid') and use_process_group) else None
            )
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                returncode = process.returncode
            except subprocess.TimeoutExpired:
                if use_process_group and hasattr(os, "setsid"):
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                            process.wait()
                    except (ProcessLookupError, OSError):
                        process.kill()
                        process.wait()
                else:
                    process.kill()
                    process.wait()
                
                self.log(f"Command timed out after {timeout} seconds", "ERROR")
                raise subprocess.TimeoutExpired(cmd, timeout)
            
            # Create CompletedProcess-like result
            result = subprocess.CompletedProcess(
                cmd,
                returncode,
                stdout,
                stderr
            )
            
            # Log output: always full detail to per-tool log file; console depends on SSC_SCAN_LOG_VERBOSE
            if capture_output:
                verbose = scan_log_verbose()
                if result.stdout:
                    with open(self.log_file, "a", encoding="utf-8") as f:
                        f.write(result.stdout)
                    if verbose and result.returncode != 0:
                        stdout_lines = result.stdout.split("\n")
                        error_lines = [
                            line.strip()
                            for line in stdout_lines
                            if line.strip()
                            and any(
                                keyword in line.lower()
                                for keyword in ("error", "failed", "exception", "fatal", "warning")
                            )
                        ]
                        for error_line in error_lines[:10]:
                            self.log(
                                f"[STDOUT] {error_line}",
                                "ERROR"
                                if "error" in error_line.lower() or "failed" in error_line.lower()
                                else "WARNING",
                            )

                if result.stderr:
                    with open(self.log_file, "a", encoding="utf-8") as f:
                        f.write(result.stderr)
                    if verbose:
                        stderr_lines = result.stderr.split("\n")
                        for stderr_line in stderr_lines[:50]:
                            if stderr_line.strip():
                                # Many tools log progress to stderr; only treat as ERROR on failure
                                lvl = "ERROR" if result.returncode != 0 else "INFO"
                                self.log(f"[STDERR] {stderr_line.strip()}", lvl)
                    elif result.returncode != 0:
                        self._log_output_tail(result.stderr, "[STDERR]", max_lines=50)
                        self._log_output_tail(result.stdout, "[STDOUT]", max_lines=25)
            
            if result.returncode == 0:
                if scan_log_verbose():
                    self.log("Command completed successfully", "SUCCESS")
                else:
                    try:
                        with open(self.log_file, "a", encoding="utf-8") as f:
                            f.write(f"[{self.name}] Command completed successfully\n")
                    except OSError:
                        pass
            else:
                self.log(f"Command failed with exit code {result.returncode}", "ERROR")
                mp = plugin_manifest_path_from_class(type(self))
                if mp:
                    desc, note, has_codes = lookup_exit_description(
                        mp, list(cmd), result.returncode
                    )
                    plug = mp.parent.name
                    if desc:
                        self.log(
                            f"[manifest {plug}] exit {result.returncode}: {desc}",
                            "WARNING",
                        )
                    elif has_codes:
                        self.log(
                            f"[manifest {plug}] exit {result.returncode} not listed under exit_codes.codes.",
                            "INFO",
                        )
                    elif note and not self._manifest_exit_note_logged:
                        self.log(
                            f"[manifest {plug}] exit_codes.note: {note}",
                            "INFO",
                        )
                        self._manifest_exit_note_logged = True

            return result
            
        except subprocess.TimeoutExpired:
            raise
        except Exception as e:
            if process:
                try:
                    if use_process_group and hasattr(os, "setsid"):
                        try:
                            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        except (ProcessLookupError, OSError):
                            process.kill()
                    else:
                        process.kill()
                    process.wait()
                except Exception:
                    pass
            self.log(f"Error running command: {e}", "ERROR")
            raise
    
    def get_tool_command(self, tool_name: str) -> Optional[List[str]]:
        """
        Determine the command to run a tool.
        Checks PATH first (so e.g. semgrep binary is used, not python -m semgrep), then npx, then Python module.
        """
        # 1. Check if it's in PATH (prefer binary over python -m for tools like semgrep)
        try:
            result = subprocess.run(
                ["which", tool_name],
                capture_output=True, text=True, check=False, timeout=5
            )
            if result.returncode == 0:
                return [tool_name]
        except Exception:
            pass

        # 2. Check if it's an npx command (for Node.js tools)
        try:
            result = subprocess.run(
                ["npx", "--no-install", tool_name, "--version"],
                capture_output=True, text=True, check=False, timeout=5
            )
            if result.returncode == 0:
                return ["npx", tool_name]
        except Exception:
            pass

        # 3. Check if it's a Python module
        try:
            import importlib.util
            spec = importlib.util.find_spec(tool_name)
            if spec:
                return ["python3", "-m", tool_name]
        except Exception:
            pass

        return None

    def check_tool_installed(self, tool_name: str) -> bool:
        """Check if a tool is installed and executable."""
        return self.get_tool_command(tool_name) is not None
    
    def get_exclude_args(self, exclude_paths: Optional[str] = None) -> List[str]:
        """
        Parse exclude paths and return command arguments
        
        Args:
            exclude_paths: Comma-separated list of paths to exclude
        
        Returns:
            List of exclude arguments (scanner-specific, override in subclass)
        """
        if not exclude_paths:
            return []
        
        # Default: return as-is, subclasses should override
        return []
    
    def ensure_output_file(self, file_path: Path) -> Path:
        """Ensure output file directory exists"""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        return file_path
    
    def start_substep(self, substep_name: str, message: str = "", substep_type: SubStepType = SubStepType.ACTION):
        """
        Start a substep for this scanner
        
        Args:
            substep_name: Name of the substep
            message: Optional message
            substep_type: Type of substep (PHASE, ACTION, OUTPUT)
        """
        step_registry = get_global_step_registry()
        if step_registry:
            step_registry.start_substep(self.name, substep_name, message, substep_type)
    
    def complete_substep(self, substep_name: str, message: str = ""):
        """
        Complete a substep for this scanner
        
        Args:
            substep_name: Name of the substep
            message: Optional completion message
        """
        step_registry = get_global_step_registry()
        if step_registry:
            step_registry.complete_substep(self.name, substep_name, message)
    
    def fail_substep(self, substep_name: str, message: str = ""):
        """
        Mark a substep as failed for this scanner
        
        Args:
            substep_name: Name of the substep
            message: Optional error message
        """
        step_registry = get_global_step_registry()
        if step_registry:
            step_registry.fail_substep(self.name, substep_name, message)
    
    def update_substep(self, substep_name: str, message: str = ""):
        """
        Update a substep message for this scanner
        
        Args:
            substep_name: Name of the substep
            message: New message
        """
        step_registry = get_global_step_registry()
        if step_registry:
            step_registry.update_substep(self.name, substep_name, message)
    
    # Standardized Substep Pipeline Helpers
    def substep_init(self, message: str = "Initializing..."):
        """Standard INIT substep"""
        self.start_substep("Initialization", message, SubStepType.ACTION)
    
    def substep_prepare(self, substep_name: str, message: str = ""):
        """Standard PREPARE substep (Phase)"""
        self.start_substep(substep_name, message, SubStepType.PHASE)
    
    def substep_scan(self, substep_name: str, message: str = ""):
        """Standard SCAN substep (Phase)"""
        self.start_substep(substep_name, message, SubStepType.PHASE)
    
    def substep_process(self, substep_name: str, message: str = ""):
        """Standard PROCESS substep (Action)"""
        self.start_substep(substep_name, message, SubStepType.ACTION)
    
    def substep_report(self, report_type: str, message: str = ""):
        """Standard REPORT substep (Output)"""
        self.start_substep(f"Generating {report_type} Report", message, SubStepType.OUTPUT)
    
    @abstractmethod
    def scan(self) -> bool:
        """
        Run the scan
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    def run(self) -> bool:
        """
        Main entry point - runs scan with error handling
        
        Returns:
            True if successful, False otherwise
        """
        self.log(f"Initializing {self.name} scan...")
        if scan_log_verbose():
            self.log(f"Target: {self.target_path}")
            self.log(f"Results: {self.results_dir}")
        
        try:
            return self.scan()
        except Exception as e:
            self.log(f"Scan failed with exception: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            return False
    
    @staticmethod
    def get_default_params_from_env() -> Dict[str, str]:
        """
        Get default parameters from environment variables.
        Used by __main__ blocks in scanner plugins.
        
        Returns:
            Dictionary with default parameters (target_path, results_dir, log_file)
        """
        import os
        scan_id = os.getenv("SCAN_ID", "test")
        return {
            "target_path": os.getenv("TARGET_PATH", "/target"),
            "results_dir": os.getenv("RESULTS_DIR", f"/app/results/{scan_id}"),
            "log_file": os.getenv("LOG_FILE", f"/app/results/{scan_id}/logs/scan.log"),
        }
