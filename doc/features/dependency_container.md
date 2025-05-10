# Dependency & Container Checks (Trivy)

SecuLite prüft deine Dependencies und Container auf bekannte Schwachstellen.

## Was wird geprüft?
- Open Source Libraries (Python, JS, etc.)
- Betriebssystem-Pakete
- Container-Images

## Wie funktioniert der Check?
- Mit Trivy und Konfiguration in `trivy/config.yaml`
- Das Skript ruft `trivy fs` auf und scannt das Zielverzeichnis

## Beispiel-Aufruf
```sh
trivy fs --config trivy/config.yaml /target --format json > results/trivy.json
```

## Beispiel-Finding (Ausschnitt aus JSON)
```json
{
  "Vulnerabilities": [
    {
      "VulnerabilityID": "CVE-2022-12345",
      "PkgName": "requests",
      "Severity": "HIGH",
      "Title": "Some vulnerability..."
    }
  ]
}
```

## Ergebnisse
- Findings stehen in `results/trivy.txt` und `results/trivy.json`

## Erweiterung
- Trivy-Konfiguration in `trivy/config.yaml` anpassen
- Siehe [Trivy Doku](https://aquasecurity.github.io/trivy/latest/docs/) für weitere Optionen

---
