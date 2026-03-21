# Roadmap

Informal planning notes for this repository—not a fixed schedule. Priorities shift with maintenance and real usage.

---

## Current state (what exists today)

**SimpleSecCheck** is a Docker-first security scanning system:

- **Scanner engine** (`scanner/`) — orchestrator + **plugins** (`scanner/plugins/<id>/` with `manifest.yaml` + Python). Results land under `results/` (HTML, JSON, SARIF, etc.).
- **Full stack (optional)** — `docker compose`: **frontend** (nginx + SPA) → **backend** (FastAPI, Postgres) → **Redis** (queue + events) → **worker** (consumes queue, starts **ephemeral scanner containers** via Docker socket). Same scanner image/logic as CLI-only runs.
- **CLI / single-shot** — run the scanner image without the full platform; see [CLI_DOCKER.md](CLI_DOCKER.md) and the root [README.md](../README.md).

Authoritative **tool names and categories**: [TOOLS.md](TOOLS.md). **Technical plugin layout**: [`scanner/README.md`](../scanner/README.md).

### Plugin inventory (`manifest.yaml` present)

| Area | Plugin IDs (folder = `scanner/plugins/<id>/`) |
|------|-----------------------------------------------|
| Base image (no standalone scan CLI) | `base` |
| Code / SAST / SCA | `bandit`, `brakeman`, `codeql`, `eslint`, `npm_audit`, `owasp`, `safety`, `semgrep`, `snyk`, `sonarqube`, `terraform` |
| Secrets | `detect_secrets`, `gitleaks`, `trufflehog` |
| Containers / infra / IaC | `anchore`, `checkov`, `clair`, `docker_bench`, `kube_bench`, `kube_hunter`, `trivy` |
| Web / DAST | `burp`, `nikto`, `nuclei`, `wapiti`, `zap` |
| Mobile / extra | `android`, `ios`, `ios_plist` |
| Internal test | `test` |

Roadmap items below are **not** “implement Semgrep again”—those scanners are already wired through the plugin model. Follow-up work is **quality**, **ops**, **UX**, and **optional external services**.

---

## Integrations & depth

### SonarQube (server / cloud — not “missing plugin”)

There is already a **`sonarqube`** plugin (`scanner/plugins/sonarqube/`) oriented around **sonar-scanner** and manifest-driven assets.

Open roadmap work is typically **around the server**, not reinventing the plugin:

- Optional **SonarQube Server** (self-hosted) or **SonarCloud**: documented URL + token, project keys, quality gates.
- Optional **Compose profile** or separate stack (SonarQube has its own DB and resource profile)—keep it **optional**, not part of the minimal stack.
- Clearer **UX** for “bring your own SonarQube” vs fully local analysis.

### Additional scanners (new plugins)

New tools should follow [`scanner/README.md`](../scanner/README.md): **manifest** + scanner class, orchestrator pipeline.

Ideas (only when needed): more IaC rulesets, language-specific linters, DAST coverage—add **concrete** gaps rather than a vague “more plugins” line.

### Scanner assets (vuln DBs, rule packs)

- Stronger automation for **asset updates** (manifest `assets` + worker/backend flows where applicable).
- Admin-triggered refresh and documented **offline / air-gapped** usage.

---

## Platform

- **Notifications** — Email is configurable; optional **webhooks** or chat hooks for scan done / failed.
- **Hardening** — Rate limits, policy tuning, deployment notes for **air-gapped** or **registry-restricted** hosts.
- **UI / UX** — Polish scan flows, results presentation, admin screens (ongoing; not listed as a single ticket here).

---

## How to contribute

- Prefer **issues** with **context**: self-hosted vs cloud, auth model, and which **plugin id** or external service you care about.
- New tools: use the **manifest + orchestrator** pattern; avoid one-off scripts outside `scanner/plugins/`.
