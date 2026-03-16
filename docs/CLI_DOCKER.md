# CLI & Docker Usage

This page covers **scan-only** CLI usage (no WebUI) plus common Docker workflows. All examples are **single-shot** runs that exit after the scan finishes.

> **Tip:** When using Docker Compose, the OWASP Dependency-Check cache is mounted automatically.

---

## 1) Scan-only (Docker Compose)

Use this when you want to run one scan and exit. It uses the `scanner` service.

### Default code scan (auto-detect)

```bash
docker compose --profile dev run --rm scanner
```

### Scan a specific codebase

```bash
docker compose --profile dev run --rm \
  -v /path/to/project:/target:ro \
  -e TARGET_TYPE=local_mount \
  scanner
```

### Website scan

```bash
SCAN_TARGET=https://example.com \
docker compose --profile dev run --rm scanner
```

### Docker image scan (remote image)

```bash
SCAN_TARGET=nginx:latest \
docker compose --profile dev run --rm scanner
```

### Docker image scan (local image, dev only)

```bash
SCAN_TARGET=local-image:latest \
docker compose --profile dev run --rm scanner
```

### Network / Docker Bench scan

```bash
TARGET_TYPE=network_host \
docker compose --profile dev run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  scanner
```

---

## 2) WebUI (Optional)

Start the WebUI (nginx) + worker (scanner discovery/asset updates run in the worker):

```bash
docker compose --profile dev up --build
```

Open **http://localhost:8080** and start a scan from the UI.

---

## 3) Standalone Docker (docker run)

Use the published image without Compose.

### Code scan

```bash
docker run --rm \
  -v /path/to/project:/target:ro \
  -v $(pwd)/results:/app/results \
  -v $(pwd)/scanner/plugins/owasp/data:/app/scanner/plugins/owasp/data \
  fr4iser/simpleseccheck:latest \
  python3 -m scanner.core.orchestrator
```

### Website scan

```bash
docker run --rm \
  -e TARGET_TYPE=website \
  -e SCAN_TARGET=https://example.com \
  -v $(pwd)/results:/app/results \
  fr4iser/simpleseccheck:latest \
  python3 -m scanner.core.orchestrator
```

### Docker image scan (remote image)

```bash
docker run --rm \
  -e TARGET_TYPE=container_registry \
  -e SCAN_TARGET=nginx:latest \
  -v $(pwd)/results:/app/results \
  -v /var/run/docker.sock:/var/run/docker.sock \
  fr4iser/simpleseccheck:latest \
  python3 -m scanner.core.orchestrator
```

### Network scan (Docker Bench)

```bash
docker run --rm \
  -e TARGET_TYPE=network_host \
  -v $(pwd)/results:/app/results \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  fr4iser/simpleseccheck:latest \
  python3 -m scanner.core.orchestrator
```

---

## 4) Environment Variables (quick reference)

- `TARGET_TYPE`: `local_mount` (default), `git_repo`, `uploaded_code`, `website`, `container_registry`, `network_host`
- `SCAN_TARGET`: URL or image name depending on `TARGET_TYPE`
- `SCAN_SCOPE`: `full` (default) or `tracked` (git-tracked files only)
- `SIMPLESECCHECK_EXCLUDE_PATHS`: comma-separated exclude list for code scans

---

## 5) Output

Results are written to `results/<target>_<timestamp>/` and include:

- `security-summary.html` (main report)
- `scan.log`
- Tool-specific JSON/XML outputs