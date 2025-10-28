#!/bin/bash
# iOS Plist Security Scanner for SimpleSecCheck

# Expected Environment Variables:
# TARGET_PATH: Path to the code to scan (e.g., /target)
# RESULTS_DIR: Directory to store results (e.g., /SimpleSecCheck/results)
# LOG_FILE: Path to the main log file

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_ios_plist_scanner.sh] Initializing iOS plist scan..." | tee -a "$LOG_FILE"

# Find Info.plist files
echo "[run_ios_plist_scanner.sh] Searching for Info.plist files..." | tee -a "$LOG_FILE"
PLIST_FILES=$(find "$TARGET_PATH" -name "Info.plist" -type f 2>/dev/null)

if [ -z "$PLIST_FILES" ]; then
    echo "[run_ios_plist_scanner.sh][iOS] No Info.plist files found, skipping scan." | tee -a "$LOG_FILE"
    echo "[iOS] No plist files found." >> "$SUMMARY_TXT"
    exit 0
fi

# Process each plist file
echo "[run_ios_plist_scanner.sh][iOS] Found Info.plist files, processing..." | tee -a "$LOG_FILE"
IOS_JSON="$RESULTS_DIR/ios-plist.json"
IOS_TEXT="$RESULTS_DIR/ios-plist.txt"

# Create Python script to parse and analyze plist
python3 << 'EOF' > "$IOS_JSON" 2>>"$LOG_FILE"
import sys
import json
import os
import plistlib
from pathlib import Path

TARGET_PATH = os.environ.get('TARGET_PATH', '/target')
RESULTS_DIR = os.environ.get('RESULTS_DIR', '/SimpleSecCheck/results')
LOG_FILE = os.environ.get('LOG_FILE', '/SimpleSecCheck/logs/security-check.log')

def find_plist_files(target_path):
    """Find all Info.plist files."""
    plist_files = []
    for path in Path(target_path).rglob('Info.plist'):
        plist_files.append(str(path))
    return plist_files

def parse_plist(plist_path):
    """Parse Info.plist and extract security-related information."""
    findings = []
    
    try:
        with open(plist_path, 'rb') as f:
            plist_data = plistlib.load(f)
        
        plist_findings = {
            "file": plist_path,
            "bundle_id": plist_data.get('CFBundleIdentifier', 'unknown'),
            "security_issues": []
        }
        
        # Check App Transport Security (ATS) configuration
        ats_config = plist_data.get('NSAppTransportSecurity', {})
        if ats_config:
            # Check for arbitrary loads
            allows_arbitrary_loads = ats_config.get('NSAllowsArbitraryLoads', False)
            allows_arbitrary_loads_in_web_content = ats_config.get('NSAllowsArbitraryLoadsInWebContent', False)
            
            if allows_arbitrary_loads:
                plist_findings["security_issues"].append({
                    "severity": "HIGH",
                    "type": "arbitrary_loads_allowed",
                    "description": "NSAllowsArbitraryLoads is enabled. HTTP traffic is allowed which can lead to MITM attacks.",
                    "recommendation": "Disable NSAllowsArbitraryLoads to enforce HTTPS-only traffic"
                })
            
            if allows_arbitrary_loads_in_web_content:
                plist_findings["security_issues"].append({
                    "severity": "MEDIUM",
                    "type": "arbitrary_loads_in_webcontent",
                    "description": "NSAllowsArbitraryLoadsInWebContent is enabled. HTTP allowed in WebViews.",
                    "recommendation": "Use HTTPS for all network requests in WebViews"
                })
            
            # Check exception domains
            exception_domains = ats_config.get('NSExceptionDomains', {})
            if exception_domains:
                plist_findings["security_issues"].append({
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
                plist_findings["security_issues"].append({
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
                plist_findings["url_schemes"] = url_schemes
                plist_findings["security_issues"].append({
                    "severity": "MEDIUM",
                    "type": "url_schemes",
                    "description": f"URL schemes configured: {', '.join(url_schemes)}. Ensure deep link validation is implemented.",
                    "recommendation": "Validate and sanitize all URL scheme handlers to prevent malicious deep links"
                })
        
        # Check keychain sharing
        keychain_access_groups = plist_data.get('keychain-access-groups', [])
        if keychain_access_groups:
            plist_findings["security_issues"].append({
                "severity": "INFO",
                "type": "keychain_sharing",
                "description": "Keychain access groups configured. Ensure proper access control.",
                "recommendation": "Limit keychain access groups to only necessary app groups"
            })
        
        findings.append(plist_findings)
        
    except plistlib.InvalidFileException as e:
        print(f"[iOS] Plist parsing error: {e}", file=sys.stderr)
    except Exception as e:
        print(f"[iOS] Error parsing plist: {e}", file=sys.stderr)
    
    return findings

def main():
    plist_files = find_plist_files(TARGET_PATH)
    
    if not plist_files:
        print(json.dumps({"findings": [], "status": "no_files"}))
        return
    
    all_findings = []
    for plist_file in plist_files:
        findings = parse_plist(plist_file)
        all_findings.extend(findings)
    
    result = {
        "status": "success",
        "file_count": len(plist_files),
        "findings": all_findings,
        "total_security_issues": sum(len(f.get("security_issues", [])) for f in all_findings)
    }
    
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
EOF

IOS_PY_EXIT=$?
if [ $IOS_PY_EXIT -eq 0 ]; then
    echo "[run_ios_plist_scanner.sh][iOS] Plist analysis complete." | tee -a "$LOG_FILE"
    echo "[run_ios_plist_scanner.sh][iOS] JSON report: $IOS_JSON" | tee -a "$LOG_FILE"
    
    # Generate text report
    python3 << 'EOFTEXT' - "$IOS_JSON" > "$IOS_TEXT" 2>>"$LOG_FILE"
import json
import sys

IOS_JSON = sys.argv[1]
with open(IOS_JSON) as f:
    data = json.load(f)

print("iOS Plist Security Analysis")
print("=" * 50)
print(f"\nTotal Plist Files: {data.get('file_count', 0)}")
print(f"Total Security Issues: {data.get('total_security_issues', 0)}")

for finding in data.get('findings', []):
    print(f"\nFile: {finding['file']}")
    print(f"  Bundle ID: {finding.get('bundle_id', 'unknown')}")
    
    for issue in finding.get('security_issues', []):
        print(f"\n  [{issue['severity']}] {issue['type']}")
        print(f"    Description: {issue['description']}")
        print(f"    Recommendation: {issue['recommendation']}")
EOFTEXT
    
    echo "[iOS] Plist scan complete." >> "$SUMMARY_TXT"
    exit 0
else
    echo "[run_ios_plist_scanner.sh][iOS][ERROR] Analysis failed with exit code $IOS_PY_EXIT" | tee -a "$LOG_FILE"
    exit 1
fi
