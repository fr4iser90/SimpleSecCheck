"""
Brakeman Scanner
Python implementation of run_brakeman.sh
"""
import os
from pathlib import Path
from typing import List, Optional
from scanner.core.base_scanner import BaseScanner


class BrakemanScanner(BaseScanner):
    """Brakeman scanner implementation"""
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None
    ):
        """
        Initialize Brakeman scanner
        
        Args:
            target_path: Path to scan
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to Brakeman config file (optional)
        """
        super().__init__("Brakeman", target_path, results_dir, log_file, config_path)
    
    def find_ruby_files(self) -> List[Path]:
        """Find Ruby/Rails files"""
        ruby_files = []
        patterns = ["*.rb", "Gemfile", "config/application.rb"]
        
        for pattern in patterns:
            for file in self.target_path.rglob(pattern):
                ruby_files.append(file)
        
        return ruby_files
    
    def scan(self) -> bool:
        """Run Brakeman scan"""
        if not self.check_tool_installed("brakeman"):
            self.log("brakeman not found in PATH", "ERROR")
            return False
        
        ruby_files = self.find_ruby_files()
        
        if not ruby_files:
            self.log("No Ruby/Rails files found, skipping scan.", "WARNING")
            return True
        
        self.log(f"Found {len(ruby_files)} Ruby/Rails file(s).")
        self.log(f"Running Ruby on Rails security scan on {self.target_path}...")
        
        json_output = self.results_dir / "brakeman.json"
        text_output = self.results_dir / "brakeman.txt"
        
        # JSON report
        self.log("Generating JSON report...")
        cmd = ["brakeman", "-q", "-f", "json", "-o", str(json_output), "--force", str(self.target_path)]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode != 0:
            self.log("JSON report generation failed", "WARNING")
        
        # Text report
        self.log("Generating text report...")
        cmd = ["brakeman", "-q", "-o", str(text_output), "--force", str(self.target_path)]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode != 0:
            self.log("Text report generation failed", "WARNING")
        
        if json_output.exists() or text_output.exists():
            self.log("Brakeman scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("No Brakeman report was generated!", "ERROR")
            return False


if __name__ == "__main__":
    import sys
    
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/SimpleSecCheck/results")
    log_file = os.getenv("LOG_FILE", "/SimpleSecCheck/logs/scan.log")
    config_path = os.getenv("BRAKEMAN_CONFIG_PATH", "/SimpleSecCheck/config/tools/brakeman/config.yaml")
    
    scanner = BrakemanScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
