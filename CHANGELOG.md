# Changelog

All notable changes to this project will be documented in this file.

## [1.1.0] - 2025-10-26

### Added - Major Scanner Expansion
- **25+ New Security Scanners** integrated across multiple categories:

#### Code Analysis Scanners
- CodeQL for advanced SAST analysis
- OWASP Dependency Check for comprehensive vulnerability assessment
- Safety for Python dependency auditing
- Snyk for multi-language dependency scanning
- SonarQube for deep code quality and security analysis
- Checkov for infrastructure-as-code security
- ESLint for JavaScript/TypeScript code quality
- Bandit for Python security issue detection
- Brakeman for Ruby on Rails security analysis

#### Secrets Detection Scanners
- TruffleHog for comprehensive secret detection
- GitLeaks for git history secret scanning
- Detect-secrets for YARL-based secret detection

#### Container Security Scanners
- Clair for container vulnerability scanning
- Anchore for in-depth container image analysis

#### Web Application Scanners
- Nuclei for fast vulnerability scanning
- Wapiti for web application security assessment
- Nikto for web server vulnerability detection
- Burp Suite Professional integration

#### Infrastructure & Network Scanners
- Terraform Security for IaC misconfiguration detection
- Kube-hunter for Kubernetes penetration testing
- Kube-bench for Kubernetes CIS benchmark compliance
- Docker Bench for Docker CIS benchmark compliance
- npm audit for Node.js dependency vulnerabilities

### Enhanced
- Extended coverage from 3 to 28+ scanners
- Comprehensive multi-layer security scanning
- Expanded infrastructure and cloud security capabilities

### Technical
- Plugin-based scanner architecture
- Individual scanner configuration support
- Cached OWASP Dependency Check data for faster scans

## [1.0.0] - 2025-10-26

### Added
- Initial release of SimpleSecCheck
- Dark Mode as default with Light Mode toggle
- ZAP web vulnerability scanning
- Semgrep static code analysis  
- Trivy dependency and container scanning
- Detailed HTML reports with alert cards
- Docker-based single-shot security scanning
- Support for both code and website targets
- Structured results with project-specific directories

### Features
- Deep security scanning with aggressive policies
- Comprehensive vulnerability detection
- Modern web UI with responsive design
- Detailed findings with descriptions and solutions
- Risk-based categorization (Critical, High, Medium, Low, Info)
- Export capabilities for raw reports (XML, JSON, TXT)

### Technical
- Docker Compose orchestration
- Multi-tool integration (ZAP, Semgrep, Trivy)
- Python-based report generation
- Shell script automation
- Volume mounting for persistent results
- Removed monitoring, causes a to big risk