"""
CodeQL Scanner
Python implementation of run_codeql.sh
"""
import os
import json
import shutil
from pathlib import Path
from typing import List, Optional
from scanner.core.base_scanner import BaseScanner


class CodeQLScanner(BaseScanner):
    """CodeQL scanner implementation"""
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None,
        queries_path: Optional[str] = None
    ):
        """
        Initialize CodeQL scanner
        
        Args:
            target_path: Path to scan
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to CodeQL config file
            queries_path: Path to CodeQL queries directory
        """
        super().__init__("CodeQL", target_path, results_dir, log_file, config_path)
        self.queries_path = Path(queries_path) if queries_path else Path("/SimpleSecCheck/config/tools/codeql/queries")
    
    def detect_languages(self) -> List[str]:
        """Detect programming languages in target"""
        if not self.check_tool_installed("codeql"):
            return []
        
        # Try CodeQL language detection
        cmd = ["codeql", "resolve", "languages", "--format=json", str(self.target_path)]
        result = self.run_command(cmd, capture_output=True)
        
        if result.returncode == 0 and result.stdout:
            try:
                languages = json.loads(result.stdout)
                if languages:
                    return languages
            except Exception:
                pass
        
        # Fallback: detect by file extensions
        self.log("Auto-detection failed, trying common languages...", "WARNING")
        languages = []
        
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
        """Run CodeQL scan"""
        if not self.check_tool_installed("codeql"):
            self.log("codeql not found in PATH", "ERROR")
            return False
        
        self.log(f"Running code analysis on {self.target_path}...")
        
        detected_languages = self.detect_languages()
        
        if not detected_languages:
            self.log("No supported languages detected, skipping CodeQL scan.", "WARNING")
            return True
        
        self.log(f"Detected languages: {', '.join(detected_languages)}")
        
        db_dir = self.results_dir / "codeql-database"
        json_output = self.results_dir / "codeql.json"
        sarif_output = self.results_dir / "codeql.sarif"
        text_output = self.results_dir / "codeql.txt"
        
        combined_json = self.results_dir / "codeql-combined.json"
        combined_sarif = self.results_dir / "codeql-combined.sarif"
        combined_text = self.results_dir / "codeql-combined.txt"
        
        # Initialize combined files
        combined_json.write_text('{"$schema":"https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json","version":"2.1.0","runs":[]}')
        combined_sarif.write_text('{"$schema":"https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json","version":"2.1.0","runs":[]}')
        combined_text.write_text("CodeQL Analysis Results\n=======================\n")
        
        first_lang = None
        
        for lang in detected_languages:
            self.log(f"Creating database for language: {lang}")
            lang_db = db_dir / f"{lang}"
            
            # Special handling for C++
            if lang == "cpp":
                cpp_files = list(self.target_path.rglob("*.cpp")) + list(self.target_path.rglob("*.c"))
                cpp_files = [f for f in cpp_files if "node_modules" not in str(f)]
                if not cpp_files:
                    self.log("No C++ source files found (only node_modules), skipping C++ database creation", "WARNING")
                    continue
                
                # Create without autobuilder
                cmd = ["codeql", "database", "create", str(lang_db), "--language=cpp", 
                       f"--source-root={self.target_path}", "--command=", "--threads=4"]
            else:
                cmd = ["codeql", "database", "create", str(lang_db), f"--language={lang}",
                       f"--source-root={self.target_path}", "--threads=4"]
            
            result = self.run_command(cmd, capture_output=True)
            if result.returncode != 0:
                self.log(f"Database creation failed for {lang}", "WARNING")
                continue
            
            # Run analysis
            query_suite = f"codeql/{lang}-queries"
            lang_sarif = self.results_dir / f"codeql-{lang}.sarif"
            
            self.log(f"Running security analysis for {lang} with {query_suite}...")
            cmd = ["codeql", "database", "analyze", str(lang_db), query_suite,
                   "--format=sarif-latest", f"--output={lang_sarif}", "--threads=4"]
            
            result = self.run_command(cmd, capture_output=True)
            if result.returncode != 0:
                self.log(f"Query execution failed for {lang}", "WARNING")
                # Create empty SARIF
                lang_sarif.write_text('{"$schema":"https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json","version":"2.1.0","runs":[{"tool":{"driver":{"name":"CodeQL"}}}]}')
            
            # Copy SARIF as JSON
            lang_json = self.results_dir / f"codeql-{lang}.json"
            if lang_sarif.exists():
                shutil.copy2(lang_sarif, lang_json)
            
            # Generate text report
            lang_text = self.results_dir / f"codeql-{lang}.txt"
            if lang_sarif.exists():
                cmd = ["codeql", "database", "interpret-results", str(lang_db),
                       "--format=sarif-latest", str(lang_sarif), f"--output={lang_text}"]
                result = self.run_command(cmd, capture_output=True)
                if result.returncode != 0:
                    lang_text.write_text("CodeQL analysis completed but report interpretation failed.")
            
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
        
        # Create final output files
        if combined_json.exists() and combined_json.stat().st_size > 100:
            shutil.copy2(combined_json, json_output)
        
        if combined_sarif.exists() and combined_sarif.stat().st_size > 100:
            shutil.copy2(combined_sarif, sarif_output)
        
        if combined_text.exists() and combined_text.stat().st_size > 100:
            shutil.copy2(combined_text, text_output)
        
        # Clean up combined temp files
        for f in [combined_json, combined_sarif, combined_text]:
            if f.exists() and f != json_output and f != sarif_output and f != text_output:
                f.unlink()
        
        if json_output.exists() or sarif_output.exists() or text_output.exists():
            self.log("CodeQL scan completed successfully", "SUCCESS")
            return True
        else:
            self.log("No CodeQL report was generated!", "ERROR")
            return False


if __name__ == "__main__":
    import sys
    
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/SimpleSecCheck/results")
    log_file = os.getenv("LOG_FILE", "/SimpleSecCheck/logs/scan.log")
    config_path = os.getenv("CODEQL_CONFIG_PATH", "/SimpleSecCheck/config/tools/codeql/config.yaml")
    queries_path = os.getenv("CODEQL_QUERIES_PATH", "/SimpleSecCheck/config/tools/codeql/queries")
    
    scanner = CodeQLScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path,
        queries_path=queries_path
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
