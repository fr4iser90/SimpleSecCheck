"""
Docker Bench Scanner
Python implementation of run_docker_bench.sh
"""
import os
import json
import re
from pathlib import Path
from typing import Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability


class DockerBenchScanner(BaseScanner):
    """Docker Bench scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.NETWORK,
            supported_targets=[TargetType.NETWORK_HOST],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 3
    REQUIRES_CONDITION = None
    ENV_VARS = {}
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None
    ):
        """
        Initialize Docker Bench scanner
        
        Args:
            target_path: Path to scan (not used for network scans)
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to Docker Bench config file (optional)
        """
        super().__init__("Docker Bench", target_path, results_dir, log_file, config_path)
        self.docker_bench_dir = Path("/opt/docker-bench-security")
    
    def check_docker_socket(self) -> bool:
        """Check if Docker socket is accessible"""
        docker_socket = Path("/var/run/docker.sock")
        if not docker_socket.exists() or not docker_socket.is_socket():
            self.log("Docker socket /var/run/docker.sock not accessible", "ERROR")
            return False
        return True
    
    def convert_text_to_json(self, text_file: Path) -> dict:
        """Convert Docker Bench text output to JSON"""
        findings = []
        
        try:
            with open(text_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Parse PASS, WARN, INFO, NOTE lines (with ANSI codes)
                pass_match = re.search(r'\[PASS\][\x1b\[\d+m\[0m]*\s*(.+?)(?:\x1b\[|$)', line)
                if pass_match:
                    findings.append({
                        "test": pass_match.group(1).strip(),
                        "result": "PASS",
                        "group": "Docker Bench Security"
                    })
                    continue
                
                warn_match = re.search(r'\[WARN\][\x1b\[\d+m\[0m]*\s*(.+?)(?:\x1b\[|$)', line)
                if warn_match:
                    findings.append({
                        "test": warn_match.group(1).strip(),
                        "result": "WARN",
                        "group": "Docker Bench Security"
                    })
                    continue
                
                info_match = re.search(r'\[INFO\][\x1b\[\d+m\[0m]*\s*(.+?)(?:\x1b\[|$)', line)
                if info_match:
                    findings.append({
                        "test": info_match.group(1).strip(),
                        "result": "INFO",
                        "group": "Docker Bench Security"
                    })
                    continue
                
                note_match = re.search(r'\[NOTE\][\x1b\[\d+m\[0m]*\s*(.+?)(?:\x1b\[|$)', line)
                if note_match:
                    findings.append({
                        "test": note_match.group(1).strip(),
                        "result": "NOTE",
                        "group": "Docker Bench Security"
                    })
                    continue
        except Exception as e:
            self.log(f"Error converting text to JSON: {e}", "WARNING")
        
        return {
            "benchmark": "Docker Bench Security",
            "tests": [{
                "group": "Docker Compliance",
                "summary": {},
                "checks": findings
            }]
        }
    
    def scan(self) -> bool:
        """Run Docker Bench scan"""
        if not self.check_tool_installed("docker-bench-security"):
            self.log("docker-bench-security not found in PATH", "ERROR")
            return False
        
        if not self.check_docker_socket():
            return False
        
        if not self.docker_bench_dir.exists():
            self.log(f"Docker Bench directory not found at {self.docker_bench_dir}", "ERROR")
            return False
        
        self.log("Running Docker daemon compliance scan...")
        
        json_output = self.results_dir / "report.json"  # Changed from docker-bench.json
        text_output = self.results_dir / "report.txt"   # Changed from docker-bench.txt
        
        bench_script = self.docker_bench_dir / "docker-bench-security.sh"
        if not bench_script.exists():
            self.log(f"Docker Bench script not found at {bench_script}", "ERROR")
            return False
        
        # Text report
        self.log("Running compliance scan...")
        cmd = [str(bench_script)]
        
        result = self.run_command(cmd, cwd=self.docker_bench_dir, capture_output=True)
        if result.returncode == 0 and result.stdout:
            with open(text_output, "w", encoding="utf-8") as f:
                f.write(result.stdout)
        else:
            self.log("Text report generation failed", "WARNING")
        
        # Convert text to JSON
        if text_output.exists():
            json_data = self.convert_text_to_json(text_output)
            with open(json_output, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2)
        
        if json_output.exists() or text_output.exists():
            self.log("Docker Bench scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("No Docker Bench report was generated!", "ERROR")
            return False


if __name__ == "__main__":
    import sys
    
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/app/results")
    log_file = os.getenv("LOG_FILE", "app/results/logs/scan.log")
    config_path = os.getenv("DOCKER_BENCH_CONFIG_PATH", "/app/scanner/plugins/docker_bench/config/config.yaml")
    
    scanner = DockerBenchScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
