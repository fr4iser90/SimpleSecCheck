# SimpleSecCheck - Single-Shot Security Scanner

> **One Command, Complete Security Analysis**

SimpleSecCheck is a powerful, single-shot Docker-based security scanner that performs comprehensive analysis of your codebase or web applications. Simply run one command and get detailed security reports with no permanent monitoring or infrastructure required.

---

## 🚀 Features

- **Single-Shot Analysis:** One command, complete security scan
- **Dual Scan Modes:** Code analysis OR web application scanning
- **Comprehensive Code Analysis:** Semgrep + Trivy for vulnerabilities and dependencies
- **Web Application Scanning:** OWASP ZAP for web vulnerabilities
- **Unified Reporting:** Consolidated HTML reports with all findings
- **Zero Infrastructure:** No databases, no persistent services, no monitoring
- **Docker-Based:** Isolated, secure scanning environment
- **Easy Usage:** Simple `./run-docker.sh` command for everything

---

## 🏁 Quick Start

### Prerequisites

- Docker and Docker Compose
- Target codebase or web application to scan

### Easy Usage

```bash
# Clone the repository
git clone https://github.com/fr4iser90/SimpleSecCheck.git
cd SimpleSecCheck

# Scan a local code project
./run-docker.sh /path/to/your/project

# Scan a website
./run-docker.sh https://example.com
```

That's it! Results will be available in the `results/` directory.

### What Gets Scanned

**Code Projects:**
- Static code analysis with Semgrep
- Dependency vulnerabilities with Trivy
- Security rule violations

**Websites:**
- Web application vulnerabilities with OWASP ZAP
- Security misconfigurations
- Common web attacks

---

## ⚙️ Configuration (Optional)

### Environment Variables

Create a `.env` file for custom settings:

```bash
# For web scanning
TARGET_URL=https://your-website.com

# For code scanning (default: auto-detected)
SCAN_TYPE=code
```

---

## 🔍 Analysis Details

### Code Analysis Tools
- **Semgrep:** Static code analysis with security-focused rules
- **Trivy:** Dependency vulnerability scanning
- **Custom Rules:** OWASP Top 10, secrets detection, API security

### Web Analysis Tools
- **OWASP ZAP:** Web application vulnerability scanning
- **Comprehensive Coverage:** Common web attacks and misconfigurations
- **Automated Testing:** Spider and active scanning

---

## 📊 Results & Reports

After scanning, results are available in the `results/[project]_[timestamp]/` directory:

- **`security-summary.html`** - Unified HTML report with all findings
- **`semgrep.json`** - Detailed code analysis results (code scans only)
- **`trivy.json`** - Dependency and vulnerability scan results (code scans only)
- **`zap-report.xml`** - Web application vulnerability report (web scans only)
- **`security-check.log`** - Complete scan log

Open the HTML report in your browser for the best experience!

---

## 🛡️ Security Rules

SimpleSecCheck includes comprehensive security rules:

- **Code Bugs** (`rules/code-bugs.yml`) - Common programming errors
- **Secrets Detection** (`rules/secrets.yml`) - API keys, passwords, tokens
- **API Security** (`rules/api-security.yml`) - API vulnerabilities
- **LLM/AI Security** (`rules/llm-ai-security.yml`) - AI-specific vulnerabilities
- **Prompt Injection** (`rules/prompt-injection.yml`) - LLM prompt attacks

---

## 🔧 Advanced Usage

### Custom Rule Sets

Add your own Semgrep rules to the `rules/` directory:

```bash
# Add custom rules
echo "rules:" >> rules/custom.yml
echo "  - id: my-custom-rule" >> rules/custom.yml
echo "    patterns:" >> rules/custom.yml
echo "      - pattern: dangerous_function(...)" >> rules/custom.yml
```

### Direct Docker Compose Usage

For advanced users who want more control:

```bash
# Code scan with custom settings
docker-compose run --rm -v /path/to/code:/target:ro scanner

# Web scan with custom URL
TARGET_URL=https://your-site.com docker-compose run --rm scanner
```

---

## 🚨 Security Considerations

- **Single-Shot Execution:** No persistent services or monitoring
- **Isolated Environment:** Docker containers are destroyed after scanning
- **Read-Only Access:** Target code is mounted read-only
- **No Data Retention:** All scan data is temporary and local
- **Minimal Attack Surface:** No web interfaces or persistent processes

---

## 🤝 Contributing

- Add new security rules to `rules/`
- Extend scanning capabilities in `scripts/tools/`
- Improve report generation in `scripts/`
- Submit issues and feature requests

---

## 📄 License

SimpleSecCheck is Open Source, MIT-licensed.