# Extending & Contributing to SimpleSecCheck

## Adding New Rules
- **Semgrep:**
  - Place new YAML rule files in `/rules/`.
  - Use descriptive filenames (e.g., `injection-detection.yml`).
  - We particularly welcome contributions to:
    - `rules/api-security.yml` (for common API vulnerabilities like auth, CORS, rate limiting)
    - `rules/llm-ai-security.yml` (for LLM/AI specific issues like prompt injection, data leakage, insecure output handling)
    - `rules/secrets.yml` (for detecting inadvertently committed secrets)
    - `rules/code-bugs.yml` (for common coding errors leading to vulnerabilities)
    - `rules/prompt-injection.yml` (for general prompt injection patterns)
  - Document the rule purpose at the top of the file or within the rule's metadata.
- **ZAP:**
  - Add new config files to `/zap/`.
  - Follow ZAP documentation for custom scan policies.
- **Trivy:**
  - Add new config files to `/trivy/`.
  - Use Trivy's YAML format for custom policies.

## Integrating New Tools
- Add tool invocation logic to `scripts/security-check.sh`.
- Output results to both `results/security-summary.txt` and `results/security-summary.json`.
- Document the tool and its output in `README.md`.

## Modifying the Automation Script
- Edit `scripts/security-check.sh` for new steps or logic.
- Ensure error handling and logging are consistent.
- Test changes locally and in CI.

## Contributing via Pull Request
- Fork the repo and create a feature branch.
- Add or modify rules, scripts, or docs.
- Write clear commit messages and PR descriptions.
- Ensure all tests and checks pass before submitting.

## Directory Structure & Naming
- Place all rules/configs in their respective folders (`/rules/`, `/zap/`, `/trivy/`).
- Use lowercase, hyphen-separated filenames.
- Keep documentation up to date with all changes.

## Best Practices
- Test all new rules and scripts on a sample codebase.
- Prioritize actionable, low-noise rules.
- Follow open-source contribution etiquette. 