# Third-Party Licenses

SimpleSecCheck orchestrates various third-party security tools. Each tool is distributed under its own license. This document provides an overview of the licenses used by the integrated tools.

## License Summary

SimpleSecCheck uses tools with the following license types:

- **MIT License** - Permissive, compatible with MIT
- **Apache 2.0** - Permissive, compatible with MIT
- **GPL v2/v3** - Copyleft (tools executed as separate processes, no code integration)
- **LGPL** - Lesser GPL (tools executed as separate processes, no code integration)
- **Proprietary/Commercial** - Some tools have commercial licensing options

## Important Legal Note

**SimpleSecCheck acts as an orchestrator** that calls external CLI tools via command-line interfaces. No third-party source code is directly integrated, statically linked, or bundled into the SimpleSecCheck codebase. All tools are executed as separate processes within Docker containers, maintaining clear separation and license boundaries.

This means:
- ✅ SimpleSecCheck's MIT license applies to the orchestrator code
- ✅ Each tool's license applies to the tool itself
- ✅ No license "infection" occurs because tools are not linked or integrated
- ✅ Users must comply with each tool's license when using SimpleSecCheck

## Integrated Tools and Their Licenses

### Static Code Analysis

| Tool | License | Notes |
|------|---------|-------|
| **Semgrep** | LGPL 2.1 | Executed as CLI tool |
| **CodeQL** | Proprietary (GitHub) | Free for open-source projects |
| **ESLint** | MIT | Executed as CLI tool |
| **Brakeman** | MIT | Executed as CLI tool |
| **Bandit** | Apache 2.0 | Executed as CLI tool |

### Dependency & Container Scanning

| Tool | License | Notes |
|------|---------|-------|
| **Trivy** | Apache 2.0 | Executed as CLI tool |
| **Clair** | Apache 2.0 | Executed as CLI tool |
| **Anchore Grype** | Apache 2.0 | Executed as CLI tool |
| **OWASP Dependency Check** | Apache 2.0 | Executed as CLI tool |
| **Safety** | MIT | Executed as CLI tool |
| **Snyk** | Apache 2.0 | Executed as CLI tool (requires account) |
| **npm audit** | ISC (npm) | Part of Node.js ecosystem |

### Infrastructure as Code

| Tool | License | Notes |
|------|---------|-------|
| **Checkov** | Apache 2.0 | Executed as CLI tool |
| **Terraform Security** | MPL 2.0 | Executed as CLI tool |

### Secret Detection

| Tool | License | Notes |
|------|---------|-------|
| **TruffleHog** | AGPL 3.0 | Executed as CLI tool |
| **GitLeaks** | MIT | Executed as CLI tool |
| **Detect-secrets** | Apache 2.0 | Executed as CLI tool |

### Code Quality

| Tool | License | Notes |
|------|---------|-------|
| **SonarQube Scanner** | LGPL 3.0 | Executed as CLI tool |

### Web Application Security

| Tool | License | Notes |
|------|---------|-------|
| **OWASP ZAP** | Apache 2.0 | Executed as CLI tool |
| **Nuclei** | MIT | Executed as CLI tool |
| **Wapiti** | GPL 2.0 | Executed as CLI tool |
| **Nikto** | GPL 2.0 | Executed as CLI tool |
| **Burp Suite** | Proprietary | Community Edition (free) |

### Container & Kubernetes Security

| Tool | License | Notes |
|------|---------|-------|
| **Kube-hunter** | GPL 2.0 | Executed as CLI tool |
| **Kube-bench** | Apache 2.0 | Executed as CLI tool |
| **Docker Bench** | Apache 2.0 | Executed as CLI tool |

## GPL-Licensed Tools

The following tools are licensed under GPL (GNU General Public License):

- **Wapiti** (GPL 2.0)
- **Nikto** (GPL 2.0)
- **Kube-hunter** (GPL 2.0)

**Important:** These tools are executed as separate CLI processes. SimpleSecCheck does not:
- Statically link GPL code
- Integrate GPL source code
- Modify and redistribute GPL code

The GPL license only applies to the tools themselves, not to SimpleSecCheck, because the tools are executed as separate processes (similar to how you might use `grep` or `find` in a script).

## User Responsibilities

When using SimpleSecCheck, you are responsible for:

1. **Compliance with tool licenses** - Ensure your use of each tool complies with its license
2. **Commercial use** - Some tools may have restrictions on commercial use
3. **API terms** - Tools that require API keys (e.g., Snyk, NVD) have their own terms of service
4. **Rate limiting** - Respect rate limits and terms of service for external APIs

## Getting License Information

To view the full license text for any tool:

1. Visit the tool's official repository (usually on GitHub)
2. Check the `LICENSE` or `LICENSE.txt` file
3. Review the tool's documentation

## Questions?

If you have questions about licensing:
- Check each tool's official documentation
- Review the tool's GitHub repository
- Consult with legal counsel for commercial use cases

---

**Last Updated:** 2025-01-28  
**SimpleSecCheck License:** MIT  
**SimpleSecCheck Copyright:** © 2025 Patrick B.
