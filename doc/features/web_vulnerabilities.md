# Web Vulnerability Checks (ZAP)

SecuLite prüft deine Webanwendung automatisiert auf typische Schwachstellen.

## Was wird geprüft?
- XSS (Cross-Site Scripting)
- SQL Injection
- Unsichere Konfigurationen
- Weitere OWASP Top 10 Schwachstellen

## Wie funktioniert der Check?
- Mit OWASP ZAP (Baseline Scan)
- Das Skript ruft `zap-baseline.py` auf und scannt die Ziel-URL (z.B. http://localhost:8000)
- Ergebnisse werden als XML/HTML gespeichert

## Beispiel-Aufruf
```sh
zap-baseline.py -t "http://localhost:8000" -c zap/baseline.conf -r results/zap-report.xml
```

## Beispiel-Finding (Ausschnitt aus XML)
```xml
<alertitem>
  <alert>Cross Site Scripting (Reflected)</alert>
  <riskcode>3</riskcode>
  <desc>Reflected XSS vulnerability found...</desc>
</alertitem>
```

## Ergebnisse
- Reports in `results/zap-report.xml` (und optional HTML)
- Zusammenfassung in `results/security-summary.txt`

## Erweiterung
- ZAP-Konfiguration in `zap/baseline.conf` anpassen
- Für manuelle Tests: ZAP WebUI aktivieren (siehe README)

---
