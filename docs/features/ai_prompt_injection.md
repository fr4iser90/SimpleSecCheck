# AI/Prompt Injection Checks

SecuLite checks your code for prompt injection vulnerabilities in AI/LLM applications.

## What is checked?
- Unsafe string concatenation or interpolation in prompt construction
- Direct use of user input in prompts

## How does the check work?
- Uses Semgrep and custom rules in the `rules/` folder
- Rules look for typical patterns, e.g.:
  - `prompt = ... + ...` (concatenation)
  - (Optional) Interpolation like `f"...{...}"` in Python

## Example Rule (Python)
```yaml
rules:
  - id: prompt-injection-detect
    patterns:
      - pattern: 'prompt = ... + ...'
    message: 'Possible prompt injection: avoid direct user input in prompt construction.'
    languages: [python]
    severity: ERROR
```

## Example Finding
```python
user_input = input()
prompt = "You are a bot. " + user_input  # <-- Finding!
```

## Results
- Findings are in `results/semgrep.txt` and `results/semgrep.json`

## Add your own rules
- Create a new YAML file in the `rules/` folder
- See [Semgrep Docs](https://semgrep.dev/docs/writing-rules/) for custom patterns

---
