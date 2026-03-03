"""
Base Scanner Class
Common functionality for all scanner implementations
"""
import os
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod


class BaseScanner(ABC):
    """Base class for all scanners - provides common functionality"""
    
    # Metadaten als Klassenattribute - werden von Subklassen überschrieben
    SCAN_TYPES: List = []  # Liste von ScanType Enum-Werten
    PRIORITY: int = 0  # Execution order (lower = earlier)
    REQUIRES_CONDITION: Optional[str] = None  # Optional condition (e.g., "IS_NATIVE", "CLAIR_IMAGE")
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
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(cwd) if cwd else None,
                env=env or os.environ.copy(),
                timeout=timeout,
                capture_output=capture_output,
                text=True,
                check=False
            )
            
            # Log output
            if capture_output:
                if result.stdout:
                    with open(self.log_file, "a", encoding="utf-8") as f:
                        f.write(result.stdout)
                if result.stderr:
                    with open(self.log_file, "a", encoding="utf-8") as f:
                        f.write(result.stderr)
            
            if result.returncode == 0:
                self.log(f"Command completed successfully", "SUCCESS")
            else:
                self.log(f"Command failed with exit code {result.returncode}", "ERROR")
            
            return result
            
        except subprocess.TimeoutExpired:
            self.log(f"Command timed out after {timeout} seconds", "ERROR")
            raise
        except Exception as e:
            self.log(f"Error running command: {e}", "ERROR")
            raise
    
    def check_tool_installed(self, tool_name: str) -> bool:
        """Check if a tool is installed"""
        try:
            result = subprocess.run(
                ["which", tool_name],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
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
