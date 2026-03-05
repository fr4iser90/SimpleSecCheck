# Tools Overview

SimpleSecCheck orchestrates multiple scanners inside Docker. This list is a **summary**; see scanner manifests for exact configuration.

## Code & Dependency Scanners

- Semgrep
- CodeQL
- Trivy
- OWASP Dependency Check
- Safety
- npm audit
- Snyk (optional token)
- ESLint
- Bandit
- Brakeman

## Secret Detection

- TruffleHog
- GitLeaks
- detect-secrets

## Infrastructure & Containers

- Checkov
- Terraform Security
- Anchore (Grype)
- Clair
- Docker Bench
- Kube-bench
- Kube-hunter

## Web Scanners

- OWASP ZAP
- Nuclei
- Nikto
- Wapiti
- Burp Suite (community)

## Mobile Checks

- React Native rules (Semgrep)
- Android Manifest checks
- iOS plist checks