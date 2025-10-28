#!/usr/bin/env python3
"""
Project Detector for SimpleSecCheck
Detects React Native, Android, and iOS native mobile app projects
"""

import os
import sys
import json
import argparse
from pathlib import Path


def detect_native_projects(target_path):
    """
    Detect if the project is a native mobile app (React Native, Android, or iOS).
    
    Args:
        target_path: Path to the project directory
        
    Returns:
        Dictionary with detection results
    """
    results = {
        "is_react_native": False,
        "is_android": False,
        "is_ios": False,
        "has_native": False,
        "project_type": "unknown",
        "detected_files": []
    }
    
    target = Path(target_path)
    
    if not target.exists():
        return results
    
    # Check for React Native
    package_json = target / "package.json"
    if package_json.exists():
        try:
            with open(package_json) as f:
                package_data = json.load(f)
                dependencies = package_data.get("dependencies", {})
                dev_dependencies = package_data.get("devDependencies", {})
                all_deps = {**dependencies, **dev_dependencies}
                
                # Check for React Native
                if "react-native" in all_deps or "expo" in all_deps:
                    results["is_react_native"] = True
                    results["detected_files"].append(str(package_json))
                    if "expo" in all_deps:
                        results["project_type"] = "react-native-expo"
                    else:
                        results["project_type"] = "react-native"
        except Exception:
            pass
    
    # Check for Android files
    android_manifest = target / "AndroidManifest.xml"
    android_folder = target / "android"
    android_gradle = target / "build.gradle"
    
    if android_manifest.exists():
        results["is_android"] = True
        results["has_native"] = True
        results["detected_files"].append(str(android_manifest))
        
        if not results["project_type"] or results["project_type"] == "unknown":
            results["project_type"] = "android-native"
    
    if android_folder.exists():
        results["is_android"] = True
        results["has_native"] = True
        if not results["project_type"] or results["project_type"] == "unknown":
            results["project_type"] = "android-native"
    
    if android_gradle.exists():
        results["is_android"] = True
        results["has_native"] = True
        if not results["project_type"] or results["project_type"] == "unknown":
            results["project_type"] = "android-native"
    
    # Check in android subfolder
    if android_folder.exists():
        android_manifest = android_folder / "AndroidManifest.xml"
        if android_manifest.exists():
            results["detected_files"].append(str(android_manifest))
    
    # Check for iOS files
    ios_folder = target / "ios"
    info_plist = target / "Info.plist"
    
    if info_plist.exists():
        results["is_ios"] = True
        results["has_native"] = True
        results["detected_files"].append(str(info_plist))
        
        if not results["project_type"] or results["project_type"] == "unknown":
            results["project_type"] = "ios-native"
    
    if ios_folder.exists():
        results["is_ios"] = True
        results["has_native"] = True
        if not results["project_type"] or results["project_type"] == "unknown":
            results["project_type"] = "ios-native"
    
    # Final determination
    if results["is_react_native"]:
        if results["is_android"] or results["is_ios"]:
            results["has_native"] = True
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Detect native mobile app projects")
    parser.add_argument("--target", required=True, help="Target directory to scan")
    parser.add_argument("--format", choices=["json", "text"], default="json", help="Output format")
    
    args = parser.parse_args()
    
    results = detect_native_projects(args.target)
    
    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        print(f"Project Type: {results['project_type']}")
        print(f"React Native: {results['is_react_native']}")
        print(f"Android: {results['is_android']}")
        print(f"iOS: {results['is_ios']}")
        print(f"Has Native Code: {results['has_native']}")
        if results['detected_files']:
            print(f"\nDetected Files:")
            for file in results['detected_files']:
                print(f"  - {file}")
    
    return 0 if results['has_native'] else 0


if __name__ == "__main__":
    sys.exit(main())
