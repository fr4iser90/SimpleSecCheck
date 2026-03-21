# CLI & Docker Usage

This page covers **scan-only** CLI usage (no WebUI) plus common Docker workflows. All examples are **single-shot** runs that exit after the scan finishes.

## Helper script (easiest)

From the repository root, use **`./run-scanner.sh`** — it sets `SCAN_TYPE`, `TARGET_TYPE`, `COLLECT_METADATA`, `SCAN_PROFILE` (quick / standard / deep), and mounts for you:

```bash
chmod +x ./run-scanner.sh
./run-scanner.sh --help
./run-scanner.sh -p quick /path/to/project
./run-scanner.sh -p deep https://example.com
./run-scanner.sh network
./run-scanner.sh --type image nginx:alpine
./run-scanner.sh --git https://github.com/org/repo.git
./run-scanner.sh --orchestrator-help   # env vars inside the container
```

Results go to `./results/<scan_id>/` by default (override with `-o`).

> **Tip:** When using Docker Compose, the OWASP Dependency-Check cache is mounted automatically.

In the **full** `docker-compose.yml`, the `scanner` **service** sets `command: ["sleep", "infinity"]` so a container can stay up for debugging. **One-off scans** must pass the orchestrator explicitly:

`scanner python3 -m scanner.core.orchestrator`

The orchestrator only starts a scan if **`SCAN_ID`** or **`SCAN_TARGET`** is set (see `scanner/core/orchestrator.py`).

---

## 1) Scan-only (Docker Compose)

Use this when you want to run one scan and exit. It uses the `scanner` service image with the command above.

### Default code scan (repository root via compose mount)

Full stack compose mounts the repo at **`/project`**. Scan that path:

```bash
docker compose run --rm \
  -e SCAN_TYPE=code \
  -e TARGET_TYPE=local_mount \
  -e SCAN_TARGET=/project \
  -e TARGET_PATH_IN_CONTAINER=/project \
  -e COLLECT_METADATA=true \
  scanner python3 -m scanner.core.orchestrator
```

### Scan a specific codebase

```bash
docker compose run --rm \
  -v /path/to/project:/target:ro \
  -e SCAN_TYPE=code \
  -e TARGET_TYPE=local_mount \
  -e SCAN_TARGET=/target \
  -e COLLECT_METADATA=true \
  scanner python3 -m scanner.core.orchestrator
```

### Git repository scan

Clone and scan a remote repo (set `SCAN_TARGET` to the clone URL; optional `GIT_BRANCH`):

```bash
docker compose run --rm \
  -e SCAN_TYPE=code \
  -e TARGET_TYPE=git_repo \
  -e SCAN_TARGET=https://github.com/user/repo.git \
  -e GIT_BRANCH=main \
  -e COLLECT_METADATA=true \
  scanner python3 -m scanner.core.orchestrator
```

### Website scan

```bash
docker compose run --rm \
  -e SCAN_TYPE=website \
  -e TARGET_TYPE=website \
  -e SCAN_TARGET=https://example.com \
  -e COLLECT_METADATA=true \
  scanner python3 -m scanner.core.orchestrator
```

### Docker image scan (remote image)

```bash
docker compose run --rm \
  -e SCAN_TYPE=image \
  -e TARGET_TYPE=container_registry \
  -e SCAN_TARGET=nginx:latest \
  -e COLLECT_METADATA=true \
  -v /var/run/docker.sock:/var/run/docker.sock \
  scanner python3 -m scanner.core.orchestrator
```

### Docker image scan (local image)

```bash
docker compose run --rm \
  -e SCAN_TYPE=image \
  -e TARGET_TYPE=container_registry \
  -e SCAN_TARGET=local-image:latest \
  -e COLLECT_METADATA=true \
  -v /var/run/docker.sock:/var/run/docker.sock \
  scanner python3 -m scanner.core.orchestrator
```

### Network / Docker Bench scan

`SCAN_ID` or `SCAN_TARGET` must be set so the orchestrator starts (here: explicit `SCAN_ID`):

