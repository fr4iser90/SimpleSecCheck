"""
CodeQL Scanner
Python implementation of run_codeql.sh
"""
import os
import json
import shlex
import shutil
from pathlib import Path
from typing import List, Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability
from scanner.core.step_registry import SubStepType


class CodeQLScanner(BaseScanner):
    """CodeQL scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.CODE,
            supported_targets=[TargetType.LOCAL_MOUNT, TargetType.GIT_REPO, TargetType.UPLOADED_CODE],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 3
    REQUIRES_CONDITION = None
    ENV_VARS = {
        "CODEQL_CONFIG_PATH": "/app/scanner/plugins/codeql/config/config.yaml",
        "CODEQL_QUERIES_PATH": "/app/scanner/plugins/codeql/config/queries"
    }
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None,
        queries_path: Optional[str] = None,
        step_name: Optional[str] = None,
    ):
        """
        Initialize CodeQL scanner

        Args:
            target_path: Path to scan
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to CodeQL config file
            queries_path: Path to CodeQL queries directory
            step_name: Step name from registry/manifest (single source)
        """
        super().__init__("CodeQL", target_path, results_dir, log_file, config_path, step_name=step_name)
        self.queries_path = Path(queries_path) if queries_path else Path("/app/scanner/plugins/codeql/config/queries")
    
    def detect_languages(self) -> List[str]:
        """Detect programming languages in target"""
        if not self.check_tool_installed("codeql"):
            return []
        
        # Try CodeQL language detection
        tool_cmd = self.get_tool_command("codeql")
        if not tool_cmd:
            return []
        cmd = [*tool_cmd, "resolve", "languages", "--format=json"]
        result = self.run_command(cmd, capture_output=True)
        
        if result.returncode == 0 and result.stdout:
            try:
                languages = json.loads(result.stdout)
                if languages:
                    file_languages = self._detect_languages_by_files()
                    return file_languages or languages
            except Exception:
                pass
        
        # Fallback: detect by file extensions
        self.log("Auto-detection failed, trying common languages...", "WARNING")
        return self._detect_languages_by_files()

    def _detect_languages_by_files(self) -> List[str]:
        languages: List[str] = []

        if any(self.target_path.rglob("*.py")):
            languages.append("python")
        if any(self.target_path.rglob("*.js")) or any(self.target_path.rglob("*.ts")):
            languages.append("javascript")
        if any(self.target_path.rglob("*.java")):
            languages.append("java")
        if any(self.target_path.rglob("*.cpp")) or any(self.target_path.rglob("*.c")) or any(self.target_path.rglob("*.h")):
            languages.append("cpp")
        if any(self.target_path.rglob("*.cs")):
            languages.append("csharp")
        if any(self.target_path.rglob("*.go")):
            languages.append("go")
        if any(self.target_path.rglob("*.kt")) or any(self.target_path.rglob("*.kts")):
            languages.append("kotlin")
        if any(self.target_path.rglob("*.swift")):
            languages.append("swift")
        if any(self.target_path.rglob("*.m")) or any(self.target_path.rglob("*.mm")):
            languages.append("objectivec")

        return languages
    
    def scan(self) -> bool:
        """Run CodeQL scan with standardized substeps"""
        # Get tool command (handles symlinks, PATH)
        tool_cmd = self.get_tool_command("codeql")
        if not tool_cmd:
            self.log("codeql not found", "ERROR")
            return False
        
        self.log(f"Running code analysis on {self.target_path}...")
        
        # INIT: CodeQL Environment Setup
        self.substep_init("Setting up CodeQL environment...")
        try:
            result = self.run_command([*tool_cmd, "--version"], capture_output=True, timeout=10)
            if result.returncode == 0:
                version = result.stdout.strip().split('\n')[0] if result.stdout else "unknown"
                self.complete_substep("Initialization", f"CodeQL {version} ready")
            else:
                self.complete_substep("Initialization", "CodeQL environment ready")
        except Exception as e:
            self.complete_substep("Initialization", f"CodeQL environment setup completed: {e}")
        
        # PREPARE: Language Detection
        self.start_substep("Language Detection", "Detecting programming languages in target...", SubStepType.ACTION)
        detected_languages = self.detect_languages()
        
        if not detected_languages:
            self.complete_substep("Language Detection", "No supported languages detected")
            self.log("No supported languages detected, skipping CodeQL scan.", "WARNING")
            return True
        
        self.complete_substep("Language Detection", f"Detected languages: {', '.join(detected_languages)}")
        self.log(f"Detected languages: {', '.join(detected_languages)}")
        
        # PREPARE: Query Pack Loading
        self.start_substep("Query Pack Loading", "Loading CodeQL query packs...", SubStepType.ACTION)
        for lang in detected_languages:
            pack_name = f"codeql/{lang}-queries"
            dl = self.run_command([*tool_cmd, "pack", "download", pack_name], capture_output=True)
            if dl.returncode != 0:
                self.log(f"CodeQL pack download {pack_name} failed (exit {dl.returncode}); analyze may fail.", "WARNING")
        self.complete_substep("Query Pack Loading", "Query packs ready")
        
        db_dir = self.results_dir / "codeql-database"
        db_dir.mkdir(parents=True, exist_ok=True)
        # Temporary files per language (will be cleaned up)
        json_output = self.results_dir / "codeql.json"  # Temporary, will be removed
        sarif_output = self.results_dir / "codeql.sarif"  # Temporary, will be removed
        text_output = self.results_dir / "codeql.txt"  # Temporary, will be removed
        
        # Final combined output files (renamed to report.*)
        combined_json = self.results_dir / "report.json"  # Changed from codeql-combined.json
        combined_sarif = self.results_dir / "report.sarif"  # Changed from codeql-combined.sarif
        combined_text = self.results_dir / "report.txt"  # Changed from codeql-combined.txt
        
        # Combined files are written only when we have real results (no fake initial content)
        first_lang = None
        
        for lang in detected_languages:
            # SCAN: Code Extraction
            self.start_substep(f"Code Extraction ({lang})", f"Extracting code for {lang}...", SubStepType.ACTION)
            # Code extraction happens during database creation
            self.complete_substep(f"Code Extraction ({lang})", f"Code extraction completed for {lang}")
            
            # SCAN: Database Creation (per language) - DYNAMIC SUBSTEP
            self.start_substep(f"Database Creation ({lang})", f"Creating CodeQL database for {lang}...", SubStepType.PHASE)
            self.log(f"Creating database for language: {lang}")
            lang_db = db_dir / f"{lang}"
            
            # Special handling for C++
            if lang == "cpp":
                cpp_files = list(self.target_path.rglob("*.cpp")) + list(self.target_path.rglob("*.c"))
                cpp_files = [f for f in cpp_files if "node_modules" not in str(f)]
                if not cpp_files:
                    self.complete_substep(f"Database Creation ({lang})", "No C++ source files found, skipping")
                    self.log("No C++ source files found (only node_modules), skipping C++ database creation", "WARNING")
                    continue
                
                # Create without autobuilder
                cmd = [*tool_cmd, "database", "create", str(lang_db), "--language=cpp", 
                       f"--source-root={self.target_path}", "--command=", "--threads=4"]
            else:
                cmd = [*tool_cmd, "database", "create", str(lang_db), f"--language={lang}",
                       f"--source-root={self.target_path}", "--threads=4"]
            
            result = self.run_command(cmd, capture_output=True)
            if result.returncode != 0:
                self.fail_substep(f"Database Creation ({lang})", f"Database creation failed for {lang}")
                self.log(f"Database creation failed for {lang}", "WARNING")
                continue
            
            self.complete_substep(f"Database Creation ({lang})", f"Database created successfully for {lang}")
            
            # SCAN: Query Execution (per language) - DYNAMIC SUBSTEP
            query_suite = f"codeql/{lang}-queries"
            lang_sarif = self.results_dir / f"codeql-{lang}.sarif"
            
            self.start_substep(f"Query Execution ({lang})", f"Running security analysis for {lang}...", SubStepType.PHASE)
            self.log(f"Running security analysis for {lang} with {query_suite}...")
            analyze_extra = shlex.split(os.getenv("CODEQL_ANALYZE_EXTRA_ARGS", "").strip())
            cmd = [*tool_cmd, "database", "analyze", str(lang_db), query_suite,
                   "--format=sarif-latest", f"--output={lang_sarif}", "--threads=4", *analyze_extra]
            
            result = self.run_command(cmd, capture_output=True)
            if result.returncode != 0:
                self.log(f"Query execution failed for {lang} (exit code {result.returncode}); no SARIF written.", "WARNING")
                self.complete_substep(f"Query Execution ({lang})", "Query execution completed with warnings")
                continue
            else:
                self.complete_substep(f"Query Execution ({lang})", f"Security analysis completed for {lang}")
            
            # PROCESS: Result Processing (per language) - DYNAMIC SUBSTEP
            self.start_substep(f"Result Processing ({lang})", f"Processing results for {lang}...", SubStepType.ACTION)
            
            # Copy SARIF as JSON
            lang_json = self.results_dir / f"codeql-{lang}.json"
            if lang_sarif.exists():
                shutil.copy2(lang_sarif, lang_json)
            
            # Human-readable report (CodeQL 2.x: --format=text removed; graphtext is supported)
            lang_text = self.results_dir / f"codeql-{lang}.txt"
            if lang_sarif.exists():
                cmd = [*tool_cmd, "database", "interpret-results", str(lang_db), query_suite,
                       "--format=graphtext", f"--output={lang_text}"]
                result = self.run_command(cmd, capture_output=True)
                if result.returncode != 0:
                    self.log("Report interpretation failed for {}; no text report.".format(lang), "WARNING")
            
            self.complete_substep(f"Result Processing ({lang})", f"Results processed for {lang}")
            
            # Combine results
            if lang_json.exists() and not first_lang:
                first_lang = lang
                shutil.copy2(lang_json, combined_json)
            
            if lang_sarif.exists():
                with open(combined_sarif, "a", encoding="utf-8") as f:
                    f.write(f"\n// {lang} results\n")
                    if lang_sarif.exists():
                        f.write(lang_sarif.read_text())
            
            if lang_text.exists():
                with open(combined_text, "a", encoding="utf-8") as f:
                    f.write(f"\n=== {lang} Results ===\n")
                    f.write(lang_text.read_text())
                    f.write("\n")
            
            # Clean up individual files
            for f in [lang_json, lang_sarif, lang_text]:
                if f.exists():
                    f.unlink()
            
            # Clean up database
            if lang_db.exists():
                shutil.rmtree(lang_db, ignore_errors=True)
        
        # PROCESS: Result Aggregation
        self.substep_process("Result Aggregation", "Aggregating results from all languages...")
        
        # Final output files are already in report.* format (combined_json, combined_sarif, combined_text)
        # Clean up temporary per-language files (already done in loop)
        # Clean up temporary combined files that were used during processing
        # Note: combined_json/sarif/text are now report.json/sarif/txt, so they stay
        
        if combined_json.exists() or combined_sarif.exists() or combined_text.exists():
            self.complete_substep("Result Aggregation", "Results aggregated successfully")
        else:
            self.fail_substep("Result Aggregation", "No reports were generated")
            self.log("No CodeQL report was generated!", "ERROR")
            return False
        
        # REPORT: SARIF Generation
        self.start_substep("SARIF Generation", "Generating SARIF report...", SubStepType.OUTPUT)
        if combined_sarif.exists() and combined_sarif.stat().st_size > 0:
            self.complete_substep("SARIF Generation", "SARIF report generated successfully")
        else:
            self.fail_substep("SARIF Generation", "SARIF report generation failed")
        
        # REPORT: JSON Report (already generated as part of SARIF)
        self.substep_report("JSON", "Generating JSON report...")
        if combined_json.exists() and combined_json.stat().st_size > 0:
            self.complete_substep("Generating JSON Report", "JSON report generated successfully")
        else:
            self.fail_substep("Generating JSON Report", "JSON report generation failed")
        
        self.log("CodeQL scan completed successfully", "SUCCESS")
        return True


if __name__ == "__main__":
    import os
    import sys
    
    # Get default parameters from BaseScanner
    default_params = BaseScanner.get_default_params_from_env()
    
    # Get scanner-specific parameters
    config_path = os.getenv("CODEQL_CONFIG_PATH", "/app/scanner/plugins/codeql/config/config.yaml")
    queries_path = os.getenv("CODEQL_QUERIES_PATH", "/app/scanner/plugins/codeql/config/queries")
    
    scanner = CodeQLScanner(
        **default_params,
        config_path=config_path,
        queries_path=queries_path
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
