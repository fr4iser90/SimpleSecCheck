#!/usr/bin/env python3
"""
Scan Metadata Collector
Collects metadata about the scanned project (ONLY when explicitly enabled by user)
"""

import os
import json
import subprocess  # nosec B404 - Used safely with hardcoded commands, timeouts, and shell=False
from pathlib import Path
from typing import Optional, Dict, Any


def get_git_info(target_path: str) -> Dict[str, Optional[str]]:
    """
    Collect Git repository information from target path.
    Returns empty dict if not a git repo or git command fails.
    """
    git_info = {
        "repository_url": None,
        "branch": None,
        "commit_hash": None,
        "commit_message": None,
        "is_dirty": False
    }
    
    try:
        # Check if target is a git repository
        git_dir = Path(target_path) / ".git"
        if not git_dir.exists():
            return git_info
        
        # Get remote URL
        # Security: Hardcoded git command, no user input, timeout set
        try:
            result = subprocess.run(  # nosec B603, B607
                ["git", "-C", target_path, "config", "--get", "remote.origin.url"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                git_info["repository_url"] = result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Get current branch
        # Security: Hardcoded git command, no user input, timeout set
        try:
            result = subprocess.run(  # nosec B603, B607
                ["git", "-C", target_path, "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                git_info["branch"] = result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Get commit hash
        # Security: Hardcoded git command, no user input, timeout set
        try:
            result = subprocess.run(  # nosec B603, B607
                ["git", "-C", target_path, "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                git_info["commit_hash"] = result.stdout.strip()[:12]  # Short hash
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Get commit message
        # Security: Hardcoded git command, no user input, timeout set
        try:
            result = subprocess.run(  # nosec B603, B607
                ["git", "-C", target_path, "log", "-1", "--pretty=%s"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                git_info["commit_message"] = result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Check if working directory is dirty
        # Security: Hardcoded git command, no user input, timeout set
        try:
            result = subprocess.run(  # nosec B603, B607
                ["git", "-C", target_path, "diff", "--quiet"],
                capture_output=True,
                timeout=5,
                check=False
            )
            git_info["is_dirty"] = result.returncode != 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
            
    except Exception as e:
        # Non-critical: Git info collection failed, don't break scan
        import logging
        logging.debug(f"Git metadata collection failed (non-critical): {e}")
    
    return git_info


def collect_scan_metadata(
    target_path: str,
    scan_type: str,
    results_dir: str,
    finding_policy: Optional[str] = None,
    ci_mode: bool = False,
    target_path_host: Optional[str] = None
) -> Dict[str, Any]:
    """
    Collect metadata about the scan.
    ONLY call this when user explicitly enabled metadata collection!
    
    Args:
        target_path: Path to scanned project (container path, e.g., /target)
        scan_type: Type of scan (code, website, network)
        results_dir: Results directory path
        finding_policy: Optional finding policy file path
        ci_mode: Whether CI mode was enabled
        target_path_host: Optional host path (e.g., /home/user/project) for better project name extraction
    
    Returns:
        Dictionary with scan metadata
    """
    # Use host path for project name extraction, container path for file access
    actual_path_for_name = target_path_host if target_path_host else target_path
    actual_path_for_files = target_path  # Always use container path (files are mounted there)
    
    metadata = {
        "scan_type": scan_type,
        "target_path": target_path,  # Container path (/target)
        "project_name": None,
        "results_dir": results_dir,
        "finding_policy": finding_policy,
        "ci_mode": ci_mode,
        "git_info": {},
        "scan_config": {
            "finding_policy_used": finding_policy is not None,
            "ci_mode": ci_mode
        }
    }
    
    # Extract project name from host path if available, otherwise from container path
    if actual_path_for_name:
        try:
            abs_path = os.path.abspath(actual_path_for_name)
            metadata["project_name"] = os.path.basename(abs_path.rstrip("/"))
        except Exception:
            metadata["project_name"] = os.path.basename(actual_path_for_name) if actual_path_for_name else None
    
    # Collect Git information
    # IMPORTANT: For CI mode, use target_path_host (original repo) instead of target_path (tracked snapshot)
    # The tracked snapshot has no .git directory, so we need the original repository
    if scan_type == "code":
        # For CI mode, target_path_host is the container path to original repo (e.g., /original-target)
        # For normal mode, use target_path (container path like /target)
        if ci_mode and target_path_host and os.path.exists(target_path_host):
            # CI Mode: Use original repository path (tracked snapshot has no .git)
            # target_path_host is already a container path like /original-target
            metadata["git_info"] = get_git_info(target_path_host)
        elif actual_path_for_files and os.path.exists(actual_path_for_files):
            # Normal mode: Use container path
            metadata["git_info"] = get_git_info(actual_path_for_files)
    
    return metadata


def save_metadata(metadata: Dict[str, Any], results_dir: str) -> bool:
    """
    Save metadata to scan.json in metadata directory.
    
    Args:
        metadata: Metadata dictionary
        results_dir: Metadata directory path (e.g., /app/results/{scan_id}/metadata)
    
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        results_path = Path(results_dir)
        results_path.mkdir(parents=True, exist_ok=True)
        
        metadata_file = results_path / "scan.json"  # Changed from scan-metadata.json
        
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception:
        # Silently fail - don't break scan if metadata save fails
        return False


def load_metadata(results_dir: str) -> Optional[Dict[str, Any]]:
    """
    Load metadata from scan.json in metadata directory.
    
    Args:
        results_dir: Metadata directory path (e.g., /app/results/{scan_id}/metadata)
    
    Returns:
        Metadata dictionary or None if not found/invalid
    """
    try:
        metadata_file = Path(results_dir) / "scan.json"  # Changed from scan-metadata.json
        if not metadata_file.exists():
            return None
        
        with open(metadata_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
