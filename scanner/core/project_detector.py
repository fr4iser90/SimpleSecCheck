#!/usr/bin/env python3
"""
Project Detector for SimpleSecCheck
Detects project types by applying rules from project_detector_config.yaml.
No tool or platform names are hardcoded here; the orchestrator uses result["has_native"].
"""

import json
import argparse
import logging
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

# Config location: same dir as this module. JSON preferred (no deps); YAML optional.
_CONFIG_JSON = "project_detector_config.json"
_CONFIG_YAML = "project_detector_config.yaml"
_THIS_DIR = Path(__file__).resolve().parent

_DEFAULT_CONFIG = {
    "result_keys": ["is_react_native", "is_android", "is_ios", "has_native", "project_type", "detected_files"],
    "project_type_default": "unknown",
    "rules": [],
}


def _load_config():
    """Load detection config from JSON or YAML. No tool names in code."""
    json_path = _THIS_DIR / _CONFIG_JSON
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f) or _DEFAULT_CONFIG
    yaml_path = _THIS_DIR / _CONFIG_YAML
    if yaml_path.exists() and yaml is not None:
        with open(yaml_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or _DEFAULT_CONFIG
    return _DEFAULT_CONFIG.copy()


def _initial_result(config):
    keys = config.get("result_keys", [])
    default_type = config.get("project_type_default", "unknown")
    result = {}
    for k in keys:
        if k == "project_type":
            result[k] = default_type
        elif k == "detected_files":
            result[k] = []
        else:
            result[k] = False
    return result


def _apply_deps_rule(target, rule, result, config):
    file_name = rule.get("file")
    if not file_name:
        return
    path = target / file_name
    if not path.exists():
        return
    deps_key = rule.get("deps_key", ["dependencies", "devDependencies"])
    deps_to_check = rule.get("deps", [])
    project_type_from_dep = rule.get("project_type_from_dep", {})
    add_detected = rule.get("add_detected")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        merged = {}
        for key in deps_key:
            merged.update(data.get(key) or {})
        found = [d for d in deps_to_check if d in merged]
        if not found:
            return
    except Exception:
        logging.debug("Could not read %s for deps rule", path, exc_info=True)
        return

    for key, val in (rule.get("set") or {}).items():
        if key in result:
            result[key] = val
    if "detected_files" in result and add_detected:
        result["detected_files"].append(str(path))
    for dep in found:
        if dep in project_type_from_dep and result.get("project_type") == config.get("project_type_default"):
            result["project_type"] = project_type_from_dep[dep]
            break


def _apply_paths_rule(target, rule, result, config):
    files = rule.get("files") or []
    dirs = rule.get("dirs") or []
    set_map = rule.get("set") or {}
    project_type = rule.get("project_type")
    add_detected = rule.get("add_detected") or []
    add_detected_under_dir = rule.get("add_detected_under_dir") or {}

    matched = False
    for f in files:
        if (target / f).exists():
            matched = True
            break
    if not matched:
        for d in dirs:
            if (target / d).exists():
                matched = True
                break
    if not matched:
        return
    for key, val in set_map.items():
        if key in result:
            result[key] = val
    if project_type and result.get("project_type") == config.get("project_type_default"):
        result["project_type"] = project_type
    detected = result.setdefault("detected_files", [])
    for add in add_detected:
        p = target / add
        if p.exists() and str(p) not in detected:
            detected.append(str(p))
    for dir_name, file_name in add_detected_under_dir.items():
        sub = target / dir_name / file_name
        if sub.exists() and str(sub) not in detected:
            detected.append(str(sub))


def _apply_combine_rule(rule, result):
    when_all = rule.get("when_all") or []
    when_any = rule.get("when_any") or []
    set_map = rule.get("set") or {}
    if when_all and not all(result.get(k) for k in when_all):
        return
    if when_any and not any(result.get(k) for k in when_any):
        return
    for key, val in set_map.items():
        if key in result:
            result[key] = val


def detect_native_projects(target_path):
    """
    Run config-driven project type detection. No tool names in this function;
    all rules and keys come from project_detector_config.yaml.
    """
    config = _load_config()
    result = _initial_result(config)
    target = Path(target_path)
    if not target.exists():
        return result

    for rule in config.get("rules") or []:
        rtype = rule.get("type")
        if rtype == "deps":
            _apply_deps_rule(target, rule, result, config)
        elif rtype == "paths":
            _apply_paths_rule(target, rule, result, config)
        elif rtype == "combine":
            _apply_combine_rule(rule, result)

    return result


def detect_native_app(target_path):
    """Backward-compatible wrapper."""
    return detect_native_projects(target_path)


def main():
    parser = argparse.ArgumentParser(description="Detect native mobile app projects")
    parser.add_argument("--target", required=True, help="Target directory to scan")
    parser.add_argument("--format", choices=["json", "text"], default="json", help="Output format")
    args = parser.parse_args()
    results = detect_native_projects(args.target)

    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        for key in results:
            print(f"{key}: {results[key]}")
        if results.get("detected_files"):
            print("Detected files:")
            for f in results["detected_files"]:
                print(f"  - {f}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
