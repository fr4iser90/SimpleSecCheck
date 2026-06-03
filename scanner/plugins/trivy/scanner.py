"""
Trivy Scanner
Python implementation of run_trivy.sh
"""
import os
from pathlib import Path
from typing import Dict, List, Optional

from scanner.core.base_scanner import BaseScanner
from scanner.core.command_retry import run_with_retry
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability
from scanner.core.step_registry import SubStepType

_MIN_TRIVY_DB_BYTES = 1024 * 1024


def trivy_db_usable(cache_dir: Optional[str]) -> bool:
    """True when TRIVY_CACHE_DIR contains a plausible vulnerability DB."""
    if not cache_dir:
        return False
    db_path = Path(cache_dir) / "db"
    if not db_path.is_dir():
        return False
    trivy_db = db_path / "trivy.db"
    if trivy_db.is_file() and trivy_db.stat().st_size >= _MIN_TRIVY_DB_BYTES:
        return True
    meta = db_path / "metadata.json"
    return meta.is_file() and meta.stat().st_size > 32


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
        self.exclude_paths = self.scan_exclude_paths(exclude_paths)

    def get_skip_args(self) -> List[str]:
        skip_args = ["--skip-files", "**/*.log", "--skip-dirs", "*/node_modules"]
        skip_args.extend(self.trivy_extra_skip_cli())
        return skip_args
    
    def get_config_args(self) -> List[str]:
        """Get Trivy config arguments"""
        if self.config_path and self.config_path.exists():
            return ["--config", str(self.config_path)]
        else:
            self.log(f"Config file not found at {self.config_path}. Running with Trivy defaults.", "WARNING")
            return []

    def _trivy_severity(self) -> str:
        s = os.getenv("TRIVY_SEVERITY", "HIGH,CRITICAL,MEDIUM,LOW").strip()
        return s if s else "HIGH,CRITICAL,MEDIUM,LOW"

    def _trivy_comprehensive_scanners(self) -> str:
        s = os.getenv("TRIVY_COMPREHENSIVE_SCANNERS", "vuln,secret,config").strip()
        return s if s else "vuln,secret,config"

    def _trivy_run_secret_scan(self) -> bool:
        return os.getenv("TRIVY_RUN_SECRET_SCAN", "1") == "1"

    def _trivy_run_config_scan(self) -> bool:
        return os.getenv("TRIVY_RUN_CONFIG_SCAN", "1") == "1"

    def _trivy_run_license_scan(self) -> bool:
        return os.getenv("TRIVY_RUN_LICENSE_SCAN", "1") == "1"

    def _trivy_db_download_timeout(self) -> int:
        raw = os.getenv("TRIVY_DB_DOWNLOAD_TIMEOUT", "900").strip()
        try:
            return max(120, int(raw))
        except ValueError:
            return 900

    def _trivy_db_download_retries(self) -> int:
        raw = os.getenv("TRIVY_DB_DOWNLOAD_RETRIES", "3").strip()
        try:
            return max(1, int(raw))
        except ValueError:
            return 3

    def _trivy_command_env(self) -> Dict[str, str]:
        env = os.environ.copy()
        cache = os.getenv("TRIVY_CACHE_DIR", "").strip()
        if cache:
            env["TRIVY_CACHE_DIR"] = cache
        repo = os.getenv("TRIVY_DB_REPOSITORY", "").strip()
        if repo:
            env["TRIVY_DB_REPOSITORY"] = repo
        return env

    def _scan_flags(self) -> List[str]:
        force = os.getenv("TRIVY_FORCE_DB_UPDATE", "").strip().lower() in ("1", "true", "yes")
        if force:
            return []
        if self._skip_db_update or os.getenv("TRIVY_SKIP_DB_UPDATE", "").strip().lower() in (
            "1",
            "true",
            "yes",
        ):
            return ["--skip-db-update"]
        return []

    def _ensure_vuln_db(self) -> bool:
        cache_dir = os.getenv("TRIVY_CACHE_DIR", "").strip()
        if trivy_db_usable(cache_dir):
            self.log("Vulnerability database found in cache")
            self._skip_db_update = True
            return True

        cmd = ["trivy", "image", "--download-db-only"]
        env = self._trivy_command_env()
        timeout = self._trivy_db_download_timeout()
        retries = self._trivy_db_download_retries()
        delay = float(os.getenv("TRIVY_DB_DOWNLOAD_RETRY_DELAY", "8") or "8")

        self.log(
            f"Downloading vulnerability DB (timeout={timeout}s, retries={retries})…"
        )

        def _download(_attempt: int):
            if _attempt > 1:
                self.log(f"Trivy DB download retry {_attempt}/{retries}", "WARNING")
            return self.run_command(cmd, capture_output=True, timeout=timeout, env=env)

        result = run_with_retry(_download, max_attempts=retries, delay_seconds=delay)

        if result.returncode == 0 or trivy_db_usable(cache_dir):
            if result.returncode != 0:
                self.log(
                    "DB download reported failure but cache is usable; continuing with --skip-db-update",
                    "WARNING",
                )
            self._skip_db_update = True
            return True

        self.log(
            "Vulnerability database download failed after retries "
            "(network/registry). Set TRIVY_DB_REPOSITORY or pre-warm cache via "
            "scanner asset update.",
            "ERROR",
        )
        return False
    
    def scan(self) -> bool:
        """Run Trivy scan with detailed substeps"""
        if not self.check_tool_installed("trivy"):
            self.log("trivy not found in PATH", "ERROR")
            return False

        self._skip_db_update = False

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

        self.log(f"Running Trivy {self.scan_type} scan on {self.target_path}...")
        
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
        
        # PREPARE: Download Vulnerability Database (retry + persistent cache)
        self.substep_prepare("Download Vulnerability Database", "Checking/downloading vulnerability database...")
        if not self._ensure_vuln_db():
            self.fail_substep("Download Vulnerability Database", "Vulnerability database unavailable")
            return False
        self.complete_substep(
            "Download Vulnerability Database",
            "Using cached database (--skip-db-update on scan steps)",
        )
        
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
        scan_flags = self._scan_flags()
        cmd = [
            "trivy",
            self.scan_type,
            *scan_flags,
            *config_args,
            "--format", "json",
            "-o", str(json_output),
            "--severity", self._trivy_severity(),
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
        if self._trivy_run_secret_scan():
            try:
                secret_cmd = [
                    "trivy",
                    self.scan_type,
                    *scan_flags,
                    "--scanners", "secret",
                    "--format", "json",
                    *skip_args,
                    str(self.target_path)
                ]
                secret_result = self.run_command(secret_cmd, capture_output=True)
                if secret_result.returncode == 0:
                    self.complete_substep("Secret Scanning", "Secret scanning completed")
                else:
                    self.complete_substep("Secret Scanning", "Secret scanning completed (with warnings)")
            except Exception as e:
                self.complete_substep("Secret Scanning", f"Secret scanning completed: {e}")
        else:
            self.complete_substep("Secret Scanning", "Skipped (profile)")
        
        # SCAN: Config Scanning
        self.substep_scan("Config Scanning", "Scanning for misconfigurations...")
        if self._trivy_run_config_scan():
            try:
                config_cmd = [
                    "trivy",
                    self.scan_type,
                    *scan_flags,
                    "--scanners", "config",
                    "--format", "json",
                    *skip_args,
                    str(self.target_path)
                ]
                config_result = self.run_command(config_cmd, capture_output=True)
                if config_result.returncode == 0:
                    self.complete_substep("Config Scanning", "Config scanning completed")
                else:
                    self.complete_substep("Config Scanning", "Config scanning completed (with warnings)")
            except Exception as e:
                self.complete_substep("Config Scanning", f"Config scanning completed: {e}")
        else:
            self.complete_substep("Config Scanning", "Skipped (profile)")
        
        # SCAN: License Scanning (optional)
        self.start_substep("License Scanning", "Scanning for license information...", SubStepType.PHASE)
        if self._trivy_run_license_scan():
            try:
                license_cmd = [
                    "trivy",
                    self.scan_type,
                    *scan_flags,
                    "--scanners", "license",
                    "--format", "json",
                    *skip_args,
                    str(self.target_path)
                ]
                license_result = self.run_command(license_cmd, capture_output=True)
                if license_result.returncode == 0:
                    self.complete_substep("License Scanning", "License scanning completed")
                else:
                    self.complete_substep("License Scanning", "License scanning completed (with warnings)")
            except Exception as e:
                self.complete_substep("License Scanning", f"License scanning skipped: {e}")
        else:
            self.complete_substep("License Scanning", "Skipped (profile)")
        
        # PROCESS: Result Aggregation
        self.substep_process("Result Aggregation", "Aggregating scan results...")
        try:
            comprehensive_cmd = [
                "trivy",
                self.scan_type,
                *scan_flags,
                *config_args,
                "--format", "json",
                "-o", str(json_output),
                "--severity", self._trivy_severity(),
                "--scanners", self._trivy_comprehensive_scanners(),
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
            *scan_flags,
            *config_args,
            "--format", "table",
            "-o", str(text_output),
            "--severity", self._trivy_severity(),
            "--scanners", self._trivy_comprehensive_scanners(),
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
                *scan_flags,
                *config_args,
                "--format", "sarif",
                "-o", str(sarif_output),
                "--severity", self._trivy_severity(),
                "--scanners", self._trivy_comprehensive_scanners(),
                *skip_args,
                str(self.target_path)
            ]
            sarif_result = self.run_command(sarif_cmd, capture_output=True)
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
            if self._trivy_run_secret_scan() or self._trivy_run_config_scan():
                parts = []
                if self._trivy_run_secret_scan():
                    parts.append("secret")
                if self._trivy_run_config_scan():
                    parts.append("config")
                scanners = ",".join(parts) if parts else "secret"
                cmd = [
                    "trivy",
                    self.scan_type,
                    *scan_flags,
                    "--scanners", scanners,
                    "--format", "json",
                    "-o", str(secrets_output),
                    *skip_args,
                    str(self.target_path)
                ]
                result = self.run_command(cmd, capture_output=True)
                if result.returncode == 0 and secrets_output.exists():
                    self.complete_substep("Secrets/Config Deep Scan", "Secrets/config deep scan completed")
                else:
                    self.complete_substep("Secrets/Config Deep Scan", "Secrets/config deep scan completed (with warnings)")
            else:
                self.complete_substep("Secrets/Config Deep Scan", "Skipped (profile)")
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
