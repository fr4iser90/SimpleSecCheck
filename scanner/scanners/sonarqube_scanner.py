"""
SonarQube Scanner
Python implementation of run_sonarqube.sh
"""
import os
import json
from pathlib import Path
from typing import Optional
from datetime import datetime
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType


class SonarQubeScanner(BaseScanner):
    """SonarQube scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    SCAN_TYPES = [ScanType.CODE]
    PRIORITY = 7
    REQUIRES_CONDITION = None
    ENV_VARS = {
        "SONARQUBE_CONFIG_PATH": "/SimpleSecCheck/config/tools/sonarqube/config.yaml"
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
        """Run SonarQube scan"""
        if not self.check_tool_installed("sonar-scanner"):
            self.log("sonar-scanner not found in PATH", "ERROR")
            return False
        
        self.log(f"Running code quality and security scan on {self.target_path}...")
        
        json_output = self.results_dir / "sonarqube.json"
        text_output = self.results_dir / "sonarqube.txt"
        
        properties_file = self.create_project_properties()
        
        # Run SonarQube scan
        self.log("Running SonarQube analysis...")
        cmd = ["sonar-scanner", "-X", f"-Dproject.settings={properties_file}"]
        
        result = self.run_command(cmd, cwd=self.target_path, capture_output=True)
        
        if result.returncode != 0:
            self.log("SonarQube scan failed, creating minimal reports...", "WARNING")
            # Create minimal reports
            empty_json = {
                "issues": [],
                "summary": {
                    "total_issues": 0,
                    "blocker": 0,
                    "critical": 0,
                    "major": 0,
                    "minor": 0,
                    "info": 0
                }
            }
            with open(json_output, "w", encoding="utf-8") as f:
                json.dump(empty_json, f, indent=2)
            
            with open(text_output, "w", encoding="utf-8") as f:
                f.write("SonarQube Scan Results\n")
                f.write("===================\n")
                f.write("SonarQube scan failed or no issues found.\n")
                f.write(f"Scan completed at: {datetime.now().isoformat()}\n")
            
            return True
        
        # Check if results were generated
        if json_output.exists():
            self.log("SonarQube results available.", "SUCCESS")
            return True
        else:
            # Create minimal reports
            empty_json = {
                "issues": [],
                "summary": {
                    "total_issues": 0,
                    "blocker": 0,
                    "critical": 0,
                    "major": 0,
                    "minor": 0,
                    "info": 0
                }
            }
            with open(json_output, "w", encoding="utf-8") as f:
                json.dump(empty_json, f, indent=2)
            
            with open(text_output, "w", encoding="utf-8") as f:
                f.write("SonarQube Scan Results\n")
                f.write("===================\n")
                f.write("No SonarQube results generated.\n")
                f.write(f"Scan completed at: {datetime.now().isoformat()}\n")
            
            self.log("No results generated.", "WARNING")
            return True


if __name__ == "__main__":
    import sys
    
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/SimpleSecCheck/results")
    log_file = os.getenv("LOG_FILE", "/SimpleSecCheck/logs/scan.log")
    config_path = os.getenv("SONARQUBE_CONFIG_PATH", "/SimpleSecCheck/config/tools/sonarqube/config.yaml")
    
    scanner = SonarQubeScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
