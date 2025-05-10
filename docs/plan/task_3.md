# Task List: Phase 3 – Script Development

- [x] Design workflow for scripts/security-check.sh (input, steps, output)
- [x] Write function to run ZAP baseline scan and parse output
- [x] Write function to run Semgrep with all rules and parse output
- [x] Write function to run Trivy and parse output
- [x] Aggregate all outputs into results/security-summary.txt and results/security-summary.json
- [x] Prioritize and highlight critical issues in output
- [x] Add error handling: exit nonzero on error, log to logs/security-check.log
- [x] Add logging for each step
- [x] Ensure script works both locally and in CI
- [x] Test script on sample codebase
- [x] Refine for usability and extensibility
