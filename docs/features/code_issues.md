# Code Issues Checks (Semgrep)

SimpleSecCheck checks your code for common bugs, unsafe patterns, and hardcoded secrets.

## What is checked?
- Dangerous functions (e.g. eval, exec)
- Hardcoded secrets (e.g. passwords, API keys)
- Code bugs and unsafe patterns

## How does the check work?
- Uses Semgrep and custom rules in the `rules/` folder
- Rules are designed for Python, JavaScript, TypeScript

## Example Rule (Dangerous Function)
```yaml
rules:
  - id: dangerous-function-detect
    patterns:
      - pattern: 'eval(...)'
      - pattern: 'exec(...)'
    message: 'Dangerous function usage detected (eval/exec).'
    languages: [python, javascript, typescript]
    severity: WARNING
```

## Example Finding
```python
user_code = input()
eval(user_code)  # <-- Finding!
```

## Results
- Findings are in `results/semgrep.txt` and `results/semgrep.json`

## Add your own rules
- Create a new YAML file in the `rules/` folder
- See [Semgrep Docs](https://semgrep.dev/docs/writing-rules/) for custom patterns

---
