# Web Vulnerability Checks (ZAP)

SecuLite automatically checks your web application for common vulnerabilities.

## What is checked?
- XSS (Cross-Site Scripting)
- SQL Injection
- Insecure configurations
- Other OWASP Top 10 vulnerabilities

## How does the check work?
- Uses OWASP ZAP (Baseline Scan)
- The script runs `zap-baseline.py` and scans the target URL (e.g. http://localhost:8000)
- Results are saved as XML/HTML

## Example Command
```sh
zap-baseline.py -t "http://localhost:8000" -c zap/baseline.conf -r results/zap-report.xml
```

## Example Finding (XML excerpt)
```xml
<alertitem>
  <alert>Cross Site Scripting (Reflected)</alert>
  <riskcode>3</riskcode>
  <desc>Reflected XSS vulnerability found...</desc>
</alertitem>
```

## Results
- Reports in `results/zap-report.xml` (and optionally HTML)
- Summary in `results/security-summary.txt`

## Extension
- Adjust ZAP configuration in `zap/baseline.conf`
- For manual tests: enable ZAP WebUI (see README)

---
