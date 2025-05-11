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

```sh
# Clone the repository
git clone https://github.com/fr4iser90/SimpleSecCheck.git
cd SimpleSecCheck
```

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

## 🤝 Contributing & Extending

- See [`doc/EXTENDING.md`](doc/EXTENDING.md) for adding your own rules, tools, workflows.
- Pull requests, issues, and feature suggestions are welcome!

---

## 📄 License

SecuLite is Open Source, MIT-licensed.
