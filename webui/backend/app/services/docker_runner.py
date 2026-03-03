"""
Docker Runner Service
Replaces run-docker.sh with pure Python implementation
Orchestrates docker-compose run commands for security scans
"""

import os
import re
import json
import subprocess
import tempfile
import shutil
import asyncio
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Callable
from datetime import datetime

# Import central path functions
import sys
sys.path.insert(0, "/app/scanner")
from core.path_setup import (
    get_host_project_root,
    get_docker_compose_file,
    get_docker_compose_context,
    get_owasp_data_path_host,
    get_target_mount_path_host,
)


class DockerRunner:
    """Orchestrates Docker Compose scans"""
    
    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize Docker Runner
        
        Args:
            log_file: Optional path to log file for orchestrator logs
        """
        self.log_file = log_file
        self.overall_success = False
        self.output_lines = []  # Store output lines (for debugging/logging purposes)
        self.process: Optional[asyncio.subprocess.Process] = None  # Track subprocess for cleanup
        
    def log_message(self, message: str, level: str = "INFO"):
        """Log message to stdout and log file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = f"[SimpleSecCheck Docker]"
        
        if level == "SUCCESS":
            formatted = f"{prefix} [SUCCESS] {message}"
        elif level == "WARNING":
            formatted = f"{prefix} [WARNING] {message}"
        elif level == "ERROR":
            formatted = f"{prefix} [ERROR] {message}"
        else:
            formatted = f"{prefix} {message}"
        
        print(formatted)
        
        if self.log_file:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(f"[{timestamp}] [{level}] {message}\n")
            except Exception:
                pass  # Ignore log file errors
    
    def determine_scan_type(self, target: str) -> Tuple[str, str, str]:
        """
        Determine scan type from target
        
        Returns:
            Tuple of (scan_type, target_path, zap_target, project_name)
        """
        if target == "network":
            return ("network", "", "", "network-infrastructure")
        elif target.startswith(("http://", "https://")):
            # Website scan
            project_name = target.replace("https://", "").replace("http://", "")
            project_name = project_name.split("/")[0].split(":")[0]
            return ("website", "", target, project_name)
        else:
            # Code scan
            target_path = target
            
            # Check if TARGET is a temporary Git clone path
            if "results/tmp/" in target or target.startswith("/") and "/tmp/" in target:
                # Try to get repo name from GIT_URL environment variable
                git_url = os.environ.get("GIT_URL", "")
                if git_url:
                    if "github.com" in git_url or "gitlab.com" in git_url:
                        project_name = git_url.rstrip("/").split("/")[-1].replace(".git", "")
                    else:
                        project_name = Path(target).name
                else:
                    project_name = Path(target).name
            else:
                project_name = Path(target).name
            
            return ("code", target_path, "", project_name)
    
    def create_tracked_snapshot(
        self, 
        target_path: str, 
        results_dir: str
    ) -> Optional[str]:
        """
        Create git archive snapshot for CI mode (tracked files only)
        
        Returns:
            Path to snapshot directory or None if failed
        """
        try:
            # Check if it's a git repository
            result = subprocess.run(
                ["git", "-C", target_path, "rev-parse", "--is-inside-work-tree"],
                capture_output=True,
                timeout=10
            )
            
            if result.returncode != 0:
                self.log_message(
                    "SCAN_SCOPE=tracked requested, but target is not a git repository. "
                    "Falling back to full scan scope.",
                    "WARNING"
                )
                return None
            
            # Create temp directory in results/tmp (host-mounted)
            temp_dir = tempfile.mkdtemp(
                prefix="simpleseccheck-tracked-",
                dir=os.path.join(results_dir, "tmp")
            )
            
            self.log_message(f"Creating tracked snapshot in: {temp_dir}")
            
            # Create git archive
            archive_process = subprocess.Popen(
                ["git", "-C", target_path, "archive", "--format=tar", "HEAD"],
                stdout=subprocess.PIPE
            )
            
            extract_process = subprocess.Popen(
                ["tar", "-xf", "-", "-C", temp_dir],
                stdin=archive_process.stdout
            )
            
            archive_process.stdout.close()
            extract_process.wait()
            archive_process.wait()
            
            if extract_process.returncode == 0:
                file_count = len(list(Path(temp_dir).rglob("*")))
                self.log_message(f"Git archive created successfully with {file_count} files")
                return temp_dir
            else:
                self.log_message("Failed to create git archive snapshot", "ERROR")
                return None
                
        except Exception as e:
            self.log_message(f"Error creating tracked snapshot: {e}", "ERROR")
            return None
    
    def find_finding_policy(
        self, 
        target_mount_path: str,
        finding_policy_arg: Optional[str] = None
    ) -> Optional[str]:
        """
        Find finding policy file
        
        Returns:
            Container path to policy file (e.g., /target/config/finding-policy.json) or None
        """
        if finding_policy_arg:
            # Explicit policy path
            if finding_policy_arg.startswith("/target/"):
                # Already a container path
                return finding_policy_arg
            elif finding_policy_arg.startswith("/"):
                # Absolute host path - convert to container path
                if os.path.exists("/app") or os.path.exists("/.dockerenv"):
                    # Running in container - assume it's inside target
                    return f"/target/{Path(finding_policy_arg).name}"
                elif finding_policy_arg.startswith(target_mount_path):
                    # Path is inside target
                    relative = finding_policy_arg[len(target_mount_path):]
                    if relative.startswith("/"):
                        relative = relative[1:]
                    return f"/target/{relative}"
            else:
                # Relative path - will be at /target/$path
                return f"/target/{finding_policy_arg}"
        
        # Auto-detect policy files
        policy_candidates = [
            "config/finding-policy.json",
            "config/finding_policy.json",
            "config/policy/finding-policy.json",
            "config/policy/finding_policy.json",
            "security/finding-policy.json",
            "security/finding_policy.json",
            ".security/finding-policy.json",
            ".security/finding_policy.json",
        ]
        
        for candidate in policy_candidates:
            policy_path = Path(target_mount_path) / candidate
            if policy_path.exists():
                self.log_message(f"Auto-detected finding policy: /target/{candidate}")
                return f"/target/{candidate}"
        
        return None
    
    def build_docker_compose_command(
        self,
        scan_type: str,
        target_mount_path: Optional[str],
        results_dir: str,
        logs_dir: str,
        zap_target: str = "",
        finding_policy: Optional[str] = None,
        collect_metadata: bool = False,
        scan_scope: str = "full",
        exclude_paths: str = "",
        scan_id: Optional[str] = None,
    ) -> List[str]:
        """
        Build docker-compose run command
        
        Returns:
            List of command arguments
        """
        docker_compose_file = get_docker_compose_file()
        docker_compose_context = get_docker_compose_context()
        
        # Base command
        cmd = [
            "docker-compose",
            "-f", docker_compose_file,
            "--project-directory", docker_compose_context,
            "run", "--rm"
        ]
        
        # Environment variables
        env_vars = [
            ("SCAN_TYPE", scan_type),
            ("ZAP_TARGET", zap_target),
            ("TARGET_URL", zap_target),
            ("PROJECT_RESULTS_DIR", results_dir),
            ("RESULTS_DIR_IN_CONTAINER", "/SimpleSecCheck/results"),  # Container path
            ("LOGS_DIR_IN_CONTAINER", "/SimpleSecCheck/results/logs"),  # Container path (logs is subdirectory of results)
            ("TARGET_PATH_IN_CONTAINER", "/target"),  # Container path
            ("COLLECT_METADATA", "true" if collect_metadata else "false"),
            ("PYTHONPATH", "/SimpleSecCheck"),  # Set PYTHONPATH so scanner module can be found
        ]
        
        # Add SCAN_ID if provided
        if scan_id:
            env_vars.append(("SCAN_ID", scan_id))
        
        # Add SELECTED_SCANNERS if provided (from environment or parameter)
        selected_scanners = os.environ.get("SELECTED_SCANNERS")
        if selected_scanners:
            env_vars.append(("SELECTED_SCANNERS", selected_scanners))
        
        if scan_type == "code":
            env_vars.extend([
                ("SIMPLESECCHECK_EXCLUDE_PATHS", exclude_paths),
                ("TARGET_PATH_HOST", target_mount_path or ""),
            ])
        
        if finding_policy:
            env_vars.append(("FINDING_POLICY_FILE", finding_policy))
            env_vars.append(("FINDING_POLICY_FILE_IN_CONTAINER", finding_policy))  # Also set for metadata collection
        
        for key, value in env_vars:
            cmd.extend(["-e", f"{key}={value}"])
        
        # Volume mounts
        volumes = [
            (results_dir, "/SimpleSecCheck/results"),
        ]
        
        if scan_type == "code" and target_mount_path:
            volumes.append((target_mount_path, "/target:ro"))
        
        # OWASP data volume - ALWAYS mount, even if path doesn't exist
        owasp_data_path = get_owasp_data_path_host()
        if not owasp_data_path:
            # Fallback: try to get from HOST_PROJECT_ROOT environment variable
            host_project_root = os.environ.get("HOST_PROJECT_ROOT")
            if host_project_root:
                owasp_data_path = os.path.join(host_project_root, "owasp-dependency-check-data")
                self.log_message(f"[OWASP Volume] Using HOST_PROJECT_ROOT fallback: {owasp_data_path}")
        
        if owasp_data_path:
            volumes.append((owasp_data_path, "/SimpleSecCheck/owasp-dependency-check-data"))
            self.log_message(f"[OWASP Volume] Using host path: {owasp_data_path}")
            if not os.path.exists(owasp_data_path):
                self.log_message(f"[OWASP Volume] Path does not exist yet, Docker will create it: {owasp_data_path}", "WARNING")
        else:
            self.log_message("[OWASP Volume] ERROR: OWASP data path not found and HOST_PROJECT_ROOT not set!", "ERROR")
            # Still try to mount a default path to avoid scan failure
            volumes.append(("/app/owasp-dependency-check-data", "/SimpleSecCheck/owasp-dependency-check-data"))
            self.log_message("[OWASP Volume] Using fallback container path: /app/owasp-dependency-check-data", "WARNING")
        
        # Docker socket for network scans
        if scan_type == "network":
            volumes.append(("/var/run/docker.sock", "/var/run/docker.sock:ro"))
        
        for host_path, container_path in volumes:
            cmd.extend(["-v", f"{host_path}:{container_path}"])
        
        # Command to run in container
        # Use modern Python orchestrator instead of bash script
        # PYTHONPATH is set as environment variable above, but we also set it explicitly in the command
        cmd.extend([
            "scanner",
            "sh", "-c",
            "cd /SimpleSecCheck && PYTHONPATH=/SimpleSecCheck:$PYTHONPATH python3 -m scanner.core.orchestrator"
        ])
        
        return cmd
    
    async def run_scan_async(
        self,
        target: str,
        scan_id: Optional[str] = None,
        project_name: Optional[str] = None,
        results_dir: Optional[str] = None,
        ci_mode: bool = False,
        finding_policy: Optional[str] = None,
        collect_metadata: bool = False,
        output_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """
        Run security scan asynchronously with output streaming
        
        Args:
            target: Target path or URL
            scan_id: Optional scan ID (timestamp format)
            project_name: Optional project name (auto-detected if not provided)
            results_dir: Optional results directory (auto-calculated if not provided)
            ci_mode: Enable CI mode (tracked files only)
            finding_policy: Optional finding policy file path
            collect_metadata: Collect scan metadata
            output_callback: Optional callback function for each output line
        
        Returns:
            True if scan succeeded, False otherwise
        """
        # Determine scan type
        scan_type, target_path, zap_target, detected_project_name = self.determine_scan_type(target)
        
        if not project_name:
            project_name = detected_project_name
        
        # Generate scan_id if not provided
        if not scan_id:
            scan_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        project_dir = f"{project_name}_{scan_id}"
        
        # Determine results directory
        if not results_dir:
            # Use environment variable or calculate
            results_dir_env = os.environ.get("RESULTS_DIR")
            if results_dir_env:
                results_dir = results_dir_env
                self.log_message(f"Using RESULTS_DIR from environment: '{results_dir}'")
            else:
                # Calculate from project root
                project_root = get_host_project_root()
                if project_root:
                    results_dir = os.path.join(project_root, "results", project_dir)
                else:
                    # Fallback to /app/results (container path)
                    results_dir = f"/app/results/{project_dir}"
        
        logs_dir = os.path.join(results_dir, "logs")
        
        # Create directories
        os.makedirs(logs_dir, exist_ok=True)
        
        # Set log file
        if not self.log_file:
            self.log_file = os.path.join(logs_dir, "orchestrator.log")
        
        self.log_message(f"Logging to: {self.log_file}")
        self.log_message("Starting Docker container for security scan...")
        
        # Handle CI mode (tracked files only)
        temp_snapshot_dir = None
        target_mount_path = target_path
        scan_scope = "tracked" if ci_mode else "full"
        exclude_paths = os.environ.get("SIMPLESECCHECK_EXCLUDE_PATHS", "")
        
        if ci_mode and scan_type == "code":
            exclude_paths = exclude_paths or ".git,node_modules,dist,build,coverage,.next,.nuxt,.cache"
            
            if target_path:
                temp_snapshot_dir = self.create_tracked_snapshot(target_path, results_dir)
                if temp_snapshot_dir:
                    target_mount_path = temp_snapshot_dir
                    self.log_message(f"Using tracked-only snapshot: {target_mount_path}")
        
        # Convert container paths to host paths for mounting
        if scan_type == "code" and target_mount_path:
            target_mount_path_host = get_target_mount_path_host(target_mount_path)
            # Also handle results_dir and logs_dir conversion if needed
            if results_dir.startswith("/app/results/"):
                host_project_root = get_host_project_root()
                if host_project_root:
                    relative = results_dir[len("/app/results"):]
                    if relative.startswith("/"):
                        relative = relative[1:]
                    results_dir_host = os.path.join(host_project_root, "results", relative)
                    logs_dir_host = os.path.join(results_dir_host, "logs")
                else:
                    results_dir_host = results_dir
                    logs_dir_host = logs_dir
            else:
                results_dir_host = results_dir
                logs_dir_host = logs_dir
        else:
            target_mount_path_host = target_mount_path
            results_dir_host = results_dir
            logs_dir_host = logs_dir
        
        # Find finding policy
        finding_policy_container = None
        if scan_type == "code" and target_mount_path:
            finding_policy_container = self.find_finding_policy(
                target_mount_path,
                finding_policy
            )
            if finding_policy_container:
                self.log_message(f"Using finding policy: {finding_policy_container}")
        
        # Build docker-compose command
        cmd = self.build_docker_compose_command(
            scan_type=scan_type,
            target_mount_path=target_mount_path_host,
            results_dir=results_dir_host,
            logs_dir=logs_dir_host,
            zap_target=zap_target,
            finding_policy=finding_policy_container,
            collect_metadata=collect_metadata,
            scan_scope=scan_scope,
            exclude_paths=exclude_paths,
            scan_id=scan_id,
        )
        
        self.log_message("Executing docker-compose command...")
        self.log_message(f"Full command: {' '.join(cmd)}")
        
        # Execute docker-compose asynchronously
        try:
            # Create async subprocess
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            
            # Write to log file and call callback
            with open(self.log_file, "a", encoding="utf-8") as log_f:
                log_f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting docker-compose command\n")
                
                try:
                    while True:
                        line = await self.process.stdout.readline()
                        if not line:
                            break
                        
                        line_str = line.decode('utf-8', errors='ignore').rstrip()
                        print(line_str)
                        log_f.write(line_str + "\n")
                        log_f.flush()
                        
                        # Store output line for analysis
                        self.output_lines.append(line_str)
                        
                        # Call output callback if provided
                        if output_callback:
                            output_callback(line_str)
                except asyncio.CancelledError:
                    # Handle cancellation - stop the process
                    self.log_message("Scan cancelled, stopping docker-compose process...", "WARNING")
                    if self.process and self.process.returncode is None:
                        self.process.terminate()
                        try:
                            await asyncio.wait_for(self.process.wait(), timeout=5.0)
                        except asyncio.TimeoutError:
                            self.log_message("Process didn't terminate, force killing...", "WARNING")
                            self.process.kill()
                            await self.process.wait()
                    raise
            
            # Wait for process to finish
            exit_code = await self.process.wait()
            
            # Log exit code
            with open(self.log_file, "a", encoding="utf-8") as log_f:
                log_f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Docker Compose exit code: {exit_code}\n")
            
            # Exit code 0 = all security scans succeeded (HTML report errors are non-critical)
            # Exit code != 0 = actual security scan failed
            if exit_code == 0:
                self.log_message("Security scan completed successfully!", "SUCCESS")
                self.overall_success = True
            else:
                self.log_message(f"Docker Compose command failed with exit code: {exit_code}", "ERROR")
                self.log_message("One or more security scans encountered errors", "ERROR")
                self.overall_success = False
                
        except asyncio.CancelledError:
            # Re-raise cancellation
            raise
        except Exception as e:
            self.log_message(f"Error executing docker-compose: {e}", "ERROR")
            self.overall_success = False
        finally:
            # Ensure process is stopped
            if self.process and self.process.returncode is None:
                self.log_message("Cleaning up docker-compose process...", "WARNING")
                try:
                    self.process.terminate()
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    self.process.kill()
                    await self.process.wait()
                except Exception as e:
                    self.log_message(f"Error cleaning up process: {e}", "WARNING")
        
        # Parse scanner statuses from output and save to JSON file
        scanner_statuses = self._parse_scanner_statuses()
        if scanner_statuses and results_dir:
            scanner_status_file = os.path.join(results_dir, "scanner-statuses.json")
            try:
                with open(scanner_status_file, "w", encoding="utf-8") as f:
                    json.dump(scanner_statuses, f, indent=2)
                self.log_message(f"Scanner statuses saved to: {scanner_status_file}")
            except Exception as e:
                self.log_message(f"Failed to save scanner statuses: {e}", "WARNING")
        
        # Cleanup temp snapshot
        if temp_snapshot_dir and os.path.exists(temp_snapshot_dir):
            try:
                shutil.rmtree(temp_snapshot_dir)
                self.log_message(f"Cleaned up temporary snapshot: {temp_snapshot_dir}")
            except Exception as e:
                self.log_message(f"Failed to cleanup temp snapshot: {e}", "WARNING")
        
        return self.overall_success
    
    def _parse_scanner_statuses(self) -> Dict[str, str]:
        """
        Parse scanner statuses from output lines.
        Looks for lines like "  Semgrep:       SUCCESS" or "  Trivy:         FAILED"
        
        Returns:
            Dictionary mapping scanner names to their status (SUCCESS, FAILED, SKIPPED, N/A)
        """
        scanner_statuses = {}
        
        if not self.output_lines:
            return scanner_statuses
        
        # Pattern to match: "  ScannerName:       STATUS"
        # Matches scanner names with optional hyphens/underscores
        pattern = r'\s+([A-Za-z][A-Za-z0-9_-]+):\s+(SUCCESS|FAILED|SKIPPED|N/A)'
        
        # Look for "Scanner Status Summary" section
        in_summary_section = False
        for line in self.output_lines:
            # Check if we're in the summary section
            if "Scanner Status Summary" in line or "Scanner Status" in line:
                in_summary_section = True
                continue
            
            # Stop parsing if we hit the next section
            if in_summary_section and ("Key Results Location" in line or "FINAL STATUS" in line or "===" in line):
                break
            
            # Parse scanner status lines
            if in_summary_section:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    scanner_name = match.group(1)
                    status = match.group(2).upper()
                    scanner_statuses[scanner_name] = status
        
        return scanner_statuses