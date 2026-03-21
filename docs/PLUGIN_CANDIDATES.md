# Possible additional scanners (candidates)

**No commitment** — ideas for future plugins (`scanner/plugins/<id>/`). See [TOOLS.md](TOOLS.md) for what is **already** integrated.

---

## What you already cover broadly

| Area | Already in the project (excerpt) |
|------|----------------------------------|
| **Images / containers / FS** | Trivy, Clair, Anchore |
| **IaC / cloud configs** | Checkov, Terraform plugin, Kube-bench, Kube-hunter |
| **Code / multi-language** | Semgrep, CodeQL, Bandit, Brakeman, ESLint, … |
| **Dependencies** | OWASP Dep. Check, Safety, npm audit, Snyk |
| **Secrets** | Gitleaks, TruffleHog, detect-secrets |
| **Web** | ZAP, Nuclei, Nikto, Wapiti, Burp |

On top of that, some “typical” candidates are **mostly redundant** — split below.

---

## Candidates that usually add *little* value (overlap)

You can **drop these from the wish list** or add them only if you *explicitly* want a second rule engine or a different report format:

| Candidate | Why it is often redundant |
|-----------|---------------------------|
| **Grype** (standalone) | Image/FS vuln scanning: **Trivy** + **Anchore** already cover this; Grype often targets the same niche. |
| **KICS** | IaC security: **Checkov** (+ similar targets) — a second large IaC engine means heavy maintenance, similar findings. |
| **Terrascan** | Same as KICS — **IaC overlap** with Checkov. |
| **kube-score / kube-linter** | K8s YAML: **Checkov** can cover Kubernetes — not a must-have. |
| **pip-audit** | Python deps: **Safety** (and optionally Trivy/OWASP) — same problem class. |
| **gosec** | Go SAST: **Semgrep** has Go rules — gosec only makes sense if you want “exactly gosec-style” findings. |
| **Hadolint** | Dockerfiles: **Trivy** can scan Dockerfiles — Hadolint is more “lint-style”; marginal extra value. |
| **OSV-Scanner** (standalone) | Trivy already pulls in OSV among sources; a standalone OSV CLI scan is often a **marginal gain**, not a new risk picture. |
| **Syft** (alone) | SBOM: **Trivy** can emit SBOM — Syft is mainly worth it if you **explicitly** want a Syft/CycloneDX workflow. |

---

## Candidates with a *distinct* profile (prefer keeping)

| Candidate | Why it is not fully replaced by “Trivy + Checkov + Semgrep” |
|-----------|-------------------------------------------------------------|
| **Conftest** | **OPA/Rego** on YAML/JSON — policy-as-code, different model than Checkov. |
| **MobSF** | **Mobile** (APK/IPA) goes much deeper than your current Android/iOS plugins. |
| **Prowler** (or similar) | **Cloud account compliance** (AWS/Azure/GCP) — not the same as image scanning. |
| **DefectDojo** | **Integration** (centralized findings), not a scanner — a separate workstream. |

---

## Short summary

- **Off the priority list** (overlap): typically **Grype, KICS, Terrascan, kube-linter/score, pip-audit, gosec, Hadolint, OSV-Scanner, Syft** — unless you have a **concrete** reason (compliance, “Syft-only SBOM”, a second opinion).
- **Keep as real “new directions”:** more likely **Conftest**, **MobSF**, **cloud CSPM** (Prowler-like), **DefectDojo integration**.

When planning a new plugin: name a **clear gap** (e.g. “OPA only” or “deep mobile scan”), then follow [`scanner/README.md`](../scanner/README.md).
