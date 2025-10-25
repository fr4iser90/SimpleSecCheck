# SimpleSecCheck Rules Directory

This directory contains Semgrep rules for automated static code and AI security analysis.

| Rule File              | Purpose                        | Example Finding                | Linked Feature Doc                          |
|------------------------|--------------------------------|-------------------------------|---------------------------------------------|
| secrets.yml            | Detect hardcoded secrets        | `password = "..."`           | [Code Issues](/docs/features/code_issues.md) |
| code-bugs.yml          | Detect dangerous functions      | `eval(user_code)`             | [Code Issues](/docs/features/code_issues.md) |
| prompt-injection.yml   | Detect prompt injection risks   | `prompt = ... + ...`          | [AI/Prompt Injection](/docs/features/ai_prompt_injection.md) |

## How to Add/Modify Rules
- Add a new YAML file in this directory following Semgrep's [rule syntax](https://semgrep.dev/docs/writing-rules/).
- Reference new rules in the appropriate feature documentation.

## See Also
- [Documentation Hub](/docs/INDEX.md)
- [Feature Docs](/docs/features/)
- [Roles/Rules Index](/docs/roles/README.md) 