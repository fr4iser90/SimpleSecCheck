"""
Terraform Security Scanner
Python implementation of run_terraform_security.sh
"""
import os
from pathlib import Path
from typing import List, Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability


class TerraformSecurityScanner(BaseScanner):
    """Terraform Security scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.CONFIG,
            supported_targets=[TargetType.LOCAL_MOUNT, TargetType.GIT_REPO, TargetType.UPLOADED_CODE],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 11
    REQUIRES_CONDITION = None
    ENV_VARS = {
        "TERRAFORM_SECURITY_CONFIG_PATH": "/app/scanner/plugins/terraform/config/config.yaml"
    }
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None
    ):
        """
        Initialize Terraform Security scanner
        
        Args:
            target_path: Path to scan
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to Terraform Security config file (optional)
        """
        super().__init__("Terraform Security", target_path, results_dir, log_file, config_path)
    
    def find_terraform_files(self) -> List[Path]:
        """Find Terraform files"""
        terraform_files = []
        patterns = ["*.tf", "*.tfvars"]
        
        for pattern in patterns:
            for file in self.target_path.rglob(pattern):
                terraform_files.append(file)
        
        return terraform_files
    
    def scan(self) -> bool:
        """Run Terraform Security scan"""
        if not self.check_tool_installed("checkov"):
            self.log("Checkov CLI not found, skipping scan.", "WARNING")
            return True
        
        terraform_files = self.find_terraform_files()
        
        if not terraform_files:
            self.log("No Terraform files found, skipping scan.", "WARNING")
            return True
        
        self.log(f"Found {len(terraform_files)} Terraform file(s).")
        self.log(f"Running Terraform security scan on {self.target_path}...")
        
        json_output = self.results_dir / "report.json"  # Changed from checkov.json
        text_output = self.results_dir / "report.txt"   # Changed from checkov.txt
        
        # JSON report
        self.log("Generating JSON report...")
        cmd = ["checkov", "-d", str(self.target_path), "--framework", "terraform",
               "--output", "json", "--output-file", str(json_output)]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode != 0:
            self.log("JSON report generation failed", "WARNING")
        
        # Text report
        self.log("Generating text report...")
        cmd = ["checkov", "-d", str(self.target_path), "--framework", "terraform",
               "--output", "cli", "--output-file", str(text_output)]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode != 0:
            self.log("Text report generation failed", "WARNING")
        
        if json_output.exists() or text_output.exists():
            self.log("Terraform Security scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("No results generated", "WARNING")
            return True


if __name__ == "__main__":
    import sys
    
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/app/results")
    log_file = os.getenv("LOG_FILE", "app/results/logs/scan.log")
    config_path = os.getenv("TERRAFORM_SECURITY_CONFIG_PATH", "/app/scanner/plugins/terraform/config/config.yaml")
    
    scanner = TerraformSecurityScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
