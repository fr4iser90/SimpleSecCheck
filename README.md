# SecuLite

> **Unified, Zero-Config Security for Modern Development**

SecuLite is an all-in-one security toolkit for modern software projects. It combines automated web, code, and dependency scans in a single CLI workflow – and optionally offers a ZAP WebUI for manual tests.

---

**Note:** Before starting, adjust the `.env` file to set your local database connection, target URL, and any other environment-specific settings.

---

## 🚀 Features

- **All-in-One CLI:** One command, everything automated (ZAP, Semgrep, Trivy)
- **Web Vulnerability Scanning:** OWASP ZAP (Baseline, Headless, optional WebUI)
- **Static Code Analysis:** Semgrep (code bugs, secrets, AI/prompt injection)
- **Dependency & Container Scanning:** Trivy (SCA, OS, Docker)
- **Unified Reporting:** Results as TXT/JSON, clearly aggregated
- **Extensible & Open:** Easily add your own rules, tools, workflows
- **CI/CD-ready:** Docker-based, GitHub Actions workflow included

---

## 🏁 Quick Start

1. **Web Dashboard (Recommended):**
   - Start the web service:
     ```sh
     docker compose up --build web
     ```
   - **Note:** On the very first start, it may take several minutes before the dashboard is available. The web service waits until the initial scan is complete and results are generated. During this time, the page will not be reachable (404). A loading page or placeholder will be implemented in the future.
   - Once the scan is finished, the dashboard is available at [http://localhost:5000/](http://localhost:5000/).
   - Reports: in the `results/` folder
   - Log files: in the `logs/` folder
   - Aggregated summary: `results/security-summary.txt` and `.json`
   - **Unified HTML Report:** `results/security-summary.html` (combines ZAP, Semgrep, Trivy)

2. **Headless CLI (Console Only):**
   - Run the all-in-one scan directly:
     ```sh
     # Default target (localhost:8000)
     docker compose up --build seculite
     # With custom target URL (e.g., for a web app in a container/network)
     ZAP_TARGET="http://your-target:port" docker compose up seculite
     # Or as an argument:
     docker compose run seculite ./scripts/security-check.sh http://your-target:port
     ```
   - Results as above in the `results/` folder and as HTML report.

3. **ZAP WebUI (Optional, for manual web testing):**
   - Start the ZAP WebUI:
     ```sh
     docker compose up --build zap-webui
     ```
   - WebUI available at: [http://localhost:8080](http://localhost:8080)

---

## 🏗 Architecture

```
[Your Codebase]
     |
     v
[security-check.sh]
     |
     +---> [OWASP ZAP] (web vulns)
     +---> [Semgrep] (code, AI, secrets)
     +---> [Trivy] (deps, containers)
     |
     v
[Unified Results & Filtering]
```
- **Modular:** Tools and rules are easily extendable
- **Headless & WebUI:** CLI and web mode can be used in parallel

---

## 📂 Directory Structure

- `rules/` – Semgrep rules
- `zap/` – ZAP configs
- `trivy/` – Trivy configs
- `scripts/` – Automation scripts
- `results/` – Scan results
- `logs/` – Log files
- `.github/workflows/` – GitHub Actions config
- `doc/` – Documentation and extension guides

---

## 🛠️ Status & Roadmap

- **Phases 1–5:** Planning, structure, all-in-one CLI, rules, CI/CD **completed**
- **Phase 6:** Reporting, aggregation, "All OK" sections **done**; HTML report, notification **pending**
- **Phase 7:** Advanced features (compliance, dashboard, auto-fix, etc.) **roadmap**

---

## 🤝 Contributing & Extending

- See [`doc/EXTENDING.md`](doc/EXTENDING.md) for adding your own rules, tools, workflows.
- Pull requests, issues, and feature suggestions are welcome!

---

## 📄 License

SecuLite is Open Source, MIT-licensed.

---

## 📝 Changelog (Key Points)
- All-in-one CLI scan (ZAP, Semgrep, Trivy) in one container
- Optional ZAP WebUI service for manual tests
- Aggregated reports, CI/CD-ready, modularly extendable
- Documentation and task lists synchronized with current state

## Requirements
- Docker (recommended)
- Python 3 (required for ZAP scans; installed in the Docker image)

## ZAP (Web Security Scanning)
- ZAP scans require Python 3 to run zap-baseline.py.
- The Docker image installs Python 3 automatically.
- If running outside Docker, ensure `python3` is available in your PATH. The script will fail early with a clear error if not.

## Troubleshooting: ZAP does not generate reports?
- Check if the target (e.g. http://localhost:8000) is reachable from inside the container.
- **IMPORTANT:** If you want to scan a web server running on the host, set:
  ```sh
  ZAP_TARGET="http://host.docker.internal:8000" docker compose run seculite
  ```
- Make sure your web server is listening on `0.0.0.0` (not just `127.0.0.1`).
- If the target is set to `localhost` and no report is generated, also check the log (`logs/security-check.log`) for a detailed error message and suggested solution.

## Results Directory

All scan results (ZAP, Semgrep, Trivy) are written to `/seculite/results` inside the container. This directory is mounted to `./results` on the host. You will find all reports (XML, HTML, JSON, TXT, and the unified HTML summary) in the `results/` directory after a run.

**Unified HTML Report:**
- `results/security-summary.html` combines the most important findings from all tools in a single, easy-to-read file.
- Links to the raw tool reports are included for further analysis.

## ZAP Report Robustness (Docker/CI)

ZAP's automation framework sometimes writes reports to unexpected locations or ignores the requested output path, especially in Dockerized or CI environments. To ensure the ZAP report is always available:

- The script now searches the entire container for any `zap-report*` files after the scan and copies them to `/seculite/results` (host: `./results`).
- This guarantees that the ZAP report (typically `zap-report.xml.html`) is always persisted, regardless of ZAP's internal path handling quirks.
- If you add custom ZAP automation or change the report name, the fallback logic will still collect any file matching `zap-report*`.

This approach is robust for CI/CD and local use, and is recommended for all-in-one security toolkits.

![SecuLite Unified Security Scan Summary](docs/screenshots/security-summary-example.png)

See below for an example of the unified HTML report generated by SecuLite:

![Unified Security Scan Example](docs/screenshots/security-summary-example.png)
