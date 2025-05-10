# SecuLite Project Plan (Autonomous Roadmap)

## Current State
- All-in-one security toolkit (ZAP, Semgrep, Trivy) is robust and CI/CD-ready.
- ZAP report persistence is solved with a fallback copy mechanism.
- Roles/rules are streamlined for autonomous, self-improving management.

## Immediate Next Steps
1. Standardize and cross-link all role/rule files.
2. Implement HTML summary report aggregating all scan results.
3. Add notification integration (Slack/Discord/email) for scan completion/failure.
4. Add configurable scan profiles (depth, speed, custom rules).
5. Add auto-fix suggestions for common issues.
6. Add a simple dashboard or status badge for CI/CD.

## Longer-Term Roadmap
- Compliance checks (OWASP Top 10, SLSA, etc.)
- Auto-update rules and tools
- Integration with external vulnerability databases
- Advanced reporting and analytics

## Self-Monitoring
- This plan will be updated after each major change.
- See also: STATUS.md for current status and recent changes.

# SecuLite Dashboard Enhancement Plan

## Goal
- Use the existing `security-summary.html` as the main dashboard.
- Add a "SCAN NOW" button to trigger a new scan.
- Show scan status and auto-refresh the summary when a scan completes.
- Keep everything simple, robust, and maintainable.

## Steps

### 1. Frontend (HTML/JS)
- Add a "SCAN NOW" button to `security-summary.html` (in the header).
- Update or extend `webui.js`:
    - On button click, send a request to trigger a scan.
    - Poll for scan status (e.g., via a `/status` endpoint or by checking file timestamps).
    - Auto-refresh the page or summary section when the scan is done.
    - Show a loading indicator/status during scan.

### 2. Backend (Scan Trigger)
- Provide a simple HTTP endpoint to trigger `security-check.sh` (Flask or minimal Python HTTP server).
- Provide a `/status` endpoint to report scan progress (e.g., "idle", "running", "done").
- Serve the latest `security-summary.html` and static assets.

### 3. Docker/Automation
- Update `docker-compose.yml` if needed to expose the dashboard and backend.
- Ensure the backend has permissions to run the scan script and write to `results/`.

### 4. Documentation
- Update `README.md` and `docs/` to describe the new dashboard workflow.
- Document how to extend/modify the dashboard and scan logic.

## Success Criteria
- User can open the dashboard, see the latest summary, and trigger a new scan with one click.
- Status is clearly shown during scan.
- Results auto-update when scan completes.
- All code and docs are clean, minimal, and extensible. 