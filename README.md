# SecuLite

> **Unified, Zero-Config Security for Modern Development**

SecuLite is a developer-first, all-in-one security workflow that brings together state-of-the-art tools for web, code, and AI security. It is designed to minimize setup time and maximize actionable results, so you can focus on fixing—not configuring.

---

## 🚀 Features

- **Automated Web Vulnerability Scanning**
  - OWASP ZAP for XSS, SQLi, misconfigurations, and more
  - Baseline and active scan modes
  - Headless and CI-friendly
- **Static Code Analysis**
  - Semgrep for code bugs, security issues, and AI/prompt injection patterns
  - Custom rules for modern frameworks and LLM/AI code
  - Secret detection and unsafe pattern checks
- **Dependency & Container Scanning**
  - Trivy for open source dependencies, Docker images, and OS packages
  - SCA (Software Composition Analysis) with actionable remediation
- **AI/Prompt Injection Security**
  - Semgrep rules for prompt construction and unsafe input handling
  - (Planned) Integration with emerging LLM security tools (PromptGuard, ProtectAI, etc.)
- **Unified Automation Script**
  - One script (`security-check.sh`) to run all checks in sequence
  - Smart filtering: only new/critical issues highlighted
- **CI/CD Integration**
  - Ready-to-use GitHub Actions, GitLab CI, and generic pipeline examples
- **Extensible & Open**
  - Add your own rules, tools, or integrations easily
  - No vendor lock-in

---

## 🏁 Quick Start

1. **Install Dependencies**
   - [OWASP ZAP](https://www.zaproxy.org/download/)
   - [Semgrep](https://semgrep.dev/docs/getting-started/): `pip install semgrep` or `brew install semgrep`
   - [Trivy](https://aquasecurity.github.io/trivy/v0.18.3/getting-started/): `brew install aquasecurity/trivy/trivy` or see docs

2. **Clone this repo and run:**
   ```sh
   ./security-check.sh
   ```

3. **Review Results**
   - All findings are shown in your terminal or CI logs, prioritized by severity.

---

## 🛠 Usage

- **Local:** Run `./security-check.sh` before every commit or release.
- **CI/CD:** Add the script to your pipeline for automated, scheduled scans.
- **Custom Rules:** Place your Semgrep rules in the `rules/` directory.

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

- Modular: Add/remove tools as needed
- Extensible: Plug in new scanners or custom rules

---

## 🏃 Standalone vs. In-Repo Usage

SecuLite can be used as a **standalone toolkit** or integrated directly into your project:

- **Standalone (empfohlen):**
  - Klone das SecuLite-Repo in ein beliebiges Verzeichnis (z.B. `security/`).
  - Führe das Skript gegen eine beliebige Codebase aus:
    ```sh
    ./scripts/security-check.sh /pfad/zu/deiner/codebase
    ```
- **Im Projekt:**
  - Kopiere den `security/`-Ordner in dein Projekt oder füge ihn als Submodul hinzu.
  - Führe das Skript direkt im Projekt aus:
    ```sh
    ./security/scripts/security-check.sh
    ```

## 📂 Directory Structure

- `rules/` – Semgrep rules
- `zap/` – ZAP configs
- `trivy/` – Trivy configs
- `scripts/` – Automation scripts
- `results/` – Scan results
- `logs/` – Log files
- `.github/workflows/` – GitHub Actions config
- `doc/` – Documentation and extension guides

## 🔌 Extending & Contributing

See [`doc/EXTENDING.md`](doc/EXTENDING.md) for how to add rules, integrate new tools, or contribute.

---

## 🗺 Roadmap

- [ ] Example Semgrep rules for AI/prompt injection
- [ ] ZAP baseline scan config templates
- [ ] Trivy integration for Docker/K8s
- [ ] Unified HTML/JSON reporting
- [ ] Auto-fix suggestions for common issues
- [ ] Smart deduplication and noise reduction
- [ ] LLM security tool integration (PromptGuard, ProtectAI)

---

## 🤝 Contributing

1. Fork the repo and create a feature branch
2. Add your tool, rule, or improvement
3. Submit a pull request with clear description

All contributions are welcome—help us build the future of simple, effective security!

---

## 📄 License

SecuLite is open source, licensed under the MIT License.

## 🐳 Docker Quick Start

1. **Pfad zum zu scannenden Projekt eintragen:**
   - Öffne `docker-compose.yml`
   - Passe die Zeile an:
     ```yaml
     volumes:
       - ./results:/seculite/results
       - ./logs:/seculite/logs
       - /ABSOLUTER/PFAD/ZU/DEINEM/PROJEKT:/target:ro
     ```
     Ersetze `/ABSOLUTER/PFAD/ZU/DEINEM/PROJEKT` durch den Pfad zu deinem Code.

2. **Build & Scan starten:**
   ```sh
   docker compose up --build
   ```

3. **Ergebnisse ansehen:**
   - Text- und JSON-Reports: im Ordner `results/`
   - Detaillierte Logs: im Ordner `logs/`

---

Weitere Hinweise und Beispiele findest du in der Dokumentation und im Ordner `doc/`.

## 🖥️ Optional: ZAP WebUI aktivieren

Für manuelle, explorative Security-Tests kannst du das ZAP Webinterface (WebUI) nutzen:

1. **In `docker-compose.yml` Ports freigeben:**
   ```yaml
   ports:
     - "8080:8080"
   ```
2. **Container starten:**
   ```sh
   docker compose up --build
   ```
3. **WebUI im Browser öffnen:**
   [http://localhost:8080](http://localhost:8080)

**Hinweis:**
- Das WebUI ist nur für manuelle Tests gedacht und sollte in CI/CD-Umgebungen deaktiviert bleiben.
- Im WebUI kannst du ZAP steuern, Scans konfigurieren und Reports direkt ansehen.
