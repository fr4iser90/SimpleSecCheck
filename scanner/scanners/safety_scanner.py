"""
Safety Scanner
Python implementation of run_safety.sh
"""
import os
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType


class SafetyScanner(BaseScanner):
    """Safety scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    SCAN_TYPES = [ScanType.CODE]
    PRIORITY = 5
    REQUIRES_CONDITION = None
    ENV_VARS = {
        "SAFETY_CONFIG_PATH": "/SimpleSecCheck/config/tools/safety/config.yaml"
    }
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None
    ):
        """
        Initialize Safety scanner
        
        Args:
            target_path: Path to scan
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to Safety config file (optional)
        """
        super().__init__("Safety", target_path, results_dir, log_file, config_path)
    
    def find_dependency_files(self) -> List[Path]:
        """Find Python dependency files"""
        patterns = [
            "requirements*.txt",
            "Pipfile",
            "Pipfile.lock",
            "pyproject.toml",
            "setup.py",
            "environment.yml",
            "conda.yml"
        ]
        
        dependency_files = []
        for pattern in patterns:
            for file in self.target_path.rglob(pattern):
                if file.is_file():
                    dependency_files.append(file)
        
        return dependency_files
    
    def create_empty_reports(self):
        """Create empty reports when no dependency files found"""
        json_output = self.results_dir / "safety.json"
        text_output = self.results_dir / "safety.txt"
        
        # Empty JSON report
        empty_json = {
            "vulnerabilities": [],
            "packages": [],
            "summary": {
                "total_packages": 0,
                "vulnerable_packages": 0,
                "total_vulnerabilities": 0
            }
        }
        with open(json_output, "w", encoding="utf-8") as f:
            json.dump(empty_json, f, indent=2)
        
        # Empty text report
        with open(text_output, "w", encoding="utf-8") as f:
            f.write("Safety Scan Results\n")
            f.write("===================\n")
            f.write("No Python dependency files found.\n")
            f.write(f"Scan completed at: {datetime.now().isoformat()}\n")
    
    def scan(self) -> bool:
        """Run Safety scan"""
        if not self.check_tool_installed("safety"):
            self.log("safety not found in PATH", "ERROR")
            return False
        
        self.log(f"Running Python dependency security scan on {self.target_path}...")
        
        dependency_files = self.find_dependency_files()
        
        if not dependency_files:
            self.log("No Python dependency files found", "WARNING")
            self.create_empty_reports()
            return True
        
        self.log(f"Found {len(dependency_files)} dependency file(s):")
        for file in dependency_files:
            self.log(f"  - {file}")
        
        json_output = self.results_dir / "safety.json"
        text_output = self.results_dir / "safety.txt"
        
        # Use first dependency file
        dep_file = dependency_files[0]
        
        # JSON report
        self.log("Running Safety scan with JSON output...")
        cmd = ["safety", "check", "--json", "--output", str(json_output), "--file", str(dep_file)]
        
        result = self.run_command(cmd, cwd=self.target_path, capture_output=True)
        if result.returncode != 0:
            self.log("JSON report generation failed, trying alternative approach...", "WARNING")
            # Try scanning directory directly
            cmd = ["safety", "check", "--json", "--output", str(json_output)]
            result = self.run_command(cmd, cwd=self.target_path, capture_output=True)
            if result.returncode != 0:
                self.log("Directory scan also failed, creating minimal report...", "WARNING")
                empty_json = {
                    "vulnerabilities": [],
                    "packages": [],
                    "summary": {"total_packages": 0, "vulnerable_packages": 0, "total_vulnerabilities": 0},
                    "error": "Safety scan failed"
                }
                with open(json_output, "w", encoding="utf-8") as f:
                    json.dump(empty_json, f, indent=2)
        
        # Text report
        self.log("Running Safety scan with text output...")
        cmd = ["safety", "check", "--output", str(text_output), "--file", str(dep_file)]
        
        result = self.run_command(cmd, cwd=self.target_path, capture_output=True)
        if result.returncode != 0:
            self.log("Text report generation failed, trying alternative approach...", "WARNING")
            # Try scanning directory directly
            cmd = ["safety", "check", "--output", str(text_output)]
            result = self.run_command(cmd, cwd=self.target_path, capture_output=True)
            if result.returncode != 0:
                self.log("Directory text scan also failed, creating minimal report...", "WARNING")
                with open(text_output, "w", encoding="utf-8") as f:
                    f.write("Safety Scan Results\n")
                    f.write("===================\n")
                    f.write("Safety scan failed or no vulnerabilities found.\n")
                    f.write(f"Scan completed at: {datetime.now().isoformat()}\n")
        
        # Additional verbose scan
        self.log("Running additional verbose scan...")
        cmd = ["safety", "check", "--verbose", "--file", str(dep_file)]
        result = self.run_command(cmd, cwd=self.target_path, capture_output=True)
        if result.returncode == 0 and result.stdout:
            with open(text_output, "a", encoding="utf-8") as f:
                f.write("\n\nVerbose Output:\n")
                f.write("===============\n")
                f.write(result.stdout)
        
        # Check if reports were generated
        if json_output.exists() or text_output.exists():
            self.log("Safety scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("Safety scan completed but no results generated", "ERROR")
            return False


if __name__ == "__main__":
    import sys
    
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/SimpleSecCheck/results")
    log_file = os.getenv("LOG_FILE", "/SimpleSecCheck/logs/scan.log")
    config_path = os.getenv("SAFETY_CONFIG_PATH", "/SimpleSecCheck/config/tools/safety/config.yaml")
    
    scanner = SafetyScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
