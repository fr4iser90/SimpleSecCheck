# Changelog

All notable changes to this project will be documented in this file.

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