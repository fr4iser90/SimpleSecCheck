# AI/Prompt Injection Checks

SecuLite prüft deinen Code auf Prompt Injection Schwachstellen in AI/LLM-Anwendungen.

## Was wird geprüft?
- Unsichere String-Konkatenation oder Interpolation bei Prompt-Konstruktion
- Direkte Nutzung von Benutzereingaben in Prompts

## Wie funktioniert der Check?
- Mit Semgrep und eigenen Regeln im Ordner `rules/`
- Die Regeln suchen nach typischen Mustern, z.B.:
  - `prompt = ... + ...` (Konkatenation)
  - (Optional) Interpolation wie `f"...{...}"` in Python

## Beispielregel (Python)
```yaml
rules:
  - id: prompt-injection-detect
    patterns:
      - pattern: 'prompt = ... + ...'
    message: 'Possible prompt injection: avoid direct user input in prompt construction.'
    languages: [python]
    severity: ERROR
```

## Beispiel-Finding
```python
user_input = input()
prompt = "You are a bot. " + user_input  # <-- Finding!
```

## Ergebnisse
- Findings stehen in `results/semgrep.txt` und `results/semgrep.json`

## Eigene Regeln ergänzen
- Lege eine neue YAML-Datei im Ordner `rules/` an
- Siehe [Semgrep Doku](https://semgrep.dev/docs/writing-rules/) für eigene Patterns

---
