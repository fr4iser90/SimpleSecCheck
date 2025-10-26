# Nikto Integration – Phase 1: Foundation Setup

## Overview
Set up Nikto CLI installation and configuration in the SimpleSecCheck system. This phase establishes the base infrastructure needed for Nikto integration.

## Objectives
- [ ] Install Nikto CLI in Docker container
- [ ] Create Nikto configuration directory structure
- [ ] Configure Nikto scanning parameters
- [ ] Verify Nikto installation

## Deliverables
- [ ] Nikto CLI installed in Dockerfile
- [ ] Configuration file: `nikto/config.yaml`
- [ ] Environment variables set up
- [ ] Installation verified in container

## Dependencies
- Requires: Docker environment
- Blocks: Phase 2 - Core Implementation

## Estimated Time
2 hours

## Success Criteria
- [ ] Nikto CLI installed and accessible
- [ ] Configuration directory created
- [ ] Configuration file with basic settings
- [ ] Nikto command works in container

## Technical Details

### 1.1 Nikto Installation
Update `Dockerfile` to install Nikto CLI:
```dockerfile
# Install Nikto (needs Perl and Perl modules)
RUN apt-get update && apt-get install -y perl libwww-perl liblwp-protocol-https-perl \
    && wget https://github.com/sullo/nikto/archive/master.zip \
    && unzip master.zip \
    && mv nikto-master /opt/nikto \
    && ln -s /opt/nikto/program/nikto.pl /usr/local/bin/nikto \
    && rm master.zip
```

### 1.2 Configuration Directory
Create directory structure:
```
nikto/
├── config.yaml
```

### 1.3 Configuration File
Create `nikto/config.yaml` with basic settings:
```yaml
# Nikto Configuration for SimpleSecCheck
# Purpose: Configure Nikto for web server security scanning

# Scan settings
format: json
evasion: 1
# User agent
user-agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36
# SSL/HTTPS
ssl: true
# Display settings
verbose: true
display: 1
# Database update
updatedb: true
```

### 1.4 Environment Variables
Add to `scripts/security-check.sh`:
```bash
export NIKTO_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/nikto/config.yaml"
```

### 1.5 Verification
Test installation:
```bash
nikto -Version
```

## Notes
- Nikto is a web server scanner that tests for dangerous files, outdated servers, and misconfigurations
- It checks for common web server vulnerabilities and dangerous files/programs
- Similar in purpose to Wapiti and Nuclei but focused on server-level scans
- Integration follows same pattern as other DAST tools (ZAP, Nuclei, Wapiti)

## Implementation Steps
1. Add Nikto installation to Dockerfile
2. Create nikto/ directory with config.yaml
3. Add environment variable to security-check.sh
4. Test Nikto installation in container
5. Verify configuration file is read correctly

