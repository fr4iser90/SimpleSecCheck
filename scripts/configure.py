#!/usr/bin/env python3

import os
import sys
from pathlib import Path
import yaml
import json

def get_input(prompt, default=None):
    if default:
        response = input(f"{prompt} [{default}]: ").strip()
        return response if response else default
    return input(f"{prompt}: ").strip()

def configure_seculite():
    print("SecuLite Configuration Setup")
    print("===========================")
    
    config = {
        "TARGET_URL": get_input("Target URL"),
        "TARGET_PATH": get_input("Target Path"),
        "ZAP_WEBUI_PORT": get_input("ZAP WebUI Port", "8080"),
        "TARGET_PORT": get_input("Target Port"),
        "ZAP_SCAN_LEVEL": get_input("ZAP Scan Level (1=Low, 2=Medium, 3=High)", "1"),
        "SEMGREP_SEVERITY": get_input("Semgrep Severity (INFO, WARNING, ERROR)", "WARNING"),
        "TRIVY_SEVERITY": get_input("Trivy Severity (UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL)", "UNKNOWN,CRITICAL,HIGH"),
        "REPORT_FORMAT": get_input("Report Format (html, json, txt)", "html"),
        "REPORT_PATH": get_input("Report Path", "./results"),
        "LOG_LEVEL": get_input("Log Level (DEBUG, INFO, WARNING, ERROR)", "INFO"),
        "LOG_PATH": get_input("Log Path", "./logs"),
        "DOCKER_NETWORK": get_input("Docker Network", "bridge")
    }
    
    # Create .env file
    env_path = Path(".env")
    with open(env_path, "w") as f:
        f.write("# SecuLite Configuration\n\n")
        for key, value in config.items():
            f.write(f"{key}={value}\n")
    
    print(f"\nConfiguration saved to {env_path}")
    
    # Create config.json for UI
    config_path = Path("config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"Configuration also saved to {config_path} for UI reference")

if __name__ == "__main__":
    try:
        configure_seculite()
    except KeyboardInterrupt:
        print("\nConfiguration cancelled")
        sys.exit(1) 