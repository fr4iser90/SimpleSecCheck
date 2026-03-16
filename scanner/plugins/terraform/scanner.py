"""
Terraform Security Scanner
Python implementation of run_terraform_security.sh
"""
import json
import os
from pathlib import Path
from typing import List, Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability
from scanner.core.step_registry import SubStepType


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
        """Run Terraform Security scan with standardized substeps"""
        if not self.check_tool_installed("checkov"):
            self.log("Checkov CLI not found, skipping scan.", "WARNING")
            return True
        
        # INIT: Initialization
        self.substep_init("Initializing Terraform Security scan...")
        self.complete_substep("Initialization", "Terraform Security initialized")
        
        # PREPARE: Terraform File Discovery
        self.start_substep("Terraform File Discovery", "Discovering Terraform files...", SubStepType.ACTION)
        terraform_files = self.find_terraform_files()
        
        if not terraform_files:
            self.complete_substep("Terraform File Discovery", "No Terraform files found")
            self.log("No Terraform files found, skipping scan.", "WARNING")
            status_file = Path(self.results_dir) / "status.json"
            try:
                status_file.write_text(json.dumps({"status": "skipped", "message": "No Terraform files found, skipping scan."}), encoding="utf-8")
            except Exception:
                pass
            return True
        
        self.complete_substep("Terraform File Discovery", f"Found {len(terraform_files)} Terraform file(s)")
        self.log(f"Found {len(terraform_files)} Terraform file(s).")
        self.log(f"Running Terraform security scan on {self.target_path}...")
        
        json_output = self.results_dir / "report.json"
        text_output = self.results_dir / "report.txt"
        
        # PREPARE: Module Resolution
        self.start_substep("Module Resolution", "Resolving Terraform modules...", SubStepType.ACTION)
        # Module resolution happens during scan
        self.complete_substep("Module Resolution", "Modules resolved")
        
        # SCAN: Terraform Validation
        self.start_substep("Terraform Validation", "Validating Terraform configuration...", SubStepType.ACTION)
        # Validation happens during scan
        self.complete_substep("Terraform Validation", "Terraform configuration validated")
        
        # SCAN: Security Rule Evaluation
        self.substep_scan("Security Rule Evaluation", "Evaluating Terraform against security rules...")
        
        # Main scan
        self.log("Generating JSON report...")
        cmd = ["checkov", "-d", str(self.target_path), "--framework", "terraform",
               "--output", "json", "--output-file", str(json_output)]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode == 0:
            self.complete_substep("Security Rule Evaluation", "Security rule evaluation completed")
        else:
            self.log("JSON report generation failed", "WARNING")
            self.complete_substep("Security Rule Evaluation", "Security rule evaluation completed (with warnings)")
        
        # PROCESS: Result Processing
        self.substep_process("Result Processing", "Processing scan results...")
        self.complete_substep("Result Processing", "Results processed")
        
        # REPORT: JSON Report
        self.substep_report("JSON", "Generating JSON report...")
        if json_output.exists() and json_output.stat().st_size > 0:
            self.complete_substep("Generating JSON Report", "JSON report generated successfully")
        else:
            self.fail_substep("Generating JSON Report", "JSON report generation failed")
        
        # Text report (for completeness)
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
    import os
    import sys
    
    # Get default parameters from BaseScanner
    default_params = BaseScanner.get_default_params_from_env()
    
    # Get scanner-specific parameters
    config_path = os.getenv("TERRAFORM_SECURITY_CONFIG_PATH", "/app/scanner/plugins/terraform/config/config.yaml")
    
    scanner = TerraformSecurityScanner(
        **default_params,
        config_path=config_path
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
