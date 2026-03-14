"""
Android Manifest Scanner
Python implementation of run_android_manifest_scanner.sh
"""
import os
import json
from defusedxml import ElementTree as ET
from pathlib import Path
from typing import List, Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability


class AndroidScanner(BaseScanner):
    """Android Manifest scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.MOBILE,
            supported_targets=[TargetType.LOCAL_MOUNT, TargetType.GIT_REPO, TargetType.UPLOADED_CODE],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 40
    REQUIRES_CONDITION = "IS_NATIVE"
    ENV_VARS = {
        "ANDROID_CONFIG_PATH": "/app/scanner/scanners/android/config/config.yaml"
    }
    # SCANNER_NAME wird automatisch aus manifest.yaml geladen
    
    def __init__(
        self,
        target_path: str,
        results_dir: str,
        log_file: str,
        config_path: Optional[str] = None
    ):
        """
        Initialize Android scanner
        
        Args:
            target_path: Path to scan
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to Android config file (optional)
        """
        super().__init__("android_manifest", target_path, results_dir, log_file, config_path)
    
    def find_manifest_files(self) -> List[Path]:
        """Find all AndroidManifest.xml files"""
        manifest_files = []
        for path in self.target_path.rglob("AndroidManifest.xml"):
            manifest_files.append(path)
        return manifest_files
    
    def parse_manifest(self, manifest_path: Path) -> dict:
        """Parse AndroidManifest.xml and extract security-related information"""
        findings = {
            "file": str(manifest_path),
            "permissions": [],
            "uses_features": [],
            "application": {},
            "security_issues": []
        }
        
        try:
            tree = ET.parse(manifest_path)
            root = tree.getroot()
            
            # Parse permissions
            for perm in root.findall('.//uses-permission'):
                perm_name = perm.get('{http://schemas.android.com/apk/res/android}name', '')
                if perm_name:
                    findings["permissions"].append(perm_name)
                    
                    # Check for dangerous permissions
                    dangerous_perms = [
                        'INTERNET',
                        'CALL_PHONE',
                        'SEND_SMS',
                        'WRITE_EXTERNAL_STORAGE',
                        'READ_EXTERNAL_STORAGE',
                        'CAMERA',
                        'RECORD_AUDIO',
                        'ACCESS_FINE_LOCATION',
                        'ACCESS_COARSE_LOCATION'
                    ]
                    
                    if any(dp in perm_name for dp in dangerous_perms):
                        findings["security_issues"].append({
                            "severity": "HIGH",
                            "type": "dangerous_permission",
                            "permission": perm_name,
                            "description": f"Dangerous permission found: {perm_name}",
                            "recommendation": "Review if this permission is necessary and document its usage"
                        })
            
            # Parse application tag
            app_element = root.find('./application')
            if app_element is not None:
                backup_enabled = app_element.get('{http://schemas.android.com/apk/res/android}allowBackup')
                debug_enabled = app_element.get('{http://schemas.android.com/apk/res/android}debuggable')
                
                if backup_enabled == 'true':
                    findings["application"]["backup_enabled"] = True
                    findings["security_issues"].append({
                        "severity": "MEDIUM",
                        "type": "backup_enabled",
                        "description": "Application backup is enabled. This can lead to data leakage.",
                        "recommendation": "Set android:allowBackup=false in production builds"
                    })
                
                if debug_enabled == 'true':
                    findings["application"]["debug_enabled"] = True
                    findings["security_issues"].append({
                        "severity": "HIGH",
                        "type": "debug_mode",
                        "description": "Application is debuggable. This is a security risk in production.",
                        "recommendation": "Set android:debuggable=false in production builds"
                    })
                
                # Check for cleartext traffic
                uses_cleartext = app_element.get('{http://schemas.android.com/apk/res/android}usesCleartextTraffic')
                if uses_cleartext == 'true':
                    findings["security_issues"].append({
                        "severity": "HIGH",
                        "type": "cleartext_traffic",
                        "description": "Cleartext traffic is allowed. HTTP traffic is not encrypted.",
                        "recommendation": "Set android:usesCleartextTraffic=false to force HTTPS"
                    })
        
        except ET.ParseError as e:
            self.log(f"XML parsing error: {e}", "ERROR")
        except Exception as e:
            self.log(f"Error parsing manifest: {e}", "ERROR")
        
        return findings
    
    def generate_text_report(self, json_data: dict) -> str:
        """Generate text report from JSON data"""
        lines = []
        lines.append("Android Manifest Security Analysis")
        lines.append("=" * 50)
        lines.append(f"\nTotal Manifest Files: {json_data.get('file_count', 0)}")
        lines.append(f"Total Security Issues: {json_data.get('total_security_issues', 0)}")
        
        for finding in json_data.get('findings', []):
            lines.append(f"\nFile: {finding['file']}")
            lines.append(f"  Permissions: {len(finding.get('permissions', []))}")
            
            for issue in finding.get('security_issues', []):
                lines.append(f"\n  [{issue['severity']}] {issue['type']}")
                lines.append(f"    Description: {issue['description']}")
                lines.append(f"    Recommendation: {issue['recommendation']}")
        
        return "\n".join(lines)
    
    def scan(self) -> bool:
        """Run Android manifest scan"""
        self.log("Searching for AndroidManifest.xml files...")
        
        manifest_files = self.find_manifest_files()
        
        if not manifest_files:
            self.log("No AndroidManifest.xml files found, skipping scan.", "WARNING")
            return True
        
        self.log(f"Found {len(manifest_files)} AndroidManifest.xml file(s), processing...")
        
        json_output = self.results_dir / "android-manifest.json"
        text_output = self.results_dir / "android-manifest.txt"
        
        all_findings = []
        for manifest_file in manifest_files:
            findings = self.parse_manifest(manifest_file)
            all_findings.append(findings)
        
        result = {
            "status": "success",
            "file_count": len(manifest_files),
            "findings": all_findings,
            "total_security_issues": sum(len(f.get("security_issues", [])) for f in all_findings)
        }
        
        # Write JSON report
        with open(json_output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        
        # Write text report
        text_content = self.generate_text_report(result)
        with open(text_output, "w", encoding="utf-8") as f:
            f.write(text_content)
        
        self.log("Manifest analysis complete.", "SUCCESS")
        self.log(f"JSON report: {json_output}")
        
        return True


if __name__ == "__main__":
    import sys
    
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/app/results")
    log_file = os.getenv("LOG_FILE", "app/results/logs/scan.log")
    config_path = os.getenv("ANDROID_CONFIG_PATH", "/app/scanner/scanners/android_manifest/config/config.yaml")
    
    scanner = AndroidScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
