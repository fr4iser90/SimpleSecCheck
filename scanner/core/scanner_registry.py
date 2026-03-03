"""
Scanner Registry
Modern, dynamic scanner registration system - no hardcoded steps!
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
from pathlib import Path


class ScanType(Enum):
    """Scan type enumeration"""
    CODE = "code"
    WEBSITE = "website"
    NETWORK = "network"


@dataclass
class Scanner:
    """Scanner definition"""
    name: str
    scan_types: List[ScanType]  # Which scan types this scanner supports
    script_path: str  # Path to scanner script (inside container)
    enabled: bool = True
    priority: int = 0  # Execution order (lower = earlier)
    requires_condition: Optional[str] = None  # Optional condition (e.g., "IS_NATIVE", "CLAIR_IMAGE")
    env_vars: Optional[Dict[str, str]] = None  # Additional environment variables


class ScannerRegistry:
    """Central registry for all scanners - dynamically extensible"""
    _scanners: Dict[str, Scanner] = {}
    
    @classmethod
    def register(cls, scanner: Scanner):
        """Register a scanner"""
        cls._scanners[scanner.name] = scanner
    
    @classmethod
    def get_scanners_for_type(cls, scan_type: ScanType, conditions: Optional[Dict[str, any]] = None) -> List[Scanner]:
        """
        Get all enabled scanners for a scan type, filtered by conditions
        
        Args:
            scan_type: The scan type to filter by
            conditions: Optional dict of conditions (e.g., {"IS_NATIVE": True, "CLAIR_IMAGE": "image:tag"})
        """
        scanners = []
        for scanner in cls._scanners.values():
            if not scanner.enabled:
                continue
            if scan_type not in scanner.scan_types:
                continue
            
            # Check condition if required
            if scanner.requires_condition:
                if not conditions or not conditions.get(scanner.requires_condition):
                    continue
            
            scanners.append(scanner)
        
        # Sort by priority
        return sorted(scanners, key=lambda s: s.priority)
    
    @classmethod
    def get_total_steps(
        cls, 
        scan_type: ScanType, 
        has_git_clone: bool, 
        collect_metadata: bool,
        conditions: Optional[Dict[str, any]] = None
    ) -> int:
        """
        Dynamically calculate total number of steps for a scan
        
        Args:
            scan_type: The scan type
            has_git_clone: Whether Git clone step is needed
            collect_metadata: Whether metadata collection is enabled
            conditions: Optional conditions for conditional scanners
        """
        steps = 0
        
        if has_git_clone:
            steps += 1  # Git Clone
        
        steps += 1  # Initialization
        
        # Count scanners for this scan type
        scanners = cls.get_scanners_for_type(scan_type, conditions)
        steps += len(scanners)
        
        if collect_metadata:
            steps += 1  # Metadata Collection
        
        steps += 1  # Completion
        
        return steps
    
    @classmethod
    def get_all_scanners(cls) -> List[Scanner]:
        """Get all registered scanners"""
        return list(cls._scanners.values())
    
    @classmethod
    def get_scanner(cls, name: str) -> Optional[Scanner]:
        """Get a specific scanner by name"""
        return cls._scanners.get(name)


# Auto-register all scanners on import
def _register_all_scanners():
    """Register all scanners - add new scanners here!"""
    BASE_DIR = "/SimpleSecCheck"
    TOOLS_DIR = f"{BASE_DIR}/scripts/tools"
    
    # === CODE SCANNERS ===
    
    # Priority 1-10: Core static analysis
    ScannerRegistry.register(Scanner(
        name="Semgrep",
        scan_types=[ScanType.CODE],
        script_path=f"{TOOLS_DIR}/run_semgrep.sh",  # Fallback to Bash if Python not available
        priority=1,
        env_vars={
            "SEMGREP_RULES_PATH": f"{BASE_DIR}/config/rules",
            "PYTHON_SCANNER_CLASS": "scanner.scanners.semgrep_scanner.SemgrepScanner"  # Use Python scanner
        }
    ))
    
    ScannerRegistry.register(Scanner(
        name="Trivy",
        scan_types=[ScanType.CODE],
        script_path=f"{TOOLS_DIR}/run_trivy.sh",  # Fallback to Bash
        priority=2,
        env_vars={
            "TRIVY_CONFIG_PATH": f"{BASE_DIR}/config/tools/trivy/config.yaml",
            "PYTHON_SCANNER_CLASS": "scanner.scanners.trivy_scanner.TrivyScanner"
        }
    ))
    
    ScannerRegistry.register(Scanner(
        name="CodeQL",
        scan_types=[ScanType.CODE],
        script_path=f"{TOOLS_DIR}/run_codeql.sh",  # Fallback to Bash
        priority=3,
        env_vars={
            "CODEQL_CONFIG_PATH": f"{BASE_DIR}/config/tools/codeql/config.yaml",
            "CODEQL_QUERIES_PATH": f"{BASE_DIR}/config/tools/codeql/queries",
            "PYTHON_SCANNER_CLASS": "scanner.scanners.codeql_scanner.CodeQLScanner"
        }
    ))
    
    ScannerRegistry.register(Scanner(
        name="OWASP Dependency Check",
        scan_types=[ScanType.CODE],
        script_path=f"{TOOLS_DIR}/run_owasp_dependency_check.sh",  # Fallback to Bash
        priority=4,
        env_vars={
            "OWASP_DC_CONFIG_PATH": f"{BASE_DIR}/config/tools/owasp-dependency-check/config.yaml",
            "OWASP_DC_DATA_DIR": f"{BASE_DIR}/owasp-dependency-check-data",
            "PYTHON_SCANNER_CLASS": "scanner.scanners.owasp_scanner.OWASPScanner"
        }
    ))
    
    ScannerRegistry.register(Scanner(
        name="Safety",
        scan_types=[ScanType.CODE],
        script_path=f"{TOOLS_DIR}/run_safety.sh",  # Fallback to Bash
        priority=5,
        env_vars={
            "SAFETY_CONFIG_PATH": f"{BASE_DIR}/config/tools/safety/config.yaml",
            "PYTHON_SCANNER_CLASS": "scanner.scanners.safety_scanner.SafetyScanner"
        }
    ))
    
    ScannerRegistry.register(Scanner(
        name="Snyk",
        scan_types=[ScanType.CODE],
        script_path=f"{TOOLS_DIR}/run_snyk.sh",  # Fallback to Bash
        priority=6,
        env_vars={
            "SNYK_CONFIG_PATH": f"{BASE_DIR}/config/tools/snyk/config.yaml",
            "PYTHON_SCANNER_CLASS": "scanner.scanners.snyk_scanner.SnykScanner"
        }
    ))
    
    ScannerRegistry.register(Scanner(
        name="SonarQube",
        scan_types=[ScanType.CODE],
        script_path=f"{TOOLS_DIR}/run_sonarqube.sh",  # Fallback to Bash
        priority=7,
        env_vars={
            "SONARQUBE_CONFIG_PATH": f"{BASE_DIR}/config/tools/sonarqube/config.yaml",
            "PYTHON_SCANNER_CLASS": "scanner.scanners.sonarqube_scanner.SonarQubeScanner"
        }
    ))
    
    # Priority 11-15: Infrastructure as Code
    ScannerRegistry.register(Scanner(
        name="Terraform Security",
        scan_types=[ScanType.CODE],
        script_path=f"{TOOLS_DIR}/run_terraform_security.sh",  # Fallback to Bash
        priority=11,
        env_vars={
            "TERRAFORM_SECURITY_CONFIG_PATH": f"{BASE_DIR}/config/tools/terraform-security/config.yaml",
            "PYTHON_SCANNER_CLASS": "scanner.scanners.terraform_scanner.TerraformSecurityScanner"
        }
    ))
    
    ScannerRegistry.register(Scanner(
        name="Checkov",
        scan_types=[ScanType.CODE],
        script_path=f"{TOOLS_DIR}/run_checkov.sh",  # Fallback to Bash
        priority=12,
        env_vars={
            "CHECKOV_CONFIG_PATH": f"{BASE_DIR}/config/tools/checkov/config.yaml",
            "PYTHON_SCANNER_CLASS": "scanner.scanners.checkov_scanner.CheckovScanner"
        }
    ))
    
    # Priority 16-20: Secret scanning
    ScannerRegistry.register(Scanner(
        name="TruffleHog",
        scan_types=[ScanType.CODE],
        script_path=f"{TOOLS_DIR}/run_trufflehog.sh",  # Fallback to Bash
        priority=16,
        env_vars={
            "TRUFFLEHOG_CONFIG_PATH": f"{BASE_DIR}/config/tools/trufflehog/config.yaml",
            "PYTHON_SCANNER_CLASS": "scanner.scanners.trufflehog_scanner.TruffleHogScanner"
        }
    ))
    
    ScannerRegistry.register(Scanner(
        name="GitLeaks",
        scan_types=[ScanType.CODE],
        script_path=f"{TOOLS_DIR}/run_gitleaks.sh",  # Fallback to Bash
        priority=17,
        env_vars={
            "GITLEAKS_CONFIG_PATH": f"{BASE_DIR}/config/tools/gitleaks/config.yaml",
            "PYTHON_SCANNER_CLASS": "scanner.scanners.gitleaks_scanner.GitLeaksScanner"
        }
    ))
    
    ScannerRegistry.register(Scanner(
        name="Detect-secrets",
        scan_types=[ScanType.CODE],
        script_path=f"{TOOLS_DIR}/run_detect_secrets.sh",  # Fallback to Bash
        priority=18,
        env_vars={
            "DETECT_SECRETS_CONFIG_PATH": f"{BASE_DIR}/config/tools/detect-secrets/config.yaml",
            "PYTHON_SCANNER_CLASS": "scanner.scanners.detect_secrets_scanner.DetectSecretsScanner"
        }
    ))
    
    # Priority 21-25: Language-specific
    ScannerRegistry.register(Scanner(
        name="npm audit",
        scan_types=[ScanType.CODE],
        script_path=f"{TOOLS_DIR}/run_npm_audit.sh",  # Fallback to Bash
        priority=21,
        env_vars={
            "NPM_AUDIT_CONFIG_PATH": f"{BASE_DIR}/config/tools/npm-audit/config.yaml",
            "PYTHON_SCANNER_CLASS": "scanner.scanners.npm_audit_scanner.NpmAuditScanner"
        }
    ))
    
    ScannerRegistry.register(Scanner(
        name="ESLint",
        scan_types=[ScanType.CODE],
        script_path=f"{TOOLS_DIR}/run_eslint.sh",  # Fallback to Bash
        priority=22,
        env_vars={
            "ESLINT_CONFIG_PATH": f"{BASE_DIR}/config/tools/eslint/config.yaml",
            "PYTHON_SCANNER_CLASS": "scanner.scanners.eslint_scanner.ESLintScanner"
        }
    ))
    
    ScannerRegistry.register(Scanner(
        name="Brakeman",
        scan_types=[ScanType.CODE],
        script_path=f"{TOOLS_DIR}/run_brakeman.sh",  # Fallback to Bash
        priority=23,
        env_vars={
            "BRAKEMAN_CONFIG_PATH": f"{BASE_DIR}/config/tools/brakeman/config.yaml",
            "PYTHON_SCANNER_CLASS": "scanner.scanners.brakeman_scanner.BrakemanScanner"
        }
    ))
    
    ScannerRegistry.register(Scanner(
        name="Bandit",
        scan_types=[ScanType.CODE],
        script_path=f"{TOOLS_DIR}/run_bandit.sh",  # Fallback to Bash
        priority=24,
        env_vars={
            "BANDIT_CONFIG_PATH": f"{BASE_DIR}/config/tools/bandit/config.yaml",
            "PYTHON_SCANNER_CLASS": "scanner.scanners.bandit_scanner.BanditScanner"
        }
    ))
    
    # Priority 30-35: Container image scanners (conditional)
    ScannerRegistry.register(Scanner(
        name="Clair",
        scan_types=[ScanType.CODE],
        script_path=f"{TOOLS_DIR}/run_clair.sh",  # Fallback to Bash
        priority=30,
        requires_condition="CLAIR_IMAGE",
        env_vars={
            "CLAIR_CONFIG_PATH": f"{BASE_DIR}/config/tools/clair/config.yaml",
            "PYTHON_SCANNER_CLASS": "scanner.scanners.clair_scanner.ClairScanner"
        }
    ))
    
    ScannerRegistry.register(Scanner(
        name="Anchore",
        scan_types=[ScanType.CODE],
        script_path=f"{TOOLS_DIR}/run_anchore.sh",  # Fallback to Bash
        priority=31,
        requires_condition="ANCHORE_IMAGE",
        env_vars={
            "ANCHORE_CONFIG_PATH": f"{BASE_DIR}/config/tools/anchore/config.yaml",
            "PYTHON_SCANNER_CLASS": "scanner.scanners.anchore_scanner.AnchoreScanner"
        }
    ))
    
    # Priority 40-45: Native mobile app scanners (conditional)
    ScannerRegistry.register(Scanner(
        name="Android",
        scan_types=[ScanType.CODE],
        script_path=f"{TOOLS_DIR}/run_android_manifest_scanner.sh",  # Fallback to Bash
        priority=40,
        requires_condition="IS_NATIVE",
        env_vars={
            "PYTHON_SCANNER_CLASS": "scanner.scanners.android_scanner.AndroidScanner"
        }
    ))
    
    ScannerRegistry.register(Scanner(
        name="iOS",
        scan_types=[ScanType.CODE],
        script_path=f"{TOOLS_DIR}/run_ios_plist_scanner.sh",  # Fallback to Bash
        priority=41,
        requires_condition="IS_NATIVE",
        env_vars={
            "PYTHON_SCANNER_CLASS": "scanner.scanners.ios_scanner.iOSScanner"
        }
    ))
    
    # === WEBSITE SCANNERS ===
    
    ScannerRegistry.register(Scanner(
        name="ZAP",
        scan_types=[ScanType.WEBSITE],
        script_path=f"{TOOLS_DIR}/run_zap.sh",  # Fallback to Bash
        priority=1,
        env_vars={
            "ZAP_CONFIG_PATH": f"{BASE_DIR}/config/tools/zap/baseline.conf",
            "PYTHON_SCANNER_CLASS": "scanner.scanners.zap_scanner.ZAPScanner"
        }
    ))
    
    ScannerRegistry.register(Scanner(
        name="Nuclei",
        scan_types=[ScanType.WEBSITE],
        script_path=f"{TOOLS_DIR}/run_nuclei.sh",  # Fallback to Bash
        priority=2,
        env_vars={
            "PYTHON_SCANNER_CLASS": "scanner.scanners.nuclei_scanner.NucleiScanner"
        }
    ))
    
    ScannerRegistry.register(Scanner(
        name="Wapiti",
        scan_types=[ScanType.WEBSITE],
        script_path=f"{TOOLS_DIR}/run_wapiti.sh",  # Fallback to Bash
        priority=3,
        env_vars={
            "PYTHON_SCANNER_CLASS": "scanner.scanners.wapiti_scanner.WapitiScanner"
        }
    ))
    
    ScannerRegistry.register(Scanner(
        name="Nikto",
        scan_types=[ScanType.WEBSITE],
        script_path=f"{TOOLS_DIR}/run_nikto.sh",  # Fallback to Bash
        priority=4,
        env_vars={
            "PYTHON_SCANNER_CLASS": "scanner.scanners.nikto_scanner.NiktoScanner"
        }
    ))
    
    ScannerRegistry.register(Scanner(
        name="Burp",
        scan_types=[ScanType.WEBSITE],
        script_path=f"{TOOLS_DIR}/run_burp.sh",  # Fallback to Bash
        priority=5,
        env_vars={
            "PYTHON_SCANNER_CLASS": "scanner.scanners.burp_scanner.BurpScanner"
        }
    ))
    
    # === NETWORK SCANNERS ===
    
    ScannerRegistry.register(Scanner(
        name="Kube-hunter",
        scan_types=[ScanType.NETWORK],
        script_path=f"{TOOLS_DIR}/run_kube_hunter.sh",  # Fallback to Bash
        priority=1,
        env_vars={
            "KUBE_HUNTER_CONFIG_PATH": f"{BASE_DIR}/config/tools/kube-hunter/config.yaml",
            "PYTHON_SCANNER_CLASS": "scanner.scanners.kube_hunter_scanner.KubeHunterScanner"
        }
    ))
    
    ScannerRegistry.register(Scanner(
        name="Kube-bench",
        scan_types=[ScanType.NETWORK],
        script_path=f"{TOOLS_DIR}/run_kube_bench.sh",  # Fallback to Bash
        priority=2,
        env_vars={
            "KUBE_BENCH_CONFIG_PATH": f"{BASE_DIR}/config/tools/kube-bench/config.yaml",
            "PYTHON_SCANNER_CLASS": "scanner.scanners.kube_bench_scanner.KubeBenchScanner"
        }
    ))
    
    ScannerRegistry.register(Scanner(
        name="Docker Bench",
        scan_types=[ScanType.NETWORK],
        script_path=f"{TOOLS_DIR}/run_docker_bench.sh",  # Fallback to Bash
        priority=3,
        env_vars={
            "DOCKER_BENCH_CONFIG_PATH": f"{BASE_DIR}/config/tools/docker-bench/config.yaml",
            "PYTHON_SCANNER_CLASS": "scanner.scanners.docker_bench_scanner.DockerBenchScanner"
        }
    ))


# Auto-register on import
_register_all_scanners()