```bash
docker compose run --rm \
  -e SCAN_ID=cli-network \
  -e SCAN_TYPE=network \
  -e TARGET_TYPE=network_host \
  -e COLLECT_METADATA=true \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  scanner python3 -m scanner.core.orchestrator
```

---

## 2) WebUI (Optional)

Start the WebUI (nginx) + worker (scanner discovery/asset updates run in the worker):

```bash
docker compose up --build
```

Open **http://localhost:80** and start a scan from the UI (nginx → backend API).

---

## 3) Standalone Docker (docker run)

Use the published image without Compose.

### Code scan (local directory)

```bash
docker run --rm \
  -v /path/to/project:/target:ro \
  -v $(pwd)/results:/app/results \
  -v $(pwd)/scanner/plugins/owasp/data:/app/scanner/plugins/owasp/data \
  -e SCAN_TYPE=code \
  -e TARGET_TYPE=local_mount \
  -e COLLECT_METADATA=true \
  fr4iser/simpleseccheck:latest \
  python3 -m scanner.core.orchestrator
```

### Code scan (Git repository)

Same entrypoint as above; no source mount—`SCAN_TARGET` is the repo URL:

```bash
docker run --rm \
  -v $(pwd)/results:/app/results \
  -e SCAN_TYPE=code \
  -e TARGET_TYPE=git_repo \
  -e SCAN_TARGET=https://github.com/user/repo.git \
  -e GIT_BRANCH=main \
  -e COLLECT_METADATA=true \
  fr4iser/simpleseccheck:latest \
  python3 -m scanner.core.orchestrator
```

Replace `fr4iser/simpleseccheck:latest` with your local tag (e.g. `simpleseccheck-scanner:local`) when built from this repo.

### Website scan

```bash
docker run --rm \
  -e SCAN_TYPE=website \
  -e TARGET_TYPE=website \
  -e SCAN_TARGET=https://example.com \
  -e COLLECT_METADATA=true \
  -v $(pwd)/results:/app/results \
  fr4iser/simpleseccheck:latest \
  python3 -m scanner.core.orchestrator
```

### Docker image scan (remote image)

```bash
docker run --rm \
  -e SCAN_TYPE=image \
  -e TARGET_TYPE=container_registry \
  -e SCAN_TARGET=nginx:latest \
  -e COLLECT_METADATA=true \
  -v $(pwd)/results:/app/results \
  -v /var/run/docker.sock:/var/run/docker.sock \
  fr4iser/simpleseccheck:latest \
  python3 -m scanner.core.orchestrator
```

### Network scan (Docker Bench)

```bash
docker run --rm \
  -e SCAN_ID=cli-network \
  -e SCAN_TYPE=network \
  -e TARGET_TYPE=network_host \
  -e COLLECT_METADATA=true \
  -v $(pwd)/results:/app/results \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  fr4iser/simpleseccheck:latest \
  python3 -m scanner.core.orchestrator
```

---

## 4) Environment Variables (quick reference)

- `TARGET_TYPE`: `local_mount` (default), `git_repo`, `uploaded_code`, `website`, `container_registry`, `network_host`
- `SCAN_TARGET`: Local path is implicit for `local_mount` (`/target` in the container); for `git_repo` use the HTTPS/SSH clone URL; for `website` / `container_registry` use URL or image ref as documented above
- `GIT_BRANCH`: branch to clone (optional, `git_repo` only)
- `SCAN_TYPE`: e.g. `code`, `website`, `image`—must match the scan mode (orchestrator validates)
- `COLLECT_METADATA`: `true` / `false`—required for standalone runs (see `scanner/core/orchestrator.py`)
- `SCAN_SCOPE`: `full` (default) or `tracked` (git-tracked files only)
- `SIMPLESECCHECK_EXCLUDE_PATHS`: comma-separated exclude list for code scans

Full target list and copy-paste `docker run` examples are also printed by:

```bash
docker run --rm fr4iser/simpleseccheck:latest python3 -m scanner.core.help
```

For architecture and adding plugins, see [scanner/README.md](../scanner/README.md).

---

## 5) Output

Results are written to `results/<target>_<timestamp>/` and include:

- `security-summary.html` (main report)
- `scan.log`
- Tool-specific JSON/XML outputs