"""
Checkov Scanner
Python implementation of run_checkov.sh
"""
import json
import os
from pathlib import Path
from typing import Any, List, Optional

from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability
from scanner.core.step_registry import SubStepType


def _collect_failed_checks(data: Any) -> List[dict]:
    """Normalize Checkov JSON (dict or list of per-framework blocks) into failed_checks."""
    out: List[dict] = []
    if isinstance(data, dict):
        res = data.get("results")
        if isinstance(res, dict):
            fc = res.get("failed_checks")
            if isinstance(fc, list):
                out.extend(fc)
        fc = data.get("failed_checks")
        if isinstance(fc, list) and not out:
            out.extend(fc)
    elif isinstance(data, list):
        for block in data:
            if not isinstance(block, dict):
                continue
            res = block.get("results")
            if isinstance(res, dict):
                fc = res.get("failed_checks")
                if isinstance(fc, list):
                    out.extend(fc)
    return out


def _merge_checkov_json_outputs(parts: List[Any]) -> dict:
    """Merge multiple Checkov JSON runs (batched -f scans) into one report dict."""
    failed: List[dict] = []
    for data in parts:
        failed.extend(_collect_failed_checks(data))
    seen_keys: set = set()
    unique_failed: List[dict] = []
    for c in failed:
        key = (
            c.get("check_id") or c.get("rule_id") or "",
            c.get("file_path") or c.get("file_abs_path") or "",
            str(c.get("file_line_range") or []),
        )
        if key not in seen_keys:
            seen_keys.add(key)
            unique_failed.append(c)
    return {
        "check_type": "merged_file_scan",
        "results": {"failed_checks": unique_failed},
        "summary": {"failed": len(unique_failed)},
    }


def checkov_json_to_text(data: Any) -> str:
    """Build human-readable report from Checkov JSON (single run — no second CLI scan)."""
    lines: List[str] = [
        "Checkov Infrastructure Security Scan",
        "=" * 60,
    ]
    failed = _collect_failed_checks(data)
    if isinstance(data, dict) and data.get("summary"):
        lines.append(f"Summary: {data['summary']}")
        lines.append("")

    if not failed:
        lines.append("No failed checks reported (compliant or no issues in scope).")
        lines.append("")
        return "\n".join(lines)

    lines.append(f"Failed checks: {len(failed)}")
    lines.append("")

    for i, c in enumerate(failed, 1):
        rid = c.get("check_id") or c.get("rule_id") or ""
        name = c.get("check_name") or c.get("name") or ""
        fp = c.get("file_path") or c.get("file_abs_path") or ""
        lr = c.get("file_line_range") or []
        line = lr[0] if isinstance(lr, list) and lr else ""
        res = c.get("resource") or ""
        guide = c.get("guideline") or ""
        if isinstance(guide, list):
            guide = " ".join(str(x) for x in guide)
        guide = str(guide).strip()
        if len(guide) > 500:
            guide = guide[:497] + "..."

        lines.append(f"[{i}] {rid} — {name}")
        lines.append(f"    File: {fp}  Line: {line}")
        if res:
            lines.append(f"    Resource: {res}")
        if guide:
            lines.append(f"    {guide}")
        lines.append("")

    return "\n".join(lines)


