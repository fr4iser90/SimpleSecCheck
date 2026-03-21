"""
SimpleSecCheck Scanner Container - Help & Usage Information
"""
from scanner.core.scanner_registry import ScanType, TargetType


def print_help():
    """Print comprehensive help information for the scanner container"""
    
    help_text = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    SimpleSecCheck Scanner Container                         ║
║                         CLI Usage & Environment Variables                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

USAGE:
  docker run [OPTIONS] <image> python3 -m scanner.core.orchestrator [--list|--bootstrap-assets|--help]

COMMANDS:
  (no args)          Run a security scan
  --list, -l         List all available scanners and sync to database
  --bootstrap-assets Run manifest-driven asset updates (e.g. vuln DB caches); no scan
  --help, -h         Show this help message

═══════════════════════════════════════════════════════════════════════════════

REQUIRED ENVIRONMENT VARIABLES (for scans):
───────────────────────────────────────────────────────────────────────────────

  SCAN_ID              Unique identifier for this scan
                       - REQUIRED when used with Worker/Backend
                       - OPTIONAL for standalone usage (auto-generated if not provided)
                       Example: SCAN_ID=scan-12345

  SCAN_TYPE            Type of scan to perform (REQUIRED)
                       Valid values: code, image, website, network, mobile
                       Example: SCAN_TYPE=code

  TARGET_TYPE          Type of target being scanned (REQUIRED)
                       Valid values: local_mount, git_repo, uploaded_code,
                                     container_registry, website, network_host,
                                     apk, ipa, openapi_spec
                       Example: TARGET_TYPE=git_repo

  COLLECT_METADATA     Whether to collect scan metadata (REQUIRED)
                       Valid values: true, false
                       Example: COLLECT_METADATA=true

═══════════════════════════════════════════════════════════════════════════════

