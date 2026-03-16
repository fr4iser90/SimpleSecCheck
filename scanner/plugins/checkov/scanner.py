"""
Checkov Scanner
Python implementation of run_checkov.sh
"""
import os
from pathlib import Path
from typing import List, Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability
from scanner.core.step_registry import SubStepType


class CheckovScanner(BaseScanner):
    """Checkov scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.CONFIG,
            supported_targets=[TargetType.LOCAL_MOUNT, TargetType.GIT_REPO, TargetType.UPLOADED_CODE],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 12
    REQUIRES_CONDITION = None
    ENV_VARS = {
        "CHECKOV_CONFIG_PATH": "/app/scanner/plugins/checkov/config/config.yaml"
    }
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None,
        exclude_paths: Optional[str] = None
    ):
        """
        Initialize Checkov scanner
        
        Args:
            target_path: Path to scan
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to Checkov config file (optional)
            exclude_paths: Comma-separated paths to exclude
        """
        super().__init__("Checkov", target_path, results_dir, log_file, config_path)
        self.exclude_paths = exclude_paths or os.getenv("SIMPLESECCHECK_EXCLUDE_PATHS", "")
    
    def find_infra_files(self) -> List[Path]:
        """Find infrastructure files"""
        infra_files = []
        patterns = [
            "*.tf", "*.tfvars", "*.yml", "*.yaml", "Dockerfile",
            "docker-compose.yml", "docker-compose.yaml", "*.json",
            "*.tfstate", "cloudformation.yaml", "cloudformation.yml",
            "serverless.yml", "serverless.yaml"
        ]
        
        for pattern in patterns:
            for file in self.target_path.rglob(pattern):
                # Check exclude paths
                skip = False
                if self.exclude_paths:
                    for exclude in self.exclude_paths.split(","):
                        exclude = exclude.strip()
                        if exclude and exclude in str(file):
                            skip = True
                            break
                
                if not skip:
                    infra_files.append(file)
        
        return infra_files
    
    def get_skip_args(self) -> List[str]:
        """Get Checkov skip arguments"""
        skip_args = []
        
        if self.exclude_paths:
            for path in self.exclude_paths.split(","):
                path = path.strip()
                if path:
                    skip_args.extend(["--skip-path", path])
        
        return skip_args
    
    def scan(self) -> bool:
        """Run Checkov scan with standardized substeps"""
        if not self.check_tool_installed("checkov"):
            self.log("Checkov CLI not found, skipping scan.", "WARNING")
            return True
        
        # INIT: Initialization
        self.substep_init("Initializing Checkov scan...")
        self.complete_substep("Initialization", "Checkov initialized")
        
        # PREPARE: Finding Infrastructure Files
        self.start_substep("Finding Infrastructure Files", "Scanning for infrastructure files...", SubStepType.ACTION)
        infra_files = self.find_infra_files()
        
        if not infra_files:
            self.complete_substep("Finding Infrastructure Files", "No infrastructure files found")
            self.log("No infrastructure files found, skipping scan.", "WARNING")
            return True
        
        self.complete_substep("Finding Infrastructure Files", f"Found {len(infra_files)} infrastructure file(s)")
        self.log(f"Found {len(infra_files)} infrastructure file(s).")
        self.log(f"Running infrastructure security scan on {self.target_path}...")
        
        # PREPARE: Parsing Infrastructure Files
        self.start_substep("Parsing Infrastructure Files", "Parsing infrastructure configuration files...", SubStepType.ACTION)
        # Parsing happens during scan
        self.complete_substep("Parsing Infrastructure Files", f"Parsed {len(infra_files)} file(s)")
        
        json_output = self.results_dir / "report.json"  # Changed from checkov-comprehensive.json
        text_output = self.results_dir / "report.txt"   # Changed from checkov-comprehensive.txt
        
        # Remove old directory if it exists
        if json_output.exists() and json_output.is_dir():
            import shutil
            shutil.rmtree(json_output, ignore_errors=True)
            self.log("Removed old directory at json_output path")
        
        skip_args = self.get_skip_args()
        
        # SCAN: Running Security Policies
        self.substep_scan("Running Security Policies", "Evaluating infrastructure against security policies...")
        
        # SCAN: Evaluating Misconfigurations
        self.start_substep("Evaluating Misconfigurations", "Checking for security misconfigurations...", SubStepType.PHASE)
        
        # Set environment variables to prevent multiprocessing issues
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = "0"
        env["OMP_NUM_THREADS"] = "1"
        env["MKL_NUM_THREADS"] = "1"
        cmd = ["checkov", "-d", str(self.target_path), *skip_args, "--output", "json", "--quiet"]
        
        result = self.run_command(cmd, capture_output=True, timeout=1800, env=env)
        wrote_json = False
        if result.stdout and result.stdout.strip():
            try:
                import json as _json
                data = _json.loads(result.stdout)
                if isinstance(data, dict) and ("results" in data or "failed_checks" in data):
                    with open(json_output, "w", encoding="utf-8") as f:
                        f.write(result.stdout)
                    wrote_json = True
                elif isinstance(data, list):
                    with open(json_output, "w", encoding="utf-8") as f:
                        f.write(result.stdout)
                    wrote_json = True
            except (ValueError, TypeError):
                pass
        if wrote_json:
            self.complete_substep("Running Security Policies", "Security policies evaluated")
            self.complete_substep("Evaluating Misconfigurations", "Misconfiguration evaluation completed")
        else:
            if result.returncode != 0:
                self.log("Checkov exited with findings (non-zero); no valid JSON in stdout, skipping report", "WARNING")
            self.complete_substep("Running Security Policies", "Security policies evaluated (with warnings)")
            self.complete_substep("Evaluating Misconfigurations", "Misconfiguration evaluation completed (with warnings)")
        
        # PROCESS: Result Processing
        self.substep_process("Result Processing", "Processing scan results...")
        self.complete_substep("Result Processing", "Results processed")
        
        # REPORT: JSON Report
        self.substep_report("JSON", "Generating JSON report...")
        if json_output.exists() and json_output.stat().st_size > 0:
            self.complete_substep("Generating JSON Report", "JSON report generated successfully")
        else:
            self.fail_substep("Generating JSON Report", "JSON report generation failed")
        
        # REPORT: Text Report
        self.start_substep("Generating Text Report", "Generating text report...", SubStepType.OUTPUT)
        self.log("Generating text report...")
        cmd = ["checkov", "-d", str(self.target_path), *skip_args, "--output", "cli", "--quiet"]
        
        result = self.run_command(cmd, capture_output=True, timeout=1800, env=env)
        if result.stdout and result.stdout.strip():
            with open(text_output, "w", encoding="utf-8") as f:
                f.write(result.stdout)
            self.complete_substep("Generating Text Report", "Text report generated successfully")
        else:
            self.log("Text report generation failed (no stdout)", "WARNING")
            self.fail_substep("Generating Text Report", "Text report generation failed")
            self.complete_substep("Text Report", "Text report skipped (no output)")
        
        if json_output.exists() or text_output.exists():
            self.log("Infrastructure security scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("No results generated", "WARNING")
            return True


if __name__ == "__main__":
    import os
    import sys
    
    # Get default parameters from BaseScanner
    default_params = BaseScanner.get_default_params_from_env()
    
    # Get scanner-specific parameters
    config_path = os.getenv("CHECKOV_CONFIG_PATH", "/app/scanner/plugins/checkov/config/config.yaml")
    exclude_paths = os.getenv("SIMPLESECCHECK_EXCLUDE_PATHS", "")
    
    scanner = CheckovScanner(
        **default_params,
        config_path=config_path,
        exclude_paths=exclude_paths
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
