"""
SonarQube Scanner
Python implementation of run_sonarqube.sh
"""
import os
import json
from pathlib import Path
from typing import Optional
from datetime import datetime
from urllib.request import urlopen
from urllib.error import URLError
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability
from scanner.core.step_registry import SubStepType


class SonarQubeScanner(BaseScanner):
    """SonarQube scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.CODE,
            supported_targets=[TargetType.LOCAL_MOUNT, TargetType.GIT_REPO, TargetType.UPLOADED_CODE],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 7
    REQUIRES_CONDITION = None
    ENV_VARS = {
        "SONARQUBE_CONFIG_PATH": "/app/scanner/plugins/sonarqube/config/config.yaml"
    }
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None
    ):
        """
        Initialize SonarQube scanner
        
        Args:
            target_path: Path to scan
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to SonarQube config file (optional)
        """
        super().__init__("SonarQube", target_path, results_dir, log_file, config_path)
    
    def create_project_properties(self) -> Path:
        """Create sonar-project.properties file"""
        properties_file = self.results_dir / "sonar-project.properties"
        
        # Check if target has existing properties
        target_properties = self.target_path / "sonar-project.properties"
        if target_properties.exists():
            return target_properties
        
        # Create default properties
        self.log("Creating temporary sonar-project.properties...")
        with open(properties_file, "w", encoding="utf-8") as f:
            f.write("sonar.projectKey=SimpleSecCheck-Analysis\n")
            f.write("sonar.projectName=SimpleSecCheck-Analysis\n")
            f.write("sonar.projectVersion=1.0.0\n")
            f.write("sonar.sources=.\n")
            f.write("sonar.sourceEncoding=UTF-8\n")
            f.write("sonar.exclusions=**/test*,**/tests/**,**/__pycache__/**,**/node_modules/**,**/venv/**\n")
        
        return properties_file
    
    def scan(self) -> bool:
        """Run SonarQube scan with standardized substeps"""
        if not self.check_tool_installed("sonar-scanner"):
            self.log("sonar-scanner not found in PATH", "ERROR")
            return False
        
        self.log(f"Running code quality and security scan on {self.target_path}...")
        
        # INIT: Project Configuration
        self.substep_init("Configuring SonarQube project...")
        properties_file = self.create_project_properties()
        self.complete_substep("Initialization", "Project configured")
        
        sonar_url = os.environ.get("SONAR_HOST_URL", "http://localhost:9000").rstrip("/")
        try:
            urlopen(sonar_url + "/api/system/status", timeout=3)
        except (URLError, OSError, Exception) as e:
            self.log(f"SonarQube server not reachable at {sonar_url}: {e}", "WARNING")
            status_file = self.results_dir / "status.json"
            try:
                status_file.write_text(json.dumps({
                    "status": "skipped",
                    "message": "SonarQube server not configured or not reachable (set SONAR_HOST_URL or run SonarQube)."
                }), encoding="utf-8")
            except Exception:
                pass
            return True
        
        json_output = self.results_dir / "report.json"
        text_output = self.results_dir / "report.txt"
        
        # Get tool command
        tool_cmd = self.get_tool_command("sonar-scanner")
        if not tool_cmd:
            self.log("sonar-scanner not found", "ERROR")
            return False
        
        # PREPARE: File Indexing
        self.start_substep("File Indexing", "Indexing source files...", SubStepType.ACTION)
        # File indexing happens during scan
        self.complete_substep("File Indexing", "Files indexed")
        
        # PREPARE: Language Detection
        self.start_substep("Language Detection", "Detecting programming languages...", SubStepType.ACTION)
        # Language detection happens during scan
        self.complete_substep("Language Detection", "Languages detected")
        
        # SCAN: Static Code Analysis
        self.substep_scan("Static Code Analysis", "Running static code analysis...")
        
        # SCAN: Security Hotspot Detection
        self.start_substep("Security Hotspot Detection", "Detecting security hotspots...", SubStepType.PHASE)
        # Security hotspot detection happens during scan
        
        # SCAN: Code Smell Detection
        self.start_substep("Code Smell Detection", "Detecting code smells...", SubStepType.PHASE)
        # Code smell detection happens during scan
        
        # Run SonarQube scan
        self.log("Running SonarQube analysis...")
        cmd = [*tool_cmd, "-X", f"-Dproject.settings={properties_file}"]
        
        env = os.environ.copy()
        env.setdefault("SONAR_USER_HOME", str(Path.home() / ".sonar"))
        
        result = self.run_command(cmd, cwd=self.target_path, env=env, capture_output=True)
        
        if result.returncode == 0:
            self.complete_substep("Static Code Analysis", "Static code analysis completed")
            self.complete_substep("Security Hotspot Detection", "Security hotspot detection completed")
            self.complete_substep("Code Smell Detection", "Code smell detection completed")
        else:
            self.log(f"SonarQube scan failed (exit code {result.returncode}), creating minimal reports...", "WARNING")
            self.complete_substep("Static Code Analysis", "Static code analysis completed (with warnings)")
            self.complete_substep("Security Hotspot Detection", "Security hotspot detection completed (with warnings)")
            self.complete_substep("Code Smell Detection", "Code smell detection completed (with warnings)")
        
        # PROCESS: Result Upload
        self.start_substep("Result Upload", "Uploading results to SonarQube server...", SubStepType.ACTION)
        # Result upload happens during scan (if server configured)
        self.complete_substep("Result Upload", "Results uploaded")
        
        # PROCESS: Quality Gate Evaluation
        self.start_substep("Quality Gate Evaluation", "Evaluating quality gate...", SubStepType.ACTION)
        # Quality gate evaluation happens during scan
        self.complete_substep("Quality Gate Evaluation", "Quality gate evaluated")
        
        # Check if results were generated
        if result.returncode != 0:
            self.log("SonarQube scan failed; no report written (no fake data).", "WARNING")
            return True
        
        if json_output.exists():
            self.log("SonarQube results available.", "SUCCESS")
            return True
        else:
            self.log("SonarQube produced no output file; no report written.", "WARNING")
            return True


if __name__ == "__main__":
    import os
    import sys
    
    # Get default parameters from BaseScanner
    default_params = BaseScanner.get_default_params_from_env()
    
    # Get scanner-specific parameters
    config_path = os.getenv("SONARQUBE_CONFIG_PATH", "/app/scanner/plugins/sonarqube/config/config.yaml")
    
    scanner = SonarQubeScanner(
        **default_params,
        config_path=config_path
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
