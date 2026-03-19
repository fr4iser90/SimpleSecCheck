# Roadmap

Informal planning notes—not a commitment schedule. Priorities shift with maintenance and contributions.

## Integrations

- **SonarQube** — Optional **SonarQube Server** (or SonarCloud) integration: push analysis from CI or map findings into reports alongside existing SAST/SCA tools; evaluate API auth, project keys, and where results surface (HTML vs Admin).
- **Additional scanners** — New plugins following [`scanner/README.md`](../scanner/README.md) (manifest + Python class); candidates: more IaC rulesets, additional language linters, DAST breadth.
- **Asset / DB updates** — Extend **scanner assets** automation (vuln DBs, rule packs) and admin-triggered refresh flows.

## Platform

- **Notifications** — Email already configurable; optional webhooks or chat integrations for scan completion/failures.
- **Hardening** — Policy tuning, rate limits, and deployment guides for air-gapped or registry-restricted environments.

## How to contribute

- Open an issue with **use case** and **constraints** (self-hosted vs SaaS, auth model).
- For new tools: prefer **plugin manifests** and reuse the orchestrator pipeline documented in the scanner README.
