# Changelog

All notable changes to this project will be documented in this file.

## [2.0.0] - 2026-03-16

### Summary

Major release: scanner fully rewritten in Python with a plug-and-play plugin system. Standalone CLI and Docker image remain the primary way to run scans; no breaking changes to how you run the scanner (e.g. `docker compose run scanner` or worker-started containers).

### Added
- **Plugin system (plug-and-play)** – All scanners are plugins under `scanner/plugins/<name>/` (scanner.py, processor.py, optional manifest.yaml). No central scanner list in core; new plugin = new folder.
- **Manifest-driven metadata** – Per-plugin `manifest.yaml`: display_name, version, languages, severity_supported, severity_map, timeout, category, homepage, documentation. No plugin-specific paths or names in core.
- **Generic scan target** – `scan_target` used across orchestrator and plugins (ZAP, Burp, Nuclei, Nikto, Wapiti); "ZAP" only appears in the ZAP plugin.
- **Single source for plugin identity** – Plugin name from module (e.g. `__name__.split(".")[2]`); display name only from manifest.
- **AI Prompt modal (report)** – Policy path from metadata, default `.scanning/finding-policy.json`, options: Include PR workflow, Only Critical/High, Max findings, language (EN/中文/Deutsch). Copy Prompt / Open in new tab.
- **Executive summary alignment** – "Tools Complete" count and list both use `executed_tools` (steps.log) so the X/Y card matches the green list.

### Changed
- **Auth API** – Login/401 no longer turned into 500 (HTTPException handling). Guest sessions: Redis `issued` + admin **revoke** under **`GET/DELETE /api/admin/guest-sessions`** (list / inspect / revoke). Session `expires_at` for guests from issued timestamp.
- **Core no longer knows plugin names** – path_setup, orchestrator, scanner_registry use generic helpers (e.g. `get_plugin_data_dir(plugin_name)`); no "owasp" or other names in core.
- **Backend scanner config** – Removed `scanner_config.yaml`; backend uses `scanner_config.py` (empty/from DB or worker), no hardcoded tool list.
- **Report UI** – Glassmorphism styling; severity badge contrast; tool cards overflow/truncation fixes; modal uses CSS variables only.
- **Finding policy default** – Default path `.scanning/finding-policy.json` in report and AI modal.

### Technical
- Scanner container version set to 2.0.0 (Dockerfile ARG, docker-compose build args).
- Standalone: run with `python3 -m scanner.core.orchestrator` or `docker compose run scanner`; CLI and behaviour unchanged from 1.4 for end users.

---

## [1.4.0] - 2026-02-17

### Added
- **WebUI Support** - Optional web interface for SimpleSecCheck
  - Start scans via web interface at `http://localhost:8080`
  - Live progress and logs during scan execution
  - View HTML reports directly in browser
  - Browse local results with file browser
- Start stack: `docker compose up --build`
  - Follows single-shot principle: no database, no persistent state
  - Auto-shutdown feature for security (configurable idle timeout)

### Security Enhancements
- **Fixed Critical Vulnerabilities:**
  - Updated `python-multipart` from `0.0.6` to `>=0.0.22` (fixes 3 HIGH severity CVEs)
  - Changed default host binding from `0.0.0.0` to `127.0.0.1` (configurable via `HOST` env var)
- **XML Parsing Security:**
  - Replaced `xml.etree.ElementTree` with `defusedxml` to prevent XXE attacks
  - Applied to all XML parsers: ZAP, OWASP Dependency Check, HTML report generation
- **Code Quality Improvements:**
  - Replaced all `Try/Except/Pass` blocks with proper logging
  - Marked all `subprocess` calls with `# nosec` comments (documented security decisions)
  - Improved error handling throughout the codebase
- **Security Score:** Improved from 46 (Good) to 90 (Excellent)
  - 0 Critical Issues
  - 0 High Severity
  - 0 Medium Severity
  - All Bandit warnings resolved

### Removed
- **Unused WebSocket Service** - Removed unused WebSocket components (websocket_service, log_worker, message_queue)

### Changed
- **Error Handling:** All silent exception handlers now log errors for better debugging
- **Security Documentation:** Added inline comments explaining security decisions for subprocess usage

## [1.2.0] - 2025-10-28

### Added
- **Native Mobile Apps Support** - Android and iOS manifest analysis
  - Android: Manifest parsing for permissions, exported components, and vulnerabilities
  - iOS: Plist analysis for security configurations
  - Automatic detection of mobile app projects

### Enhanced - UI/UX Improvements
- **Collapsible Tool Categories** - Auto-collapse clean categories, expand only those with issues
- **Categorized Tool Grid** - Tools grouped by functionality (Static Analysis, Dependencies, Secrets, etc.)
- **Visual Status Indicators** - Color-coded left borders (Green=Clean, Yellow=Issues, Gray=Skipped)
- **Compact Tool Cards** - More efficient space usage with modern card-based layout
- **Tool Status Badges** - Clear indication of findings count
- **Category Statistics** - Shows count of tools with issues per category

### Fixed
- **Snyk Scanner** - No longer fails when SNYK_TOKEN is not provided
  - Gracefully skips with clear message
  - Prevents authentication errors (401)
  - Shows skipped status in report

### Removed
- **LLM Chat Integration** - Removed for single-shot scan compatibility
- **WebUI Interactive Buttons** - Removed scan/refresh controls for standalone reports

### Changed
- **Single-Shot Focus** - Reports are now fully standalone with no backend dependencies
- **Simplified Architecture** - Removed all interactive web features

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