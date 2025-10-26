# Wapiti Integration – Phase 1: Foundation Setup

## Overview
Set up Wapiti CLI installation and configuration in the SimpleSecCheck system. This phase establishes the base infrastructure needed for Wapiti integration.

## Objectives
- [x] Install Wapiti CLI in Docker container
- [x] Create Wapiti configuration directory structure
- [x] Configure Wapiti scanning parameters
- [x] Verify Wapiti installation

## Deliverables
- [x] Wapiti CLI installed in Dockerfile
- [x] Configuration file: `wapiti/config.yaml`
- [x] Environment variables set up
- [x] Installation verified in container

## Dependencies
- Requires: Docker environment
- Blocks: Phase 2 - Core Implementation

## Estimated Time
2 hours

## Success Criteria
- [ ] Wapiti CLI installed and accessible
- [ ] Configuration directory created
- [ ] Configuration file with basic settings
- [ ] Wapiti command works in container

## Technical Details

### 1.1 Wapiti Installation
Update `Dockerfile` to install Wapiti CLI:
```dockerfile
# Install Wapiti CLI
RUN pip3 install wapiti3
```

### 1.2 Configuration Directory
Create directory structure:
```
wapiti/
├── config.yaml
```

### 1.3 Configuration File
Create `wapiti/config.yaml` with basic settings:
```yaml
scope:
  exclude:
    - "logout"
    - "error"
  limit: 100

filter:
  sql: true
  xss: true
  xxe: true
  ssti: true
  backup: true
  shellshock: true
  ssl: true
  ssrf: true
  open_redirect: true
```

### 1.4 Environment Variables
Add to `scripts/security-check.sh`:
```bash
export WAPITI_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/wapiti/config.yaml"
```

### 1.5 Verification
Test installation:
```bash
wapiti --version
```

## Notes
- Wapiti is a web application vulnerability scanner (DAST tool)
- It scans for SQL injection, XSS, XXE, and other web vulnerabilities
- Similar in purpose to OWASP ZAP but with different scanning approach
- Integration follows same pattern as ZAP and Nuclei

