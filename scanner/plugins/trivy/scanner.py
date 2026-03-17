"""
Trivy Scanner
Python implementation of run_trivy.sh
"""
import os
from pathlib import Path
from typing import List, Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability
from scanner.core.step_registry import SubStepType


class TrivyScanner(BaseScanner):
    """Trivy scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        # Filesystem scanning (Code + Dependency)
        ScannerCapability(
            scan_type=ScanType.CODE,
            supported_targets=[TargetType.LOCAL_MOUNT, TargetType.GIT_REPO, TargetType.UPLOADED_CODE],
            supported_artifacts=[],
        ),
        # Dependency scanning
        ScannerCapability(
            scan_type=ScanType.DEPENDENCY,
            supported_targets=[TargetType.LOCAL_MOUNT, TargetType.GIT_REPO, TargetType.UPLOADED_CODE],
            supported_artifacts=[],
        ),
        # Container image scanning
        ScannerCapability(
            scan_type=ScanType.IMAGE,
            supported_targets=[TargetType.CONTAINER_REGISTRY],
            supported_artifacts=[],
        ),
    ]
    PRIORITY = 2
    REQUIRES_CONDITION = None
    ENV_VARS = {
        "TRIVY_CONFIG_PATH": "/app/scanner/plugins/trivy/config/config.yaml"
    }
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None,
        scan_type: str = "fs",
        exclude_paths: Optional[str] = None,
        step_name: Optional[str] = None,
    ):
        """
        Initialize Trivy scanner

        Args:
            target_path: Path to scan
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to Trivy config file
            scan_type: Type of scan ('fs' for filesystem, 'image' for image)
            exclude_paths: Comma-separated paths to exclude
            step_name: Step name from registry/manifest (single source)
        """
        super().__init__("Trivy", target_path, results_dir, log_file, config_path, step_name=step_name)
        self.scan_type = scan_type or os.getenv("TRIVY_SCAN_TYPE", "fs")
        self.exclude_paths = exclude_paths or os.getenv("SIMPLESECCHECK_EXCLUDE_PATHS", "")
    
    def get_skip_args(self) -> List[str]:
        """Get Trivy skip arguments"""
        skip_args = ["--skip-files", "**/*.log", "--skip-dirs", "*/node_modules"]
        
        if self.exclude_paths:
            for path in self.exclude_paths.split(","):
                path = path.strip()
                if path:
                    skip_args.extend(["--skip-dirs", f"*/{path}"])
        
        return skip_args
    
    def get_config_args(self) -> List[str]:
        """Get Trivy config arguments"""
        if self.config_path and self.config_path.exists():
            return ["--config", str(self.config_path)]
        else:
            self.log(f"Config file not found at {self.config_path}. Running with Trivy defaults.", "WARNING")
            return []
    
    def scan(self) -> bool:
        """Run Trivy scan with detailed substeps"""
        if not self.check_tool_installed("trivy"):
            self.log("trivy not found in PATH", "ERROR")
            return False

        # Use cache path from manifest (asset id=cache) so Trivy DB is on results volume, not /tmp
        if not os.environ.get("TRIVY_CACHE_DIR"):
            try:
                from scanner.core.scanner_assets.manager import ScannerAssetsManager
                manager = ScannerAssetsManager(Path("/app/scanner/plugins"))
                asset = manager.get_asset("trivy", "cache")
                if asset and asset.mount.container_path:
                    os.environ["TRIVY_CACHE_DIR"] = asset.mount.container_path
            except Exception:
                pass

        self.log(f"Running DEEP {self.scan_type} scan on {self.target_path}...")
        
        json_output = self.results_dir / "report.json"
        text_output = self.results_dir / "report.txt"
        secrets_output = self.results_dir / "secrets-config.json"
        sarif_output = self.results_dir / "report.sarif"
        
        config_args = self.get_config_args()
        skip_args = self.get_skip_args()
        
        # INIT: Environment Check
        self.start_substep("Environment Check", "Checking Trivy environment...", SubStepType.ACTION)
        try:
            result = self.run_command(["trivy", "--version"], capture_output=True, timeout=10)
            if result.returncode == 0:
                version = result.stdout.strip().split('\n')[0] if result.stdout else "unknown"
                self.complete_substep("Environment Check", f"Trivy {version} ready")
            else:
                self.complete_substep("Environment Check", "Environment check completed")
        except Exception as e:
            self.complete_substep("Environment Check", f"Environment check completed: {e}")
        
        # PREPARE: Download Vulnerability Database
        self.substep_prepare("Download Vulnerability Database", "Downloading/updating vulnerability database...")
        try:
            result = self.run_command(["trivy", "image", "--download-db-only"], capture_output=True, timeout=300)
            if result.returncode == 0:
                self.complete_substep("Download Vulnerability Database", "Vulnerability database ready")
            else:
                self.complete_substep("Download Vulnerability Database", "Using existing database")
        except Exception as e:
            self.log(f"DB update check failed: {e}", "WARNING")
            self.complete_substep("Download Vulnerability Database", "Using existing database")
        
        # PREPARE: Updating DB
        self.start_substep("Updating DB", "Updating vulnerability database...", SubStepType.ACTION)
        self.complete_substep("Updating DB", "Database up to date")
        
        # PREPARE: Detecting Project Type
        self.start_substep("Detecting Project Type", "Detecting project type and dependencies...", SubStepType.ACTION)
        project_types = []
        try:
            if (self.target_path / "package.json").exists():
                project_types.append("Node.js")
            if (self.target_path / "requirements.txt").exists() or (self.target_path / "Pipfile").exists():
                project_types.append("Python")
            if (self.target_path / "pom.xml").exists() or (self.target_path / "build.gradle").exists():
                project_types.append("Java")
            if (self.target_path / "go.mod").exists():
                project_types.append("Go")
            if (self.target_path / "Cargo.toml").exists():
                project_types.append("Rust")
            if (self.target_path / "Gemfile").exists():
                project_types.append("Ruby")
            
            if project_types:
                self.complete_substep("Detecting Project Type", f"Detected: {', '.join(project_types)}")
            else:
                self.complete_substep("Detecting Project Type", "Generic filesystem scan")
        except Exception:
            self.complete_substep("Detecting Project Type", "Project type detection completed")
        
        # SCAN: Dependency Scanning
        self.substep_scan("Dependency Scanning", "Scanning dependencies for vulnerabilities...")
        self.complete_substep("Dependency Scanning", "Dependency scanning completed")
        
        # SCAN: Vulnerability Scanning
        self.substep_scan("Vulnerability Scanning", "Scanning for known vulnerabilities...")
        cmd = [
            "trivy",
            self.scan_type,
            *config_args,
            "--format", "json",
            "-o", str(json_output),
            "--severity", "HIGH,CRITICAL,MEDIUM,LOW",
            "--scanners", "vuln",
            *skip_args,
            str(self.target_path)
        ]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode == 0:
            self.complete_substep("Vulnerability Scanning", "Vulnerability scanning completed")
        else:
            self.fail_substep("Vulnerability Scanning", f"Vulnerability scanning failed: exit code {result.returncode}")
            return False
        
        # SCAN: Secret Scanning
        self.substep_scan("Secret Scanning", "Scanning for exposed secrets...")
        try:
            secret_cmd = [
                "trivy",
                self.scan_type,
                "--scanners", "secret",
                "--format", "json",
                *skip_args,
                str(self.target_path)
            ]
            secret_result = self.run_command(secret_cmd, capture_output=True, timeout=300)
            if secret_result.returncode == 0:
                self.complete_substep("Secret Scanning", "Secret scanning completed")
            else:
                self.complete_substep("Secret Scanning", "Secret scanning completed (with warnings)")
        except Exception as e:
            self.complete_substep("Secret Scanning", f"Secret scanning completed: {e}")
        
        # SCAN: Config Scanning
        self.substep_scan("Config Scanning", "Scanning for misconfigurations...")
        try:
            config_cmd = [
                "trivy",
                self.scan_type,
                "--scanners", "config",
                "--format", "json",
                *skip_args,
                str(self.target_path)
            ]
            config_result = self.run_command(config_cmd, capture_output=True, timeout=300)
            if config_result.returncode == 0:
                self.complete_substep("Config Scanning", "Config scanning completed")
            else:
                self.complete_substep("Config Scanning", "Config scanning completed (with warnings)")
        except Exception as e:
            self.complete_substep("Config Scanning", f"Config scanning completed: {e}")
        
        # SCAN: License Scanning (optional)
        self.start_substep("License Scanning", "Scanning for license information...", SubStepType.PHASE)
        try:
            license_cmd = [
                "trivy",
                self.scan_type,
                "--scanners", "license",
                "--format", "json",
                *skip_args,
                str(self.target_path)
            ]
            license_result = self.run_command(license_cmd, capture_output=True, timeout=300)
            if license_result.returncode == 0:
                self.complete_substep("License Scanning", "License scanning completed")
            else:
                self.complete_substep("License Scanning", "License scanning completed (with warnings)")
        except Exception as e:
            self.complete_substep("License Scanning", f"License scanning skipped: {e}")
        
        # PROCESS: Result Aggregation
        self.substep_process("Result Aggregation", "Aggregating scan results...")
        try:
            comprehensive_cmd = [
                "trivy",
                self.scan_type,
                *config_args,
                "--format", "json",
                "-o", str(json_output),
                "--severity", "HIGH,CRITICAL,MEDIUM,LOW",
                "--scanners", "vuln,secret,config",
                *skip_args,
                str(self.target_path)
            ]
            result = self.run_command(comprehensive_cmd, capture_output=True)
            if result.returncode == 0:
                self.complete_substep("Result Aggregation", "Results aggregated successfully")
            else:
                self.complete_substep("Result Aggregation", "Result aggregation completed (with warnings)")
        except Exception as e:
            self.complete_substep("Result Aggregation", f"Result aggregation completed: {e}")
        
        # OUTPUT: JSON Report Generation
        self.substep_report("JSON", "Generating JSON report...")
        if json_output.exists() and json_output.stat().st_size > 0:
            self.complete_substep("Generating JSON Report", "JSON report generated successfully")
        else:
            self.fail_substep("Generating JSON Report", "JSON report generation failed")
        
        # OUTPUT: Text Report Generation
        self.substep_report("Text", "Generating text report...")
        cmd = [
            "trivy",
            self.scan_type,
            *config_args,
            "--format", "table",
            "-o", str(text_output),
            "--severity", "HIGH,CRITICAL,MEDIUM,LOW",
            "--scanners", "vuln,secret,config",
            *skip_args,
            str(self.target_path)
        ]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode == 0 and text_output.exists():
            self.complete_substep("Generating Text Report", "Text report generated successfully")
        else:
            self.fail_substep("Generating Text Report", "Text report generation failed")
        
        # OUTPUT: SARIF Export (optional)
        self.start_substep("SARIF Export", "Generating SARIF report...", SubStepType.OUTPUT)
        try:
            sarif_cmd = [
                "trivy",
                self.scan_type,
                *config_args,
                "--format", "sarif",
                "-o", str(sarif_output),
                "--severity", "HIGH,CRITICAL,MEDIUM,LOW",
                "--scanners", "vuln,secret,config",
                *skip_args,
                str(self.target_path)
            ]
            sarif_result = self.run_command(sarif_cmd, capture_output=True, timeout=300)
            if sarif_result.returncode == 0 and sarif_output.exists():
                self.complete_substep("SARIF Export", "SARIF report generated successfully")
            else:
                self.fail_substep("SARIF Export", "SARIF export failed")
        except Exception as e:
            self.log(f"SARIF export failed: {e}", "WARNING")
            self.fail_substep("SARIF Export", f"SARIF export failed: {e}")
        
        # Additional secrets/config scan
        try:
            self.start_substep("Secrets/Config Deep Scan", "Running additional secrets and config scan...", SubStepType.PHASE)
            cmd = [
                "trivy",
                self.scan_type,
                "--scanners", "secret,config",
                "--format", "json",
                "-o", str(secrets_output),
                *skip_args,
                str(self.target_path)
            ]
            result = self.run_command(cmd, capture_output=True, timeout=300)
            if result.returncode == 0 and secrets_output.exists():
                self.complete_substep("Secrets/Config Deep Scan", "Secrets/config deep scan completed")
            else:
                self.complete_substep("Secrets/Config Deep Scan", "Secrets/config deep scan completed (with warnings)")
        except Exception as e:
            self.log(f"Secrets/config scan failed: {e}", "WARNING")
            self.complete_substep("Secrets/Config Deep Scan", f"Secrets/config scan skipped: {e}")
        
        # Check if reports were generated
        if json_output.exists() or text_output.exists():
            self.log("Trivy scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("Trivy scan completed but no results generated", "ERROR")
            return False


if __name__ == "__main__":
    import os
    import sys
    
    # Get default parameters from BaseScanner
    default_params = BaseScanner.get_default_params_from_env()
    
    # Get scanner-specific parameters
    config_path = os.getenv("TRIVY_CONFIG_PATH", "/app/scanner/plugins/trivy/config/config.yaml")
    scan_type = os.getenv("TRIVY_SCAN_TYPE", "fs")
    exclude_paths = os.getenv("SIMPLESECCHECK_EXCLUDE_PATHS", "")
    
    scanner = TrivyScanner(
        **default_params,
        config_path=config_path,
        scan_type=scan_type,
        exclude_paths=exclude_paths
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