class CheckovScanner(BaseScanner):
    """Checkov scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.CONFIG,
            supported_targets=[TargetType.LOCAL_MOUNT, TargetType.GIT_REPO, TargetType.UPLOADED_CODE],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 12
    REQUIRES_CONDITION = None
    ENV_VARS = {
        "CHECKOV_CONFIG_PATH": "/app/scanner/plugins/checkov/config/config.yaml"
    }
    # Max files per checkov invocation (avoids ARG_MAX; keeps RAM lower than -d on whole tree)
    CHECKOV_FILES_PER_BATCH = 80
    
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
        Initialize Checkov scanner.
        step_name: From registry/manifest (single source).
        """
        super().__init__("Checkov", target_path, results_dir, log_file, config_path, step_name=step_name)
        self.exclude_paths = exclude_paths or os.getenv("SIMPLESECCHECK_EXCLUDE_PATHS", "")
    
    def find_infra_files(self) -> List[Path]:
        """Find infrastructure files only (no generic *.yml/*.json to avoid Semgrep rules, package.json, etc.)."""
        infra_files = []
        patterns = [
            # Terraform
            "*.tf",
            "*.tfvars",
            "*.tfstate",
            "*.tfstate.json",
            # Docker
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.yaml",
            "docker-compose*.yml",
            # CloudFormation / Serverless
            "cloudformation.yaml",
            "cloudformation.yml",
            "cloudformation.json",
            "serverless.yml",
            "serverless.yaml",
            "*.template.json",
            # Kubernetes / Helm (common naming; avoids all random .yml)
            "*deployment*.yaml",
            "*deployment*.yml",
            "*service*.yaml",
            "*service*.yml",
            "*ingress*.yaml",
            "*ingress*.yml",
            "values.yaml",
        ]
        
        for pattern in patterns:
            for file in self.target_path.rglob(pattern):
                if "node_modules" in file.parts or ".git" in file.parts:
                    continue
                skip = False
                if self.exclude_paths:
                    for exclude in self.exclude_paths.split(","):
                        exclude = exclude.strip()
                        if exclude and exclude in str(file):
                            skip = True
                            break

                if not skip:
                    infra_files.append(file)

        by_key: dict = {}
        for f in infra_files:
            try:
                k = f.resolve()
            except OSError:
                k = f
            by_key[k] = f
        return list(by_key.values())
    
    def get_skip_args(self) -> List[str]:
        """Get Checkov skip arguments"""
        skip_args = []
        
        if self.exclude_paths:
            for path in self.exclude_paths.split(","):
                path = path.strip()
                if path:
                    skip_args.extend(["--skip-path", path])
        
        return skip_args

    def _skip_framework_args(self) -> List[str]:
        """Optional --skip-framework list from env (comma-separated). Empty/unset = no skips.
        Reserved for future admin config, e.g. CHECKOV_SKIP_FRAMEWORKS=secrets,cdk,arm
        """
        raw = (os.getenv("CHECKOV_SKIP_FRAMEWORKS") or "").strip()
        if not raw or raw.lower() == "none":
            return []
        out: List[str] = []
        for fw in raw.split(","):
            fw = fw.strip()
            if fw:
                out.extend(["--skip-framework", fw])
        return out

    def scan(self) -> bool:
        """Run Checkov scan with standardized substeps"""
        if not self.check_tool_installed("checkov"):
            self.log("Checkov CLI not found, skipping scan.", "WARNING")
            return True
        
        # INIT: Initialization
        self.substep_init("Initializing Checkov scan...")
        self.complete_substep("Initialization", "Checkov initialized")
        
        # PREPARE: Finding Infrastructure Files
        self.start_substep("Finding Infrastructure Files", "Scanning for infrastructure files...", SubStepType.ACTION)
        infra_files = self.find_infra_files()
        
        if not infra_files:
            self.complete_substep("Finding Infrastructure Files", "No infrastructure files found")
            self.log("No infrastructure files found, skipping scan.", "WARNING")
            return True
        
        self.complete_substep("Finding Infrastructure Files", f"Found {len(infra_files)} infrastructure file(s)")
        self.log(f"Found {len(infra_files)} infrastructure file(s).")
        self.log(f"Running infrastructure security scan on {self.target_path}...")
        
        # PREPARE: Parsing Infrastructure Files
        self.start_substep("Parsing Infrastructure Files", "Parsing infrastructure configuration files...", SubStepType.ACTION)
        # Parsing happens during scan
        self.complete_substep("Parsing Infrastructure Files", f"Parsed {len(infra_files)} file(s)")
        
        json_output = self.results_dir / "report.json"  # Changed from checkov-comprehensive.json
        text_output = self.results_dir / "report.txt"   # Changed from checkov-comprehensive.txt
        
        # Remove old directory if it exists
        if json_output.exists() and json_output.is_dir():
            import shutil
            shutil.rmtree(json_output, ignore_errors=True)
            self.log("Removed old directory at json_output path")
        
        skip_args = self.get_skip_args()
        fw_skip = self._skip_framework_args()

        # SCAN: Running Security Policies
        self.substep_scan("Running Security Policies", "Evaluating infrastructure against security policies...")

        # SCAN: Evaluating Misconfigurations
        self.start_substep("Evaluating Misconfigurations", "Checking for security misconfigurations...", SubStepType.PHASE)

        env = os.environ.copy()
        env["PYTHONHASHSEED"] = "0"
        env["OMP_NUM_THREADS"] = "1"
        env["MKL_NUM_THREADS"] = "1"

        batch_size = max(1, int(os.getenv("CHECKOV_FILES_PER_BATCH", str(self.CHECKOV_FILES_PER_BATCH))))
        batches: List[List[Path]] = [
            infra_files[i : i + batch_size] for i in range(0, len(infra_files), batch_size)
        ]
        self.log(
            f"Checkov: scanning {len(infra_files)} file(s) in {len(batches)} batch(es) (-f, not full tree -d)."
        )

        parsed_chunks: List[Any] = []
        combined_stderr: List[str] = []
        last_returncode = 0

        for idx, batch in enumerate(batches, start=1):
            file_args: List[str] = []
            for p in batch:
                file_args.extend(["-f", str(p)])
            cmd = [
                "checkov",
                *file_args,
                *skip_args,
                *fw_skip,
                "--output",
                "json",
                "--quiet",
            ]
            result = self.run_command(cmd, capture_output=True, env=env)
            last_returncode = result.returncode
            if result.stderr:
                combined_stderr.append(result.stderr)
            if result.stdout and result.stdout.strip():
                try:
                    chunk = json.loads(result.stdout)
                    if isinstance(chunk, (dict, list)):
                        parsed_chunks.append(chunk)
                except (ValueError, TypeError) as e:
                    self.log(f"Checkov batch {idx}/{len(batches)}: JSON parse error: {e}", "WARNING")

        wrote_json = False
        parsed_data: Any = None
        if parsed_chunks:
            if len(parsed_chunks) == 1 and isinstance(parsed_chunks[0], dict):
                parsed_data = parsed_chunks[0]
            else:
                parsed_data = _merge_checkov_json_outputs(parsed_chunks)
            with open(json_output, "w", encoding="utf-8") as f:
                json.dump(parsed_data, f, indent=2)
            wrote_json = True

        result_stderr = "\n".join(combined_stderr) if combined_stderr else ""

        if wrote_json:
            self.complete_substep("Running Security Policies", "Security policies evaluated")
            self.complete_substep("Evaluating Misconfigurations", "Misconfiguration evaluation completed")
        else:
            if last_returncode != 0:
                self.log(
                    "Checkov: no parseable JSON from batches (exit may be non-zero if findings present)",
                    "WARNING",
                )
            self.complete_substep("Running Security Policies", "Security policies evaluated (with warnings)")
            self.complete_substep("Evaluating Misconfigurations", "Misconfiguration evaluation completed (with warnings)")
        
        # PROCESS: Result Processing
        self.substep_process("Result Processing", "Processing scan results...")
        self.complete_substep("Result Processing", "Results processed")
        
        # REPORT: JSON Report
        self.substep_report("JSON", "Generating JSON report...")
        if json_output.exists() and json_output.stat().st_size > 0:
            self.complete_substep("Generating JSON Report", "JSON report generated successfully")
        else:
            self.fail_substep("Generating JSON Report", "JSON report generation failed")
        
        # REPORT: Text Report (from JSON only — avoids second full Checkov scan)
        self.start_substep("Generating Text Report", "Generating text report from JSON...", SubStepType.OUTPUT)
        self.log("Generating text report from Checkov JSON (single scan).")
        if wrote_json and parsed_data is not None:
            text_body = checkov_json_to_text(parsed_data)
            with open(text_output, "w", encoding="utf-8") as f:
                f.write(text_body)
            self.complete_substep("Generating Text Report", "Text report generated successfully")
        else:
            stub = (
                "Checkov text report: no parseable JSON from scan.\n\n"
                + (result_stderr or "")[:8000]
            )
            with open(text_output, "w", encoding="utf-8") as f:
                f.write(stub)
            self.log("Text report is stub (JSON missing or unparseable)", "WARNING")
            self.complete_substep("Generating Text Report", "Text stub written (no JSON)")
        
        if json_output.exists() or text_output.exists():
            self.log("Infrastructure security scan completed successfully", "SUCCESS")
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
    config_path = os.getenv("CHECKOV_CONFIG_PATH", "/app/scanner/plugins/checkov/config/config.yaml")
    exclude_paths = os.getenv("SIMPLESECCHECK_EXCLUDE_PATHS", "")
    
    scanner = CheckovScanner(
        **default_params,
        config_path=config_path,
        exclude_paths=exclude_paths
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
