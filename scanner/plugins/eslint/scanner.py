"""
ESLint Scanner
Python implementation of run_eslint.sh
"""
import os
import shlex
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

        # Install plugins in results_dir so we don't pollute the target repo.
        # Minimal package.json keeps npm layout stable (scoped packages under node_modules).
        pkg_json = self.results_dir / "package.json"
        if not pkg_json.is_file():
            try:
                pkg_json.write_text('{"name":"ssc-eslint-plugins","private":true}\n', encoding="utf-8")
            except OSError as e:
                self.log(f"Cannot write {pkg_json}: {e}", "WARNING")

        # Pin versions for reproducible installs; resolve via NODE_PATH + package name in .cjs
        # (avoids brittle absolute paths if npm lays out deps differently).
        install_result = self.run_command(
            [
                "npm",
                "install",
                "--no-fund",
                "--no-audit",
                "eslint-plugin-security@^3.0.0",
                "@typescript-eslint/parser@8.57.1",
                "@typescript-eslint/eslint-plugin@8.57.1",
            ],
            capture_output=True,
            cwd=self.results_dir,
        )
        if install_result.returncode != 0:
            self.log("npm install for eslint plugins failed (will try anyway): " + (install_result.stderr or install_result.stdout or "")[:200], "WARNING")

        plugins_nm = str((self.results_dir / "node_modules").resolve())
        parser_pkg = self.results_dir / "node_modules" / "@typescript-eslint" / "parser"
        if not (parser_pkg / "package.json").is_file():
            self.log(
                f"ESLint plugin layout incomplete (missing {parser_pkg}); npm install may have failed.",
                "ERROR",
            )
            tail = (install_result.stderr or install_result.stdout or "").strip()
            if tail:
                self.log(f"npm output (truncated): {tail[:800]}", "WARNING")

        # ESLint 9 flat config: "files" are relative to the config file's directory. So we write
        # the config inside the target and run with cwd=target; then **/*.js matches target files.
        temp_config = self.target_path / ".eslint.scan.cjs"
        config_content = """const security = require('eslint-plugin-security');
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
"""
        try:
            temp_config.write_text(config_content, encoding="utf-8")
        except OSError as e:
            self.log(f"Cannot write ESLint config to target: {e}", "ERROR")
            return False

        ignore_args = self.get_ignore_args()
        extra = shlex.split(os.getenv("ESLINT_EXTRA_ARGS", "").strip())

        # Run ESLint with cwd=target so config base path = target and "." lints the repo
        run_cwd = str(self.target_path)
        config_arg = ".eslint.scan.cjs"

        run_env = os.environ.copy()
        prev_np = run_env.get("NODE_PATH", "").strip()
        run_env["NODE_PATH"] = (
            plugins_nm + os.pathsep + prev_np if prev_np else plugins_nm
        )

        # JSON report (output paths must be absolute when cwd=target)
        self.log("Running ESLint scan with JSON output...")
        cmd = [
            *tool_cmd,
            "-c",
            config_arg,
            *ignore_args,
            *extra,
            "--format=json",
            f"--output-file={json_output.resolve()}",
            ".",
        ]
        result = self.run_command(cmd, capture_output=True, cwd=Path(run_cwd), env=run_env)
        json_failed = result.returncode != 0
        if json_failed:
            self.log("JSON report generation failed (exit code {}); no report written.".format(result.returncode), "WARNING")

        # Text report
        self.log("Running ESLint scan with text output...")
        cmd = [
            *tool_cmd,
            "-c",
            config_arg,
            *ignore_args,
            *extra,
            "--format=compact",
            f"--output-file={text_output.resolve()}",
            ".",
        ]
        result = self.run_command(
            cmd,
            capture_output=True,
            cwd=Path(run_cwd),
            env=run_env,
            log_failure_output_tail=not json_failed,
        )
        if result.returncode != 0:
            self.log("Text report generation failed", "WARNING")

        try:
            if temp_config.exists():
                temp_config.unlink()
        except OSError:
            pass

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
