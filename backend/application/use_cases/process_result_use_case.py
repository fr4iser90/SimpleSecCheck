"""
Process Result Use Case

This module defines the ProcessResultUseCase for handling scan results.
This is a pure use case with no framework dependencies, containing only business logic.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from domain.entities.vulnerability import Vulnerability
from domain.value_objects.vulnerability_severity import VulnerabilitySeverity
from domain.services.scan_validation_service import ScanValidationService
from domain.exceptions.scan_exceptions import (
    ScanNotFoundException,
    ScanValidationException,
    VulnerabilityProcessingException,
    ResultStorageException
)

from application.dtos.result_dto import (
    ScanResultDTO,
    VulnerabilityDTO,
    AggregatedResultDTO,
    ResultRequestDTO
)


class ProcessResultUseCase:
    """Use case for processing scan results."""
    
    def __init__(self, validation_service: ScanValidationService):
        self.validation_service = validation_service
    
    def execute(self, request: ResultRequestDTO) -> ScanResultDTO:
        """Execute the process result use case."""
        # Validate request data
        request.validate()
        
        # Validate scan results format
        self.validation_service.validate_scan_results(request.vulnerabilities)
        
        # Process vulnerabilities
        vulnerabilities = self._process_vulnerabilities(request.vulnerabilities, request.scanner)
        
        # Create result DTO
        result = ScanResultDTO(
            scan_id=request.scan_id,
            scanner=request.scanner,
            scanner_version=request.metadata.get('scanner_version'),
            status=request.status,
            message=request.message,
            duration=request.duration,
            timestamp=request.timestamp or datetime.utcnow(),
            vulnerabilities=vulnerabilities,
            raw_output=request.raw_output,
            raw_output_format=request.raw_output_format,
            metadata=request.metadata,
        )
        
        # Calculate statistics
        result.calculate_statistics()
        
        return result
    
    def _process_vulnerabilities(self, vulnerabilities_data: List[Dict[str, Any]], scanner: str) -> List[VulnerabilityDTO]:
        """Process vulnerability data and create DTOs."""
        vulnerabilities = []
        
        for vuln_data in vulnerabilities_data:
            try:
                vulnerability = self._create_vulnerability_dto(vuln_data, scanner)
                vulnerabilities.append(vulnerability)
            except Exception as e:
                # Log error but continue processing other vulnerabilities
                raise VulnerabilityProcessingException(
                    scan_id="unknown",
                    message=f"Failed to process vulnerability: {str(e)}",
                    scanner_name=scanner
                )
        
        return vulnerabilities
    
    def _create_vulnerability_dto(self, vuln_data: Dict[str, Any], scanner: str) -> VulnerabilityDTO:
        """Create a VulnerabilityDTO from vulnerability data."""
        # Extract severity information
        severity_level = self._extract_severity(vuln_data)
        severity = VulnerabilitySeverity.from_level(severity_level)
        
        # Extract CVSS information
        cvss_score = vuln_data.get('cvss_score')
        cvss_vector = vuln_data.get('cvss_vector')
        
        if cvss_score:
            severity = VulnerabilitySeverity.from_cvss_score(cvss_score, cvss_vector)
        
        return VulnerabilityDTO(
            id=vuln_data.get('id') or Vulnerability.generate_id(),
            title=vuln_data.get('title', 'Unknown vulnerability'),
            description=vuln_data.get('description', ''),
            severity=severity,
            cwe_id=vuln_data.get('cwe_id'),
            cve_id=vuln_data.get('cve_id'),
            scanner=scanner,
            scanner_version=vuln_data.get('scanner_version'),
            scanner_output=vuln_data.get('scanner_output'),
            file_path=vuln_data.get('file_path'),
            line_number=vuln_data.get('line_number'),
            column_number=vuln_data.get('column_number'),
            function_name=vuln_data.get('function_name'),
            class_name=vuln_data.get('class_name'),
            confidence=vuln_data.get('confidence'),
            cvss_score=cvss_score,
            cvss_vector=cvss_vector,
            cvss_severity=vuln_data.get('cvss_severity'),
            remediation=vuln_data.get('remediation'),
            references=vuln_data.get('references', []),
            metadata=vuln_data.get('metadata', {}),
        )
    
    def _extract_severity(self, vuln_data: Dict[str, Any]) -> str:
        """Extract severity level from vulnerability data."""
        # Try different severity field names
        severity = (
            vuln_data.get('severity') or
            vuln_data.get('level') or
            vuln_data.get('risk') or
            vuln_data.get('cvss_severity') or
            'medium'  # default severity
        )
        
        # Normalize severity values
        severity_map = {
            'critical': 'critical',
            'high': 'high',
            'medium': 'medium',
            'low': 'low',
            'info': 'info',
            'informational': 'info',
            'warning': 'medium',
            'error': 'high',
        }
        
        return severity_map.get(severity.lower(), 'medium')
    
    def aggregate_results(self, scan_id: str, results: List[ScanResultDTO]) -> AggregatedResultDTO:
        """Aggregate results from multiple scanners."""
        if not results:
            raise ScanValidationException("No results to aggregate")
        
        # Calculate total statistics
        total_vulnerabilities = sum(result.total_vulnerabilities for result in results)
        critical_vulnerabilities = sum(result.critical_vulnerabilities for result in results)
        high_vulnerabilities = sum(result.high_vulnerabilities for result in results)
        medium_vulnerabilities = sum(result.medium_vulnerabilities for result in results)
        low_vulnerabilities = sum(result.low_vulnerabilities for result in results)
        info_vulnerabilities = sum(result.info_vulnerabilities for result in results)
        
        # Aggregate vulnerabilities (deduplicate)
        vulnerabilities = self._deduplicate_vulnerabilities(results)
        
        # Calculate scanner statistics
        total_scanners = len(results)
        successful_scanners = sum(1 for result in results if result.status == 'SUCCESS')
        failed_scanners = total_scanners - successful_scanners
        
        # Calculate total duration
        duration = sum(result.duration or 0 for result in results)
        
        return AggregatedResultDTO(
            scan_id=scan_id,
            total_vulnerabilities=total_vulnerabilities,
            critical_vulnerabilities=critical_vulnerabilities,
            high_vulnerabilities=high_vulnerabilities,
            medium_vulnerabilities=medium_vulnerabilities,
            low_vulnerabilities=low_vulnerabilities,
            info_vulnerabilities=info_vulnerabilities,
            scanner_results=results,
            vulnerabilities=vulnerabilities,
            total_scanners=total_scanners,
            successful_scanners=successful_scanners,
            failed_scanners=failed_scanners,
            duration=duration,
        )
    
    def _deduplicate_vulnerabilities(self, results: List[ScanResultDTO]) -> List[VulnerabilityDTO]:
        """Deduplicate vulnerabilities from multiple scanner results."""
        vulnerability_map = {}
        
        for result in results:
            for vulnerability in result.vulnerabilities:
                # Create a unique key for deduplication
                key = self._create_vulnerability_key(vulnerability)
                
                if key not in vulnerability_map:
                    vulnerability_map[key] = vulnerability
                else:
                    # Merge vulnerability information if needed
                    existing = vulnerability_map[key]
                    self._merge_vulnerability_data(existing, vulnerability)
        
        return list(vulnerability_map.values())
    
    def _create_vulnerability_key(self, vulnerability: VulnerabilityDTO) -> str:
        """Create a unique key for vulnerability deduplication."""
        # Use a combination of title, file_path, and line_number for deduplication
        parts = [
            vulnerability.title.lower().strip(),
            vulnerability.file_path or '',
            str(vulnerability.line_number or 0),
            vulnerability.scanner,
        ]
        return '|'.join(parts)
    
    def _merge_vulnerability_data(self, existing: VulnerabilityDTO, new: VulnerabilityDTO) -> None:
        """Merge vulnerability data from multiple scanners."""
        # Keep the most severe severity
        if new.severity > existing.severity:
            existing.severity = new.severity
        
        # Merge references
        existing.references.extend(new.references)
        existing.references = list(set(existing.references))  # Remove duplicates
        
        # Merge metadata
        existing.metadata.update(new.metadata)
    
    def validate_result_integrity(self, result: ScanResultDTO) -> bool:
        """Validate result integrity and consistency."""
        # Check if vulnerability counts match actual vulnerabilities
        if len(result.vulnerabilities) != result.total_vulnerabilities:
            raise ScanValidationException("Vulnerability count mismatch")
        
        # Validate severity distribution
        severity_counts = {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'info': 0,
        }
        
        for vulnerability in result.vulnerabilities:
            severity_level = vulnerability.severity.level.value
            if severity_level in severity_counts:
                severity_counts[severity_level] += 1
        
        if (severity_counts['critical'] != result.critical_vulnerabilities or
            severity_counts['high'] != result.high_vulnerabilities or
            severity_counts['medium'] != result.medium_vulnerabilities or
            severity_counts['low'] != result.low_vulnerabilities or
            severity_counts['info'] != result.info_vulnerabilities):
            raise ScanValidationException("Severity distribution mismatch")
        
        return True
    
    def calculate_risk_score(self, vulnerabilities: List[VulnerabilityDTO]) -> float:
        """Calculate overall risk score based on vulnerabilities."""
        if not vulnerabilities:
            return 0.0
        
        # Risk score calculation based on severity weights
        severity_weights = {
            'critical': 10.0,
            'high': 7.0,
            'medium': 4.0,
            'low': 1.0,
            'info': 0.1,
        }
        
        total_score = 0.0
        for vulnerability in vulnerabilities:
            severity_level = vulnerability.severity.level.value
            weight = severity_weights.get(severity_level, 1.0)
            total_score += weight
        
        # Normalize by number of vulnerabilities
        return total_score / len(vulnerabilities)
    
    def generate_remediation_report(self, vulnerabilities: List[VulnerabilityDTO]) -> Dict[str, Any]:
        """Generate remediation recommendations based on vulnerabilities."""
        remediation_report = {
            'total_vulnerabilities': len(vulnerabilities),
            'by_severity': {},
            'by_type': {},
            'recommendations': [],
        }
        
        # Group by severity
        for vulnerability in vulnerabilities:
            severity = vulnerability.severity.level.value
            remediation_report['by_severity'][severity] = remediation_report['by_severity'].get(severity, 0) + 1
        
        # Group by type (CWE)
        for vulnerability in vulnerabilities:
            cwe_id = vulnerability.cwe_id
            if cwe_id:
                remediation_report['by_type'][cwe_id] = remediation_report['by_type'].get(cwe_id, 0) + 1
        
        # Generate recommendations
        remediation_report['recommendations'] = self._generate_recommendations(vulnerabilities)
        
        return remediation_report
    
    def _generate_recommendations(self, vulnerabilities: List[VulnerabilityDTO]) -> List[str]:
        """Generate remediation recommendations."""
        recommendations = []
        
        # Count vulnerabilities by type
        cwe_counts = {}
        for vulnerability in vulnerabilities:
            if vulnerability.cwe_id:
                cwe_counts[vulnerability.cwe_id] = cwe_counts.get(vulnerability.cwe_id, 0) + 1
        
        # Generate specific recommendations based on common vulnerabilities
        if cwe_counts.get('CWE-79'):  # XSS
            recommendations.append("Implement proper input validation and output encoding to prevent XSS attacks")
        
        if cwe_counts.get('CWE-89'):  # SQL Injection
            recommendations.append("Use parameterized queries and input validation to prevent SQL injection")
        
        if cwe_counts.get('CWE-200'):  # Information Disclosure
            recommendations.append("Review and restrict access to sensitive information")
        
        if cwe_counts.get('CWE-352'):  # CSRF
            recommendations.append("Implement CSRF tokens and proper authentication checks")
        
        # General recommendations
        if any(v.severity.is_critical_or_high() for v in vulnerabilities):
            recommendations.append("Prioritize fixing critical and high severity vulnerabilities")
        
        if len(vulnerabilities) > 10:
            recommendations.append("Consider implementing automated security testing in CI/CD pipeline")
        
        return recommendations