#!/bin/bash
# Android Manifest Security Scanner for SimpleSecCheck

# Expected Environment Variables:
# TARGET_PATH: Path to the code to scan (e.g., /target)
# RESULTS_DIR: Directory to store results (e.g., /SimpleSecCheck/results)
# LOG_FILE: Path to the main log file

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_android_manifest_scanner.sh] Initializing Android manifest scan..." | tee -a "$LOG_FILE"

# Find AndroidManifest.xml files
echo "[run_android_manifest_scanner.sh] Searching for AndroidManifest.xml files..." | tee -a "$LOG_FILE"
MANIFEST_FILES=$(find "$TARGET_PATH" -name "AndroidManifest.xml" -type f 2>/dev/null)

if [ -z "$MANIFEST_FILES" ]; then
    echo "[run_android_manifest_scanner.sh][Android] No AndroidManifest.xml files found, skipping scan." | tee -a "$LOG_FILE"
    echo "[Android] No manifest files found." >> "$SUMMARY_TXT"
    exit 0
fi

# Process each manifest file
echo "[run_android_manifest_scanner.sh][Android] Found AndroidManifest.xml files, processing..." | tee -a "$LOG_FILE"
ANDROID_JSON="$RESULTS_DIR/android-manifest.json"
ANDROID_TEXT="$RESULTS_DIR/android-manifest.txt"

# Create Python script to parse and analyze manifest
python3 << 'EOF' > "$ANDROID_JSON" 2>>"$LOG_FILE"
import sys
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path

TARGET_PATH = os.environ.get('TARGET_PATH', '/target')
RESULTS_DIR = os.environ.get('RESULTS_DIR', '/SimpleSecCheck/results')
LOG_FILE = os.environ.get('LOG_FILE', '/SimpleSecCheck/logs/security-check.log')

def find_manifest_files(target_path):
    """Find all AndroidManifest.xml files."""
    manifest_files = []
    for path in Path(target_path).rglob('AndroidManifest.xml'):
        manifest_files.append(str(path))
    return manifest_files

def parse_manifest(manifest_path):
    """Parse AndroidManifest.xml and extract security-related information."""
    findings = []
    
    try:
        tree = ET.parse(manifest_path)
        root = tree.getroot()
        
        manifest_findings = {
            "file": manifest_path,
            "permissions": [],
            "uses_features": [],
            "application": {},
            "security_issues": []
        }
        
        # Parse permissions
        for perm in root.findall('.//uses-permission'):
            perm_name = perm.get('{http://schemas.android.com/apk/res/android}name', '')
            if perm_name:
                manifest_findings["permissions"].append(perm_name)
                
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
                    manifest_findings["security_issues"].append({
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
                manifest_findings["application"]["backup_enabled"] = True
                manifest_findings["security_issues"].append({
                    "severity": "MEDIUM",
                    "type": "backup_enabled",
                    "description": "Application backup is enabled. This can lead to data leakage.",
                    "recommendation": "Set android:allowBackup=false in production builds"
                })
            
            if debug_enabled == 'true':
                manifest_findings["application"]["debug_enabled"] = True
                manifest_findings["security_issues"].append({
                    "severity": "HIGH",
                    "type": "debug_mode",
                    "description": "Application is debuggable. This is a security risk in production.",
                    "recommendation": "Set android:debuggable=false in production builds"
                })
        
        # Check for cleartext traffic network security config
        app_element = root.find('./application')
        if app_element is not None:
            uses_cleartext = app_element.get('{http://schemas.android.com/apk/res/android}usesCleartextTraffic')
            if uses_cleartext == 'true':
                manifest_findings["security_issues"].append({
                    "severity": "HIGH",
                    "type": "cleartext_traffic",
                    "description": "Cleartext traffic is allowed. HTTP traffic is not encrypted.",
                    "recommendation": "Set android:usesCleartextTraffic=false to force HTTPS"
                })
        
        findings.append(manifest_findings)
        
    except ET.ParseError as e:
        print(f"[Android] XML parsing error: {e}", file=sys.stderr)
    except Exception as e:
        print(f"[Android] Error parsing manifest: {e}", file=sys.stderr)
    
    return findings

def main():
    manifest_files = find_manifest_files(TARGET_PATH)
    
    if not manifest_files:
        print(json.dumps({"findings": [], "status": "no_files"}))
        return
    
    all_findings = []
    for manifest_file in manifest_files:
        findings = parse_manifest(manifest_file)
        all_findings.extend(findings)
    
    result = {
        "status": "success",
        "file_count": len(manifest_files),
        "findings": all_findings,
        "total_security_issues": sum(len(f.get("security_issues", [])) for f in all_findings)
    }
    
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
EOF

ANDROID_PY_EXIT=$?
if [ $ANDROID_PY_EXIT -eq 0 ]; then
    echo "[run_android_manifest_scanner.sh][Android] Manifest analysis complete." | tee -a "$LOG_FILE"
    echo "[run_android_manifest_scanner.sh][Android] JSON report: $ANDROID_JSON" | tee -a "$LOG_FILE"
    
    # Generate text report
    python3 << 'EOFTEXT' - "$ANDROID_JSON" > "$ANDROID_TEXT" 2>>"$LOG_FILE"
import json
import sys

ANDROID_JSON = sys.argv[1]
with open(ANDROID_JSON) as f:
    data = json.load(f)

print("Android Manifest Security Analysis")
print("=" * 50)
print(f"\nTotal Manifest Files: {data.get('file_count', 0)}")
print(f"Total Security Issues: {data.get('total_security_issues', 0)}")

for finding in data.get('findings', []):
    print(f"\nFile: {finding['file']}")
    print(f"  Permissions: {len(finding.get('permissions', []))}")
    
    for issue in finding.get('security_issues', []):
        print(f"\n  [{issue['severity']}] {issue['type']}")
        print(f"    Description: {issue['description']}")
        print(f"    Recommendation: {issue['recommendation']}")
EOFTEXT
    
    echo "[Android] Manifest scan complete." >> "$SUMMARY_TXT"
    exit 0
else
    echo "[run_android_manifest_scanner.sh][Android][ERROR] Analysis failed with exit code $ANDROID_PY_EXIT" | tee -a "$LOG_FILE"
    exit 1
fi
