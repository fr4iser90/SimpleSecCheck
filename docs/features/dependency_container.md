# Dependency & Container Checks (Trivy)

SecuLite checks your dependencies and containers for known vulnerabilities.

## What is checked?
- Open source libraries (Python, JS, etc.)
- Operating system packages
- Container images

## How does the check work?
- Uses Trivy and configuration in `trivy/config.yaml`
- The script runs `trivy fs` and scans the target directory

## Example Command
```sh
trivy fs --config trivy/config.yaml /target --format json > results/trivy.json
```

## Example Finding (JSON excerpt)
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

## Results
- Findings are in `results/trivy.txt` and `results/trivy.json`

## Extension
- Adjust Trivy configuration in `trivy/config.yaml`
- See [Trivy Docs](https://aquasecurity.github.io/trivy/latest/docs/) for more options

---