OPTIONAL ENVIRONMENT VARIABLES:
───────────────────────────────────────────────────────────────────────────────

  SCAN_TARGET                    Target URL/path to scan
                                 - For git_repo: Git repository URL
                                 - For website: Website URL (e.g., https://example.com)
                                 - For container_registry: Container image name
                                 - For local_mount: Path is handled via volume mount
                                 Example: SCAN_TARGET=https://github.com/user/repo.git

  TARGET_PATH_IN_CONTAINER       Path to scan target inside container
                                 Default: /target
                                 Example: TARGET_PATH_IN_CONTAINER=/target

  RESULTS_DIR_IN_CONTAINER       Base directory for scan results
                                 Default: /app/results
                                 Results are stored in: {RESULTS_DIR_IN_CONTAINER}/{SCAN_ID}/
                                 Example: RESULTS_DIR_IN_CONTAINER=/app/results

  SELECTED_SCANNERS              JSON array of scanner names to run (optional)
                                 If not set, all compatible scanners are auto-selected
                                 Example: SELECTED_SCANNERS=["Semgrep", "Bandit", "Safety"]

  SCAN_PROFILE                   Manifest-driven profile: quick, standard, or deep (optional)
                                 Set by the worker from scan config; orchestrator logs this at scan start.
                                 Default when unset: standard
                                 Example: SCAN_PROFILE=deep

  SSC_SCAN_LOG_VERBOSE           Mirror tool stdout/stderr to container console (optional)
                                 Default: unset/false — quiet console; full output still in each tool's log file.
                                 Set to 1, true, or yes for verbose console (legacy-style noise).
                                 Example: SSC_SCAN_LOG_VERBOSE=1

  GIT_BRANCH                     Git branch to clone (for git_repo target type)
                                 Example: GIT_BRANCH=main

  EXCLUDE_PATHS                   Comma-separated list of paths to exclude
                                 Example: EXCLUDE_PATHS=node_modules,venv,.git

  FINDING_POLICY_FILE_IN_CONTAINER  Path to finding policy file inside container
                                     Example: FINDING_POLICY_FILE_IN_CONTAINER=/app/policy.json

  CI_MODE                        Enable CI mode for metadata collection
                                 Valid values: true, false
                                 Default: false
                                 Example: CI_MODE=true

  TARGET_PATH_HOST               Original target path on host (for metadata)
                                 Example: TARGET_PATH_HOST=/home/user/project

  ORIGINAL_TARGET_PATH           Original repository path (for CI mode)
                                 Example: ORIGINAL_TARGET_PATH=/home/user/repo

  PUID                           User ID for file permissions (optional)
                                 Auto-detected from /project mount if available
                                 Example: PUID=1000

  PGID                           Group ID for file permissions (optional)
                                 Auto-detected from /project mount if available
                                 Example: PGID=1000

  LOG_LEVEL                      Logging level (for --list command)
                                 Valid values: DEBUG, INFO, WARNING, ERROR
                                 Default: INFO

  POSTGRES_HOST, POSTGRES_PORT   PostgreSQL (for --list DB sync; no DATABASE_URL)
  POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB

═══════════════════════════════════════════════════════════════════════════════

SCAN TYPE VALUES:
───────────────────────────────────────────────────────────────────────────────
"""
    
    # Add scan types
    scan_types = [st.value for st in ScanType]
    help_text += "  " + ", ".join(scan_types) + "\n\n"
    
    help_text += """
TARGET TYPE VALUES:
───────────────────────────────────────────────────────────────────────────────
"""
    
    # Add target types with descriptions
    target_descriptions = {
        "local_mount": "Local filesystem path mounted into container (dev only)",
        "git_repo": "Git repository URL to clone",
        "uploaded_code": "Uploaded ZIP file extracted and mounted",
        "container_registry": "Container registry image (docker.io, ghcr.io, etc.)",
        "website": "Website URL to scan (dev only)",
        "api_endpoint": "REST/GraphQL API endpoint (dev only)",
        "network_host": "Network host/IP to scan (dev only)",
        "kubernetes_cluster": "Live Kubernetes cluster (dev only)",
        "apk": "Android APK file",
        "ipa": "iOS IPA file",
        "openapi_spec": "OpenAPI/Swagger spec file for API fuzzing"
    }
    
    for target_type in TargetType:
        desc = target_descriptions.get(target_type.value, "")
        help_text += f"  {target_type.value:<25} {desc}\n"
    
    help_text += """
═══════════════════════════════════════════════════════════════════════════════

EXAMPLES:
───────────────────────────────────────────────────────────────────────────────

1. Code scan (local mount):
   docker run --rm \\
     -v /path/to/project:/target:ro \\
     -v $(pwd)/results:/app/results \\
     -e SCAN_TYPE=code \\
     -e TARGET_TYPE=local_mount \\
     -e COLLECT_METADATA=true \\
     <image> python3 -m scanner.core.orchestrator

2. Git repository scan:
   docker run --rm \\
     -v $(pwd)/results:/app/results \\
     -e SCAN_TYPE=code \\
     -e TARGET_TYPE=git_repo \\
     -e SCAN_TARGET=https://github.com/user/repo.git \\
     -e GIT_BRANCH=main \\
     -e COLLECT_METADATA=true \\
     <image> python3 -m scanner.core.orchestrator

3. Container image scan:
   docker run --rm \\
     -v $(pwd)/results:/app/results \\
     -v /var/run/docker.sock:/var/run/docker.sock \\
     -e SCAN_ID=scan-003 \\
     -e SCAN_TYPE=image \\
     -e TARGET_TYPE=container_registry \\
     -e SCAN_TARGET=nginx:latest \\
     -e COLLECT_METADATA=true \\
     <image> python3 -m scanner.core.orchestrator

4. Website scan:
   docker run --rm \\
     -v $(pwd)/results:/app/results \\
     -e SCAN_ID=scan-004 \\
     -e SCAN_TYPE=website \\
     -e TARGET_TYPE=website \\
     -e SCAN_TARGET=https://example.com \\
     -e COLLECT_METADATA=true \\
     <image> python3 -m scanner.core.orchestrator

5. List all scanners:
   docker run --rm \\
     -e POSTGRES_HOST=postgres -e POSTGRES_PORT=5432 \\
     -e POSTGRES_USER=ssc_user -e POSTGRES_PASSWORD=secret \\
     -e POSTGRES_DB=simpleseccheck \\
     <image> python3 -m scanner.core.orchestrator --list

═══════════════════════════════════════════════════════════════════════════════

RESULTS:
───────────────────────────────────────────────────────────────────────────────
Results are stored in: {RESULTS_DIR_IN_CONTAINER}/{SCAN_ID}/

Structure:
  {SCAN_ID}/
    ├── logs/
    │   └── scan.log              Main scan log
    ├── metadata/
    │   └── scan.json             Scan metadata
    ├── summary/
    │   └── summary.html          HTML report
    ├── tools/
    │   └── {scanner_name}/
    │       ├── log               Scanner-specific log
    │       └── report.json       Scanner results
    └── artifacts/
        ├── sarif/               SARIF files
        ├── json/                JSON reports
        ├── html/                HTML reports
        └── logs/                Log files

═══════════════════════════════════════════════════════════════════════════════
"""
    
    print(help_text)


if __name__ == "__main__":
    print_help()
