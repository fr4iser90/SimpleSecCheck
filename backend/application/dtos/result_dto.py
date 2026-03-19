"""
Result DTO (Data Transfer Object)

This module defines DTOs for scan result data transfer between layers.
DTOs are used to transfer result data without exposing domain entities directly.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from uuid import UUID

from domain.entities.vulnerability import Vulnerability
from domain.datetime_serialization import isoformat_utc
from domain.value_objects.vulnerability_severity import VulnerabilitySeverity


@dataclass
class VulnerabilityDTO:
    """Data Transfer Object for Vulnerability entities."""
    
    # Basic vulnerability information
    id: str
    title: str
    description: str
    severity: VulnerabilitySeverity
    scanner: str
    
    # Scanner information
    scanner_version: Optional[str] = None
    scanner_output: Optional[str] = None
    
    # Vulnerability identifiers
    cwe_id: Optional[str] = None
    cve_id: Optional[str] = None
    
    # Location information
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    function_name: Optional[str] = None
    class_name: Optional[str] = None
    
    # Vulnerability details
    confidence: Optional[str] = None  # HIGH, MEDIUM, LOW
    cvss_score: Optional[float] = None
    cvss_vector: Optional[str] = None
    cvss_severity: Optional[str] = None
    
    # Remediation information
    remediation: Optional[str] = None
    references: List[str] = field(default_factory=list)
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_entity(cls, vulnerability: Vulnerability) -> 'VulnerabilityDTO':
        """Create DTO from Vulnerability entity."""
        return cls(
            id=str(vulnerability.id),
            title=vulnerability.title,
            description=vulnerability.description,
            severity=vulnerability.severity,
            cwe_id=vulnerability.cwe_id,
            cve_id=vulnerability.cve_id,
            scanner=vulnerability.scanner,
            scanner_version=vulnerability.scanner_version,
            scanner_output=vulnerability.scanner_output,
            file_path=vulnerability.file_path,
            line_number=vulnerability.line_number,
            column_number=vulnerability.column_number,
            function_name=vulnerability.function_name,
            class_name=vulnerability.class_name,
            confidence=vulnerability.confidence,
            cvss_score=vulnerability.cvss_score,
            cvss_vector=vulnerability.cvss_vector,
            cvss_severity=vulnerability.cvss_severity,
            remediation=vulnerability.remediation,
            references=vulnerability.references,
            metadata=vulnerability.metadata,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'severity': self.severity.to_dict(),
            'cwe_id': self.cwe_id,
            'cve_id': self.cve_id,
            'scanner': self.scanner,
            'scanner_version': self.scanner_version,
            'scanner_output': self.scanner_output,
            'file_path': self.file_path,
            'line_number': self.line_number,
            'column_number': self.column_number,
            'function_name': self.function_name,
            'class_name': self.class_name,
            'confidence': self.confidence,
            'cvss_score': self.cvss_score,
            'cvss_vector': self.cvss_vector,
            'cvss_severity': self.cvss_severity,
            'remediation': self.remediation,
            'references': self.references,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VulnerabilityDTO':
        """Create DTO from dictionary."""
        severity_data = data.get('severity', {})
        severity = VulnerabilitySeverity.from_dict(severity_data)
        
        return cls(
            id=data['id'],
            title=data['title'],
            description=data['description'],
            severity=severity,
            cwe_id=data.get('cwe_id'),
            cve_id=data.get('cve_id'),
            scanner=data['scanner'],
            scanner_version=data.get('scanner_version'),
            scanner_output=data.get('scanner_output'),
            file_path=data.get('file_path'),
            line_number=data.get('line_number'),
            column_number=data.get('column_number'),
            function_name=data.get('function_name'),
            class_name=data.get('class_name'),
            confidence=data.get('confidence'),
            cvss_score=data.get('cvss_score'),
            cvss_vector=data.get('cvss_vector'),
            cvss_severity=data.get('cvss_severity'),
            remediation=data.get('remediation'),
            references=data.get('references', []),
            metadata=data.get('metadata', {}),
        )


@dataclass
class ScanResultDTO:
    """Data Transfer Object for scan results."""
    
    # Scan information
    scan_id: str
    scanner: str
    status: str  # SUCCESS, FAILED, PARTIAL
    scanner_version: Optional[str] = None
    
    # Result metadata
    message: Optional[str] = None
    duration: Optional[float] = None  # in seconds
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Vulnerabilities
    vulnerabilities: List[VulnerabilityDTO] = field(default_factory=list)
    
    # Statistics
    total_vulnerabilities: int = 0
    critical_vulnerabilities: int = 0
    high_vulnerabilities: int = 0
    medium_vulnerabilities: int = 0
    low_vulnerabilities: int = 0
    info_vulnerabilities: int = 0
    
    # Raw output
    raw_output: Optional[str] = None
    raw_output_format: Optional[str] = None  # JSON, XML, TEXT
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScanResultDTO':
        """Create DTO from dictionary."""
        vulnerabilities_data = data.get('vulnerabilities', [])
        vulnerabilities = [VulnerabilityDTO.from_dict(vuln_data) for vuln_data in vulnerabilities_data]
        
        return cls(
            scan_id=data['scan_id'],
            scanner=data['scanner'],
            scanner_version=data.get('scanner_version'),
            status=data['status'],
            message=data.get('message'),
            duration=data.get('duration'),
            timestamp=datetime.fromisoformat(data['timestamp']) if data.get('timestamp') else datetime.utcnow(),
            vulnerabilities=vulnerabilities,
            total_vulnerabilities=data.get('total_vulnerabilities', 0),
            critical_vulnerabilities=data.get('critical_vulnerabilities', 0),
            high_vulnerabilities=data.get('high_vulnerabilities', 0),
            medium_vulnerabilities=data.get('medium_vulnerabilities', 0),
            low_vulnerabilities=data.get('low_vulnerabilities', 0),
            info_vulnerabilities=data.get('info_vulnerabilities', 0),
            raw_output=data.get('raw_output'),
            raw_output_format=data.get('raw_output_format'),
            metadata=data.get('metadata', {}),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'scan_id': self.scan_id,
            'scanner': self.scanner,
            'scanner_version': self.scanner_version,
            'status': self.status,
            'message': self.message,
            'duration': self.duration,
            'timestamp': isoformat_utc(self.timestamp),
            'vulnerabilities': [vuln.to_dict() for vuln in self.vulnerabilities],
            'total_vulnerabilities': self.total_vulnerabilities,
            'critical_vulnerabilities': self.critical_vulnerabilities,
            'high_vulnerabilities': self.high_vulnerabilities,
            'medium_vulnerabilities': self.medium_vulnerabilities,
            'low_vulnerabilities': self.low_vulnerabilities,
            'info_vulnerabilities': self.info_vulnerabilities,
            'raw_output': self.raw_output,
            'raw_output_format': self.raw_output_format,
            'metadata': self.metadata,
        }
    
    def calculate_statistics(self) -> None:
        """Calculate vulnerability statistics from vulnerabilities list."""
        self.total_vulnerabilities = len(self.vulnerabilities)
        
        severity_counts = {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'info': 0,
        }
        
        for vulnerability in self.vulnerabilities:
            severity_level = vulnerability.severity.level.value
            if severity_level in severity_counts:
                severity_counts[severity_level] += 1
        
        self.critical_vulnerabilities = severity_counts['critical']
        self.high_vulnerabilities = severity_counts['high']
        self.medium_vulnerabilities = severity_counts['medium']
        self.low_vulnerabilities = severity_counts['low']
        self.info_vulnerabilities = severity_counts['info']


@dataclass
class ResultSummaryDTO:
    """Summary DTO for scan results."""
    
    scan_id: str
    scanner: str
    status: str
    total_vulnerabilities: int
    critical_vulnerabilities: int
    high_vulnerabilities: int
    medium_vulnerabilities: int
    low_vulnerabilities: int
    info_vulnerabilities: int
    duration: Optional[float] = None
    timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'scan_id': self.scan_id,
            'scanner': self.scanner,
            'status': self.status,
            'total_vulnerabilities': self.total_vulnerabilities,
            'critical_vulnerabilities': self.critical_vulnerabilities,
            'high_vulnerabilities': self.high_vulnerabilities,
            'medium_vulnerabilities': self.medium_vulnerabilities,
            'low_vulnerabilities': self.low_vulnerabilities,
            'info_vulnerabilities': self.info_vulnerabilities,
            'duration': self.duration,
            'timestamp': isoformat_utc(self.timestamp),
        }


@dataclass
class ResultRequestDTO:
    """Request DTO for processing scan results."""
    
    scan_id: str
    scanner: str
    vulnerabilities: List[Dict[str, Any]]
    status: str = "SUCCESS"
    message: Optional[str] = None
    duration: Optional[float] = None
    timestamp: Optional[datetime] = None
    raw_output: Optional[str] = None
    raw_output_format: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> None:
        """Validate the request data."""
        if not self.scan_id:
            raise ValueError("scan_id is required")
        if not self.scanner:
            raise ValueError("scanner is required")
        if not isinstance(self.vulnerabilities, list):
            raise ValueError("vulnerabilities must be a list")


@dataclass
class AggregatedResultDTO:
    """Aggregated result DTO combining results from multiple scanners."""
    
    scan_id: str
    total_vulnerabilities: int
    critical_vulnerabilities: int
    high_vulnerabilities: int
    medium_vulnerabilities: int
    low_vulnerabilities: int
    info_vulnerabilities: int
    
    # Scanner results
    scanner_results: List[ScanResultDTO] = field(default_factory=list)
    
    # Aggregated vulnerabilities (deduplicated)
    vulnerabilities: List[VulnerabilityDTO] = field(default_factory=list)
    
    # Statistics
    total_scanners: int = 0
    successful_scanners: int = 0
    failed_scanners: int = 0
    duration: Optional[float] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'scan_id': self.scan_id,
            'total_vulnerabilities': self.total_vulnerabilities,
            'critical_vulnerabilities': self.critical_vulnerabilities,
            'high_vulnerabilities': self.high_vulnerabilities,
            'medium_vulnerabilities': self.medium_vulnerabilities,
            'low_vulnerabilities': self.low_vulnerabilities,
            'info_vulnerabilities': self.info_vulnerabilities,
            'scanner_results': [result.to_dict() for result in self.scanner_results],
            'vulnerabilities': [vuln.to_dict() for vuln in self.vulnerabilities],
            'total_scanners': self.total_scanners,
            'successful_scanners': self.successful_scanners,
            'failed_scanners': self.failed_scanners,
            'duration': self.duration,
            'metadata': self.metadata,
        }