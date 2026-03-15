"""
iOS Plist Scanner
Python implementation of run_ios_plist_scanner.sh
"""
import os
import json
import plistlib
from pathlib import Path
from typing import List, Optional
from scanner.core.base_scanner import BaseScanner
from scanner.core.scanner_registry import ScanType, TargetType, ScannerCapability


class iOSScanner(BaseScanner):
    """iOS Plist scanner implementation"""
    
    # Metadaten für Auto-Registrierung
    CAPABILITIES = [
        ScannerCapability(
            scan_type=ScanType.MOBILE,
            supported_targets=[TargetType.LOCAL_MOUNT, TargetType.GIT_REPO, TargetType.UPLOADED_CODE],
            supported_artifacts=[],
        )
    ]
    PRIORITY = 41
    REQUIRES_CONDITION = "IS_NATIVE"
    ENV_VARS = {
        "IOS_CONFIG_PATH": "/app/scanner/scanners/ios_plist/config/config.yaml"
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
        Initialize iOS scanner
        
        Args:
            target_path: Path to scan
            results_dir: Results directory
            log_file: Log file path
            config_path: Path to iOS config file (optional)
        """
        super().__init__("ios_plist", target_path, results_dir, log_file, config_path)
    
    def find_plist_files(self) -> List[Path]:
        """Find all Info.plist files"""
        plist_files = []
        for path in self.target_path.rglob("Info.plist"):
            plist_files.append(path)
        return plist_files
    
    def parse_plist(self, plist_path: Path) -> dict:
        """Parse Info.plist and extract security-related information"""
        findings = {
            "file": str(plist_path),
            "bundle_id": "unknown",
            "security_issues": []
        }
        
        try:
            with open(plist_path, 'rb') as f:
                plist_data = plistlib.load(f)
            
            findings["bundle_id"] = plist_data.get('CFBundleIdentifier', 'unknown')
            
            # Check App Transport Security (ATS) configuration
            ats_config = plist_data.get('NSAppTransportSecurity', {})
            if ats_config:
                # Check for arbitrary loads
                allows_arbitrary_loads = ats_config.get('NSAllowsArbitraryLoads', False)
                allows_arbitrary_loads_in_web_content = ats_config.get('NSAllowsArbitraryLoadsInWebContent', False)
                
                if allows_arbitrary_loads:
                    findings["security_issues"].append({
                        "severity": "HIGH",
                        "type": "arbitrary_loads_allowed",
                        "description": "NSAllowsArbitraryLoads is enabled. HTTP traffic is allowed which can lead to MITM attacks.",
                        "recommendation": "Disable NSAllowsArbitraryLoads to enforce HTTPS-only traffic"
                    })
                
                if allows_arbitrary_loads_in_web_content:
                    findings["security_issues"].append({
                        "severity": "MEDIUM",
                        "type": "arbitrary_loads_in_webcontent",
                        "description": "NSAllowsArbitraryLoadsInWebContent is enabled. HTTP allowed in WebViews.",
                        "recommendation": "Use HTTPS for all network requests in WebViews"
                    })
                
                # Check exception domains
                exception_domains = ats_config.get('NSExceptionDomains', {})
                if exception_domains:
                    findings["security_issues"].append({
                        "severity": "MEDIUM",
                        "type": "ats_exceptions",
                        "description": f"ATS exceptions configured for {len(exception_domains)} domain(s). HTTP traffic allowed for these domains.",
                        "recommendation": "Review ATS exceptions and ensure they're necessary. Use certificate pinning if HTTP is required."
                    })
            
            # Check for debug settings
            development_region = plist_data.get('CFBundleDevelopmentRegion', '')
            if development_region:
                # Check if potentially debug-related
                if 'debug' in str(plist_data).lower():
                    findings["security_issues"].append({
                        "severity": "INFO",
                        "type": "debug_indicators",
                        "description": "Potential debug indicators found in plist.",
                        "recommendation": "Ensure production builds don't contain debug configurations"
                    })
            
            # Check for URL schemes (security risk if not validated)
            url_types = plist_data.get('CFBundleURLTypes', [])
            if url_types:
                url_schemes = []
                for url_type in url_types:
                    schemes = url_type.get('CFBundleURLSchemes', [])
                    url_schemes.extend(schemes)
                
                if url_schemes:
                    findings["url_schemes"] = url_schemes
                    findings["security_issues"].append({
                        "severity": "MEDIUM",
                        "type": "url_schemes",
                        "description": f"URL schemes configured: {', '.join(url_schemes)}. Ensure deep link validation is implemented.",
                        "recommendation": "Validate and sanitize all URL scheme handlers to prevent malicious deep links"
                    })
            
            # Check keychain sharing
            keychain_access_groups = plist_data.get('keychain-access-groups', [])
            if keychain_access_groups:
                findings["security_issues"].append({
                    "severity": "INFO",
                    "type": "keychain_sharing",
                    "description": "Keychain access groups configured. Ensure proper access control.",
                    "recommendation": "Limit keychain access groups to only necessary app groups"
                })
        
        except plistlib.InvalidFileException as e:
            self.log(f"Plist parsing error: {e}", "ERROR")
        except Exception as e:
            self.log(f"Error parsing plist: {e}", "ERROR")
        
        return findings
    
    def generate_text_report(self, json_data: dict) -> str:
        """Generate text report from JSON data"""
        lines = []
        lines.append("iOS Plist Security Analysis")
        lines.append("=" * 50)
        lines.append(f"\nTotal Plist Files: {json_data.get('file_count', 0)}")
        lines.append(f"Total Security Issues: {json_data.get('total_security_issues', 0)}")
        
        for finding in json_data.get('findings', []):
            lines.append(f"\nFile: {finding['file']}")
            lines.append(f"  Bundle ID: {finding.get('bundle_id', 'unknown')}")
            
            for issue in finding.get('security_issues', []):
                lines.append(f"\n  [{issue['severity']}] {issue['type']}")
                lines.append(f"    Description: {issue['description']}")
                lines.append(f"    Recommendation: {issue['recommendation']}")
        
        return "\n".join(lines)
    
    def scan(self) -> bool:
        """Run iOS plist scan"""
        self.log("Searching for Info.plist files...")
        
        plist_files = self.find_plist_files()
        
        if not plist_files:
            self.log("No Info.plist files found, skipping scan.", "WARNING")
            return True
        
        self.log(f"Found {len(plist_files)} Info.plist file(s), processing...")
        
        json_output = self.results_dir / "report.json"  # Changed from ios-plist.json
        text_output = self.results_dir / "report.txt"   # Changed from ios-plist.txt
        
        all_findings = []
        for plist_file in plist_files:
            findings = self.parse_plist(plist_file)
            all_findings.append(findings)
        
        result = {
            "status": "success",
            "file_count": len(plist_files),
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
        
        self.log("Plist analysis complete.", "SUCCESS")
        self.log(f"JSON report: {json_output}")
        
        return True


if __name__ == "__main__":
    import sys
    
    target_path = os.getenv("TARGET_PATH", "/target")
    results_dir = os.getenv("RESULTS_DIR", "/app/results")
    log_file = os.getenv("LOG_FILE", "app/results/logs/scan.log")
    config_path = os.getenv("IOS_CONFIG_PATH", "/app/scanner/scanners/ios_plist/config/config.yaml")
    
    scanner = iOSScanner(
        target_path=target_path,
        results_dir=results_dir,
        log_file=log_file,
        config_path=config_path
    )
    
    success = scanner.run()
    sys.exit(0 if success else 1)
