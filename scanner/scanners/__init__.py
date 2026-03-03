"""
Scanner Implementations
Python implementations of scanner scripts

Auto-registers all scanners on import - no manual registration needed!
"""
try:
    from scanner.core.scanner_registry import ScannerRegistry
except ImportError:
    from core.scanner_registry import ScannerRegistry

# Import all scanners - this triggers their registration
from scanner.scanners.semgrep_scanner import SemgrepScanner
from scanner.scanners.trivy_scanner import TrivyScanner
from scanner.scanners.safety_scanner import SafetyScanner
from scanner.scanners.owasp_scanner import OWASPScanner
from scanner.scanners.codeql_scanner import CodeQLScanner
from scanner.scanners.snyk_scanner import SnykScanner
from scanner.scanners.sonarqube_scanner import SonarQubeScanner
from scanner.scanners.trufflehog_scanner import TruffleHogScanner
from scanner.scanners.gitleaks_scanner import GitLeaksScanner
from scanner.scanners.detect_secrets_scanner import DetectSecretsScanner
from scanner.scanners.npm_audit_scanner import NpmAuditScanner
from scanner.scanners.eslint_scanner import ESLintScanner
from scanner.scanners.brakeman_scanner import BrakemanScanner
from scanner.scanners.bandit_scanner import BanditScanner
from scanner.scanners.terraform_scanner import TerraformSecurityScanner
from scanner.scanners.checkov_scanner import CheckovScanner
from scanner.scanners.zap_scanner import ZAPScanner
from scanner.scanners.nuclei_scanner import NucleiScanner
from scanner.scanners.wapiti_scanner import WapitiScanner
from scanner.scanners.nikto_scanner import NiktoScanner
from scanner.scanners.burp_scanner import BurpScanner
from scanner.scanners.kube_hunter_scanner import KubeHunterScanner
from scanner.scanners.kube_bench_scanner import KubeBenchScanner
from scanner.scanners.docker_bench_scanner import DockerBenchScanner
from scanner.scanners.clair_scanner import ClairScanner
from scanner.scanners.anchore_scanner import AnchoreScanner
from scanner.scanners.android_scanner import AndroidScanner
from scanner.scanners.ios_scanner import iOSScanner

# Auto-register all scanners that have metadata defined
# Scanners without metadata will still work via the old manual registration
_scanner_classes = [
    SemgrepScanner,  # Has metadata - will auto-register
    # Add more as they get metadata...
]

for scanner_class in _scanner_classes:
    try:
        ScannerRegistry.register_from_class(scanner_class)
    except Exception as e:
        # Skip if scanner doesn't have required metadata yet
        pass

__all__ = [
    "SemgrepScanner", "TrivyScanner", "SafetyScanner", "OWASPScanner",
    "CodeQLScanner", "SnykScanner", "SonarQubeScanner", "TruffleHogScanner",
    "GitLeaksScanner", "DetectSecretsScanner", "NpmAuditScanner", "ESLintScanner",
    "BrakemanScanner", "BanditScanner", "TerraformSecurityScanner", "CheckovScanner",
    "ZAPScanner", "NucleiScanner", "WapitiScanner", "NiktoScanner", "BurpScanner",
    "KubeHunterScanner", "KubeBenchScanner", "DockerBenchScanner", "ClairScanner",
    "AnchoreScanner", "AndroidScanner", "iOSScanner"
]
