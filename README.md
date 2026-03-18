# SimpleSecCheck

<p align="center">
  <img src="docs/assets/background.png" alt="SimpleSecCheck Preview" width="100%">
</p>

<div align="center">
  <img src="docs/assets/transparent.png" alt="SimpleSecCheck Logo" width="120">
  <p><strong>Single-shot security scanning for code or web apps.</strong></p>
</div>

SimpleSecCheck runs a complete security scan in one command using Docker. No persistent services, no monitoring, just a report.

---

## Why SimpleSecCheck

- **Single-shot**: run once, get an HTML report.
- **Different modes**: codebase, website, network or image scan.
- **Docker-first**: isolated, reproducible scans.
- **WebUI (optional)**: run scans from a minimal UI.

---

## Quick Start (Recommended)

### 0) Clone the repository

```bash
git clone https://github.com/fr4iser90/SimpleSecCheck.git
cd SimpleSecCheck
```

### 1) Start Frontend (nginx) + Backend + stack

```bash
docker compose up --build
```

Open **http://localhost:8080** and start a scan. The Frontend is **frontend-only** (nginx); `/api/*` is proxied to the backend (worker+scanner).

### 2) CLI-only scan (optional)

```bash
docker compose run --rm scanner
```

### 3) Website scan

```bash
SCAN_TARGET=https://example.com docker compose run --rm scanner
```

Results appear in `results/` as a timestamped folder with `security-summary.html`.

---

## Deploy behind Traefik

For TLS and a reverse proxy, use the Traefik overlay file (see `docker-compose.traefik.yml` and your `DOMAIN` / labels).

- Docker image scans can be restricted to **Docker Hub** only (`nginx:latest` or `docker.io/...`) via app configuration where applicable.
- Use **HTTPS** on the public edge.

---

## Usage Notes

- **Legal**: Scan only systems you own or have explicit permission to test.
- **OWASP cache**: When using Docker Compose, the cache is mounted automatically. For manual `docker run`, mount `scanner/plugins/owasp/data`.
- **CLI detail**: See [CLI & Docker examples](docs/CLI_DOCKER.md) for scan-only commands and full environment variables.

---

## Documentation

- [CLI & Docker examples](docs/CLI_DOCKER.md)
- [Frontend docs](frontend/README.md)
- [Development](docs/DEVELOPMENT.md)
- [Tool list](docs/TOOLS.md)
- [Legal considerations](docs/LEGAL_CONSIDERATIONS.md)
- [Third-party licenses](docs/THIRD_PARTY_LICENSES.md)

---

## License

MIT. See [LICENSE](LICENSE).
