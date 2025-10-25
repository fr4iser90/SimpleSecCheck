# SecuLite - Deep Security Scanner

> **Single-Shot Deep Security Analysis for Modern Development**

SecuLite is a powerful, single-shot security scanner that performs comprehensive deep analysis of your codebase and web applications. It combines automated web, code, and dependency scans with aggressive scanning policies for maximum security coverage.

---

## 🚀 Features

- **Single-Shot Deep Analysis:** One command, comprehensive security scan
- **Aggressive Web Scanning:** OWASP ZAP with extended spider and scanner settings
- **Deep Code Analysis:** Semgrep with multiple rule sets (custom + auto + security-focused)
- **Comprehensive Dependency Scanning:** Trivy with all vulnerability databases and scanners
- **Intelligent Reporting:** AI-powered analysis with LLM integration
- **Zero Infrastructure:** No databases, no persistent services, no security risks
- **Docker-Based:** Isolated, secure scanning environment

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root or set these variables:

- `TARGET_URL`: Target URL for web scanning (default: `http://host.docker.internal:8000`)
- `SCAN_DEPTH`: Scan depth level (default: `deep`)

### LLM Integration (Optional)

For AI-powered vulnerability analysis:

- `LLM_PROVIDER`: Choose from `openai`, `gemini`, `huggingface`, `groq`, `mistral`, `anthropic`
- `<PROVIDER>_API_KEY`: API key for the chosen provider
- `<PROVIDER>_MODEL`: Specific model (e.g., `OPENAI_MODEL=gpt-4`)

---

## 🏁 Quick Start

### Prerequisites

- Docker and Docker Compose
- Target codebase or web application to scan

### Basic Usage

```bash
# Clone the repository
git clone https://github.com/fr4iser90/SimpleSecCheck.git
cd SimpleSecCheck

# Scan a local project
./run-docker.sh /path/to/your/project

# Scan with custom web target
./run-docker.sh /path/to/your/project http://localhost:3000
```

### Docker Compose Usage

```bash
# Scan with default settings
docker-compose run --rm -v /path/to/target:/target:ro scanner

# Scan with custom environment
TARGET_URL=http://your-app:8080 docker-compose run --rm -v /path/to/target:/target:ro scanner
```

---

## 🔍 Deep Analysis Features

### Web Application Scanning (ZAP)
- **Aggressive Spider:** Extended crawling with JavaScript execution
- **Deep Scanner:** Comprehensive vulnerability detection
- **Extended Timeouts:** More thorough analysis
- **Multiple Report Formats:** XML and HTML outputs

### Code Analysis (Semgrep)
- **Multi-Rule Scanning:** Custom rules + auto rules + security-focused rules
- **Comprehensive Coverage:** All severity levels (ERROR, WARNING, INFO)
- **Security-Focused Rules:** OWASP Top 10, secrets detection, security audit
- **Verbose Output:** Detailed analysis results

### Dependency Scanning (Trivy)
- **All Scanners:** Vulnerabilities, secrets, misconfigurations
- **All Severities:** CRITICAL, HIGH, MEDIUM, LOW
- **Multiple Formats:** JSON and table outputs
- **Comprehensive Coverage:** Filesystem and container image scanning

---

## 📊 Results & Reports

After scanning, results are available in the `results/` directory:

- **`security-summary.html`** - Unified HTML report with all findings
- **`semgrep.json`** - Detailed code analysis results
- **`semgrep-security-deep.json`** - Additional security-focused scan
- **`trivy.json`** - Dependency and vulnerability scan results
- **`trivy-secrets-config.json`** - Secrets and misconfiguration scan
- **`zap-report.xml`** - Web application vulnerability report
- **`zap-report.html`** - Web application vulnerability report (HTML)
- **`security-check.log`** - Complete scan log

---

## 🛡️ Security Rules

SecuLite includes comprehensive security rules:

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

### Trivy Configuration

Customize Trivy scanning in `trivy/config.yaml`:

```yaml
format: json
severity: [CRITICAL,HIGH,MEDIUM,LOW]
scanners: [vuln,secret,config]
```

### ZAP Configuration

Modify ZAP scanning behavior in `zap/baseline.conf`:

```ini
# Extended spider settings
spider.maxDuration=10
scanner.maxDuration=30
scanner.maxRuleTimeInMs=60000
```

---

## 🚨 Security Considerations

- **Docker Socket Access:** Only during scan execution, not persistent
- **No Persistent Data:** All scans are stateless and isolated
- **Minimal Attack Surface:** No web interfaces or persistent services
- **Read-Only Mounts:** Target code is mounted read-only

---

## 🤝 Contributing

- Add new security rules to `rules/`
- Extend scanning capabilities in `scripts/tools/`
- Improve report generation in `scripts/`
- Submit issues and feature requests

---

## 📄 License

SecuLite is Open Source, MIT-licensed.