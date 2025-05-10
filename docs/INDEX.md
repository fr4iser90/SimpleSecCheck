# SecuLite Documentation Hub

Welcome to the central documentation hub for SecuLite. Here you will find everything you need to understand, extend, and monitor the project.

---

## 📚 Documentation Structure

```
docs/
├── INDEX.md                # This file (documentation hub)
├── EXTENDING.md            # How to extend/contribute
├── features/               # Feature-specific docs
│   ├── ai_prompt_injection.md
│   ├── code_issues.md
│   ├── dependency_container.md
│   └── web_vulnerabilities.md
├── plan/                   # Planning, roadmap, and tasks
│   ├── PLAN.md
│   ├── STATUS.md
│   ├── detailed_plan.md
│   ├── task_1.md ... task_7.md
└── roles/                  # Roles and rules
    └── README.md
```

---

## 🏗️ Architecture & Design Pattern

- **Architecture:** Modular, extensible, and CI/CD-ready security toolkit.
- **Design Pattern:**
  - Central automation script (`security-check.sh`) orchestrates all tools.
  - Each tool (ZAP, Semgrep, Trivy) is modular and can be extended via config/rules.
  - Results are unified and aggregated for easy reporting and CI integration.
- **Folder Structure:**
  - All documentation is in `docs/` for easy navigation and onboarding.
  - All rules/configs are in their respective folders (`rules/`, `zap/`, `trivy/`).

---

## 🛠️ Tech Stack
- **Shell (Bash):** Automation scripting
- **OWASP ZAP:** Web vulnerability scanning
- **Semgrep:** Static code analysis
- **Trivy:** Dependency/container scanning
- **YAML:** For rules/configs
- **GitHub Actions:** CI/CD integration

---

## 📋 Planning & Roadmap
- [Current Plan & Roadmap](plan/PLAN.md)
- [Current Status & Progress](plan/STATUS.md)
- [Detailed Plan & Atomic Tasks](plan/detailed_plan.md)
  - [Phase 1 Tasks](plan/task_1.md)
  - [Phase 2 Tasks](plan/task_2.md)
  - [Phase 3 Tasks](plan/task_3md)
  - [Phase 4 Tasks](plan/task_4.md)
  - [Phase 5 Tasks](plan/task_5.md)
  - [Phase 6 Tasks](plan/task_6.md)
  - [Phase 7 Tasks](plan/task_7.md)

---

## 🛡️ Features & Checks
- [AI/Prompt Injection](features/ai_prompt_injection.md)
- [Code Issues](features/code_issues.md)
- [Dependency & Container](features/dependency_container.md)
- [Web Vulnerabilities](features/web_vulnerabilities.md)

---

## 🧩 Extending & Contributing
- [How to Extend/Contribute](EXTENDING.md)

---

## 🧑‍💻 Roles & Rules
- [Roles/Rules Index](roles/README.md)
- [Rules Directory & Rule Docs](../rules/README.md)

---

## 🗺️ How to Navigate This Project
- All planning and status: `docs/plan/`
- All features: `docs/features/`
- All extension/contribution: `docs/EXTENDING.md`
- All roles/rules: `docs/roles/`

---

## 📖 Documentation Role

A dedicated documentation role (`role_documentation.mdc`) ensures that all docs are up-to-date, cross-linked, and state-of-the-art. This role is responsible for:
- Maintaining this index and all doc cross-links
- Ensuring onboarding, architecture, and tech stack are always clear
- Proactively improving documentation as the project evolves 

---

## 📂 Absolute Paths (for reference)

- /docs/INDEX.md
- /docs/EXTENDING.md
- /docs/features/ai_prompt_injection.md
- /docs/features/code_issues.md
- /docs/features/dependency_container.md
- /docs/features/web_vulnerabilities.md
- /docs/plan/PLAN.md
- /docs/plan/STATUS.md
- /docs/plan/detailed_plan.md
- /docs/plan/task_1.md
- /docs/plan/task_2.md
- /docs/plan/task_3md
- /docs/plan/task_4.md
- /docs/plan/task_5.md
- /docs/plan/task_6.md
- /docs/plan/task_7.md
- /docs/roles/README.md
- /rules/README.md 