# SecuLite

> **Unified, Zero-Config Security for Modern Development**

SecuLite ist ein All-in-One-Security-Toolkit für moderne Softwareprojekte. Es vereint automatisierte Web-, Code- und Dependency-Scans in einem einzigen CLI-Workflow – und bietet optional eine ZAP-WebUI für manuelle Tests.

---

## 🚀 Features

- **All-in-One-CLI:** Ein Befehl, alles automatisiert (ZAP, Semgrep, Trivy)
- **Web Vulnerability Scanning:** OWASP ZAP (Baseline, Headless, optional WebUI)
- **Static Code Analysis:** Semgrep (Code-Bugs, Secrets, AI/Prompt Injection)
- **Dependency & Container Scanning:** Trivy (SCA, OS, Docker)
- **Unified Reporting:** Ergebnisse als TXT/JSON, übersichtlich aggregiert
- **Extensible & Open:** Eigene Regeln, Tools, Workflows einfach ergänzbar
- **CI/CD-ready:** Docker-basiert, GitHub Actions-Workflow vorhanden

---

## 🏁 Quick Start

1. **Build & Run All-in-One-Scan (Headless/CLI):**
   ```sh
   # Standard-Ziel (localhost:8000)
   docker compose up --build seculite
   # Mit eigener Ziel-URL (z.B. für Web-App im Container/Netzwerk)
   ZAP_TARGET="http://dein-ziel:port" docker compose up seculite
   # Oder als Argument:
   docker compose run seculite ./scripts/security-check.sh http://dein-ziel:port
   ```
   → Führt ZAP (Web), Semgrep (Code), Trivy (Dependencies) sequenziell aus.

2. **(Optional) ZAP WebUI für manuelle Tests:**
   ```sh
   docker compose up --build zap-webui
   ```
   → WebUI erreichbar unter: [http://localhost:8080](http://localhost:8080)

3. **Ergebnisse ansehen:**
   - Reports: im Ordner `results/`
   - Logfiles: im Ordner `logs/`
   - Aggregierte Übersicht: `results/security-summary.txt` und `.json`

---

## ⚙️ Konfiguration & Erweiterung

- **Ziel-URL für ZAP:**
  - Standard: `http://localhost:8000`
  - Per ENV: `ZAP_TARGET="http://dein-ziel:port" docker compose up seculite`
  - Oder als Argument: `docker compose run seculite ./scripts/security-check.sh http://dein-ziel:port`
- **Eigene Regeln:** YAML-Files in `rules/` (Semgrep), `zap/`, `trivy/`
- **Erweiterung:** Siehe `doc/EXTENDING.md`

---

## 🏗 Architektur

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
- **Modular:** Tools und Regeln einfach erweiterbar
- **Headless & WebUI:** CLI und Web-Modus parallel nutzbar

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

- **Phasen 1–5:** Planung, Struktur, All-in-One-CLI, Regeln, CI/CD **abgeschlossen**
- **Phase 6:** Reporting, Aggregation, "Alles okay"-Abschnitte **fertig**; HTML-Report, Benachrichtigung **offen**
- **Phase 7:** Advanced Features (Compliance, Dashboard, Auto-Fix, etc.) **Roadmap**

---

## 🤝 Contributing & Extending

- Siehe [`doc/EXTENDING.md`](doc/EXTENDING.md) für eigene Regeln, Tools, Workflows.
- Pull Requests, Issues und Feature-Vorschläge willkommen!

---

## 📄 License

SecuLite ist Open Source, MIT-Lizenz.

---

## 📝 Changelog (Kernpunkte)
- All-in-One-CLI-Scan (ZAP, Semgrep, Trivy) in einem Container
- Optionaler ZAP-WebUI-Service für manuelle Tests
- Aggregierte Reports, CI/CD-ready, modular erweiterbar
- Doku und Task-Listen synchronisiert mit aktuellem Stand

## Requirements
- Docker (recommended)
- Python 3 (required for ZAP scans; installed in the Docker image)

## ZAP (Web Security Scanning)
- ZAP scans require Python 3 to run zap-baseline.py.
- The Docker image installs Python 3 automatically.
- If running outside Docker, ensure `python3` is available in your PATH. The script will fail early with a clear error if not.

## Troubleshooting: ZAP erzeugt keine Reports?
- Prüfe, ob das Ziel (z.B. http://localhost:8000) im Container erreichbar ist.
- **WICHTIG:** Wenn du einen Webserver auf dem Host scannen willst, setze:
  ```sh
  ZAP_TARGET="http://host.docker.internal:8000" docker compose run seculite
  ```
- Stelle sicher, dass dein Webserver auf `0.0.0.0` lauscht (nicht nur auf `127.0.0.1`).
- Wenn das Target auf `localhost` steht und kein Report erzeugt wird, siehe auch das Log (`logs/security-check.log`) für eine genaue Fehlermeldung und Lösungsvorschlag.
