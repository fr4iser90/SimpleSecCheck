# Code Issues Checks (Semgrep)

SecuLite prüft deinen Code auf typische Fehler, unsichere Patterns und Hardcoded Secrets.

## Was wird geprüft?
- Unsichere Funktionen (z.B. eval, exec)
- Hardcoded Secrets (z.B. Passwörter, API-Keys)
- Code-Bugs und unsichere Patterns

## Wie funktioniert der Check?
- Mit Semgrep und eigenen Regeln im Ordner `rules/`
- Die Regeln sind für Python, JavaScript, TypeScript ausgelegt

## Beispielregel (Dangerous Function)
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

## Beispiel-Finding
```python
user_code = input()
eval(user_code)  # <-- Finding!
```

## Ergebnisse
- Findings stehen in `results/semgrep.txt` und `results/semgrep.json`

## Eigene Regeln ergänzen
- Lege eine neue YAML-Datei im Ordner `rules/` an
- Siehe [Semgrep Doku](https://semgrep.dev/docs/writing-rules/) für eigene Patterns

---
