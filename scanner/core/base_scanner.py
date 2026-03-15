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
from abc import ABC, abstractmethod

# Global StepRegistry instance (set by orchestrator)
_global_step_registry = None


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
        config_path: Optional[str] = None
    ):
        """
        Initialize scanner
        
        Args:
            name: Scanner name (e.g., "Semgrep")
            target_path: Path to scan target
            results_dir: Directory for results
            log_file: Path to log file
            config_path: Optional path to config file
        """
        self.name = name
        self.target_path = Path(target_path)
        self.results_dir = Path(results_dir)
        self.log_file = Path(log_file)
        self.config_path = Path(config_path) if config_path else None
        
        # Ensure directories exist
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
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
    
    def run_command(
        self,
        cmd: List[str],
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        capture_output: bool = True
    ) -> subprocess.CompletedProcess:
        """
        Run a command and log output
        
        Args:
            cmd: Command to run
            cwd: Working directory
            env: Environment variables
            timeout: Timeout in seconds
            capture_output: Whether to capture stdout/stderr
        
        Returns:
            CompletedProcess result
        """
        self.log(f"Running command: {' '.join(cmd)}")
        
        process = None
        try:
            # Use process group to kill all child processes on timeout
            # This is important for tools like Checkov that use multiprocessing
            # NOTE: os.setsid can cause issues with Checkov's multiprocessing, so we only use it for timeout handling
            # We'll use a different approach: track child PIDs and kill them manually
            use_process_group = True  # Can be disabled per-scanner if needed
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
                # Kill the entire process group (including all child processes)
                if hasattr(os, 'setsid'):
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        # Wait a bit for graceful shutdown
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            # Force kill if still running
                            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                            process.wait()
                    except (ProcessLookupError, OSError):
                        # Process already dead or no process group
                        process.kill()
                        process.wait()
                else:
                    # Fallback for Windows
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
            
            # Log output
            if capture_output:
                if result.stdout:
                    with open(self.log_file, "a", encoding="utf-8") as f:
                        f.write(result.stdout)
                    # Also log errors from stdout to console
                    if result.returncode != 0:
                        stdout_lines = result.stdout.split('\n')
                        error_lines = [line.strip() for line in stdout_lines if line.strip() and any(keyword in line.lower() for keyword in ['error', 'failed', 'exception', 'fatal', 'warning'])]
                        if error_lines:
                            for error_line in error_lines[:10]:  # Log first 10 error lines
                                self.log(f"[STDOUT] {error_line}", "ERROR" if "error" in error_line.lower() or "failed" in error_line.lower() else "WARNING")
                
                if result.stderr:
                    with open(self.log_file, "a", encoding="utf-8") as f:
                        f.write(result.stderr)
                    # Always log stderr to console as it contains error messages
                    stderr_lines = result.stderr.split('\n')
                    for stderr_line in stderr_lines[:20]:  # Log first 20 stderr lines
                        if stderr_line.strip():
                            self.log(f"[STDERR] {stderr_line.strip()}", "ERROR")
            
            if result.returncode == 0:
                self.log(f"Command completed successfully", "SUCCESS")
            else:
                self.log(f"Command failed with exit code {result.returncode}", "ERROR")
            
            return result
            
        except subprocess.TimeoutExpired:
            raise
        except Exception as e:
            if process:
                try:
                    if hasattr(os, 'setsid'):
                        try:
                            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        except (ProcessLookupError, OSError):
                            process.kill()
                    else:
                        process.kill()
                    process.wait()
                except:
                    pass
            self.log(f"Error running command: {e}", "ERROR")
            raise
    
    def get_tool_command(self, tool_name: str) -> Optional[List[str]]:
        """
        Determine the command to run a tool.
        Checks for Python module, npx, and then PATH.
        """
        # 1. Check if it's a Python module
        try:
            import importlib.util
            spec = importlib.util.find_spec(tool_name)
            if spec:
                return ["python3", "-m", tool_name]
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

        # 3. Check if it's in PATH
        try:
            result = subprocess.run(
                ["which", tool_name],
                capture_output=True, text=True, check=False, timeout=5
            )
            if result.returncode == 0:
                return [tool_name]
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
    
    def start_substep(self, substep_name: str, message: str = ""):
        """
        Start a substep for this scanner
        
        Args:
            substep_name: Name of the substep
            message: Optional message
        """
        step_registry = get_global_step_registry()
        if step_registry:
            step_registry.start_substep(self.name, substep_name, message)
    
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
        self.log(f"Target: {self.target_path}")
        self.log(f"Results: {self.results_dir}")
        
        try:
            return self.scan()
        except Exception as e:
            self.log(f"Scan failed with exception: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            return False
