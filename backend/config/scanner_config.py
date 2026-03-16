"""
Scanner configuration for backend.

Scanner list and metadata come from the database (synced by scanner container)
and from the Worker API. This module no longer loads a hardcoded YAML;
it returns an empty dict so ScanOrchestrationService does not rely on
duplicate config. Real scan execution is done by the Worker (one scanner
container image); this service is only used for cancel_scan when deleting
a running scan.
"""


def get_scanner_config() -> dict:
    """
    Return scanner config dict. No hardcoded YAML.

    Scanner discovery and metadata: use DB / Worker API (e.g. /api/scanners).
    Scan execution: Worker starts scanner container; backend does not run
    per-scanner containers from this config.
    """
    return {}
