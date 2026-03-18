"""
ESLint Scanner
Python implementation of run_eslint.sh
"""
import os
from pathlib import Path
from typing import List, Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability


class ESLintScanner(BaseScanner):
    """ESLint scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.CODE,
            supported_targets=[TargetType.LOCAL_MOUNT, TargetType.GIT_REPO, TargetType.UPLOADED_CODE],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 22
    REQUIRES_CONDITION = None
    ENV_VARS = {
        "ESLINT_CONFIG_PATH": "/app/scanner/plugins/eslint/config/config.yaml"
    }
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None,
        exclude_paths: Optional[str] = None,
        step_name: Optional[str] = None,
    ):
        """
        Initialize ESLint scanner.
        step_name: From registry/manifest (single source).
        """
        super().__init__("ESLint", target_path, results_dir, log_file, config_path, step_name=step_name)
        self.exclude_paths = exclude_paths or os.getenv("SIMPLESECCHECK_EXCLUDE_PATHS", "")
    
    def find_js_files(self) -> List[Path]:
        """Find JavaScript/TypeScript files"""
        js_files = []
        extensions = ["*.js", "*.jsx", "*.ts", "*.tsx"]
        
        for ext in extensions:
            for file in self.target_path.rglob(ext):
                # Skip node_modules and exclude paths
                if "node_modules" in str(file):
                    continue
                
                skip = False
                if self.exclude_paths:
                    for exclude in self.exclude_paths.split(","):
                        exclude = exclude.strip()
                        if exclude and exclude in str(file):
                            skip = True
                            break
                
                if not skip:
                    js_files.append(file)
        
        return js_files
    
    def get_ignore_args(self) -> List[str]:
        """Get ESLint ignore arguments"""
        ignore_args = []
        
        if self.exclude_paths:
            for path in self.exclude_paths.split(","):
                path = path.strip()
                if path:
                    ignore_args.extend(["--ignore-pattern", f"**/{path}/**"])
        
        return ignore_args
    
    def scan(self) -> bool:
        """Run ESLint scan"""
        # Get tool command (handles npm global packages, npx, PATH)
        tool_cmd = self.get_tool_command("eslint")
        if not tool_cmd:
            self.log("eslint not found", "ERROR")
            return False
        
        js_files = self.find_js_files()
        
        if not js_files:
            self.log("No JavaScript/TypeScript files found, skipping scan (no report written).", "WARNING")
            return True
        
        self.log(f"Found {len(js_files)} JavaScript/TypeScript file(s).")
        self.log(f"Running JavaScript/TypeScript security scan on {self.target_path}...")
        
        json_output = self.results_dir / "report.json"  # Changed from eslint.json
        text_output = self.results_dir / "report.txt"   # Changed from eslint.txt
        temp_config = self.results_dir / "eslint.config.cjs"

        # Ensure plugins are available where the config runs (config is in results_dir, so resolve from there)
        install_result = self.run_command(
            ["npm", "install", "eslint-plugin-security", "@typescript-eslint/parser", "@typescript-eslint/eslint-plugin"],
            capture_output=True,
            cwd=self.results_dir,
        )
        if install_result.returncode != 0:
            self.log("npm install for eslint plugins failed (will try anyway): " + (install_result.stderr or install_result.stdout or "")[:200], "WARNING")

        temp_config.write_text(
            """const security = require('eslint-plugin-security');
const tsParser = require('@typescript-eslint/parser');

module.exports = [
  {
    files: ['**/*.{js,jsx,ts,tsx}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      parser: tsParser,
    },
    plugins: {
      security,
    },
    rules: {
      ...security.configs.recommended.rules,
    },
  },
];
""",
            encoding="utf-8",
        )
        
        ignore_args = self.get_ignore_args()
        
        # JSON report
        self.log("Running ESLint scan with JSON output...")
        cmd = [
            *tool_cmd,
            "-c",
            str(temp_config),
            *ignore_args,
            "--format=json",
            f"--output-file={json_output}",
            str(self.target_path),
        ]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode != 0:
            self.log("JSON report generation failed (exit code {}); no report written.".format(result.returncode), "WARNING")
        
        # Text report
        self.log("Running ESLint scan with text output...")
        cmd = [
            *tool_cmd,
            "-c",
            str(temp_config),
            *ignore_args,
            "--format=compact",
            f"--output-file={text_output}",
            str(self.target_path),
        ]
        
        result = self.run_command(cmd, capture_output=True)
        if result.returncode != 0:
            self.log("Text report generation failed", "WARNING")
        
        if temp_config.exists():
            temp_config.unlink()

        if json_output.exists():
            self.log("ESLint scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("No ESLint report was generated!", "ERROR")
            return False


if __name__ == "__main__":
    import sys
    
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/app/results")
    log_file = os.getenv("LOG_FILE", "app/results/logs/scan.log")
    config_path = os.getenv("ESLINT_CONFIG_PATH", "/app/scanner/plugins/eslint/config/config.yaml")
    exclude_paths = os.getenv("SIMPLESECCHECK_EXCLUDE_PATHS", "")
    
    scanner = ESLintScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path,
        exclude_paths=exclude_paths
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
