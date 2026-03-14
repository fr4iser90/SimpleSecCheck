# SimpleSecCheck Rules Directory

This directory contains Semgrep rules for automated static code and AI security analysis.

| Rule File                    | Purpose                          | Example Finding                | Linked Feature Doc                          |
|------------------------------|----------------------------------|-------------------------------|---------------------------------------------|
| secrets.yml                  | Detect hardcoded secrets          | `password = "..."`           | [Code Issues](/docs/features/code_issues.md) |
| code-bugs.yml                | Detect dangerous functions        | `eval(user_code)`             | [Code Issues](/docs/features/code_issues.md) |
| prompt-injection.yml         | Detect prompt injection risks     | `prompt = ... + ...`          | [AI/Prompt Injection](/docs/features/ai_prompt_injection.md) |
| api-security.yml             | Detect API security issues        | Missing authentication         | [API Security](/docs/features/api_security.md) |
| llm-ai-security.yml           | Detect LLM/AI security issues     | Exposed API keys              | [AI Security](/docs/features/ai_security.md) |
| react-native-security.yml    | Detect React Native security issues | Insecure AsyncStorage         | [Mobile Security](/docs/features/mobile_security.md) |

## How to Add/Modify Rules
- Add a new YAML file in this directory following Semgrep's [rule syntax](https://semgrep.dev/docs/writing-rules/).
- Reference new rules in the appropriate feature documentation.

## React Native Support
React Native-specific security rules are now available in `react-native-security.yml`. These rules detect common mobile app security vulnerabilities including:
- Insecure storage with AsyncStorage
- WebView security issues
- Deep linking vulnerabilities
- Insecure network requests
- Sensitive data logging
- And many more mobile-specific security concerns

## See Also
- [Documentation Hub](/docs/INDEX.md)
- [Feature Docs](/docs/features/)
- [Roles/Rules Index](/docs/roles/README.md) 