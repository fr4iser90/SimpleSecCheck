# GitLeaks Integration – Phase 1: Foundation Setup

## Overview
Install and configure GitLeaks CLI in the Docker container, and create the necessary configuration files for secret detection scanning.

## Objectives
- [ ] Install GitLeaks CLI in Dockerfile using latest release
- [ ] Create `gitleaks/` configuration directory
- [ ] Create `gitleaks/config.yaml` with detection rules
- [ ] Set up environment variables for GitLeaks in security-check.sh

## Deliverables
- File: `Dockerfile` - Updated with GitLeaks installation
- File: `gitleaks/config.yaml` - GitLeaks configuration with detection rules
- File: `scripts/security-check.sh` - Updated with GITLEAKS_CONFIG_PATH environment variable
- Directory: `gitleaks/` - New configuration directory

## Implementation Steps

### Step 1: Dockerfile Installation
Add GitLeaks CLI installation to `Dockerfile` after TruffleHog installation:

```bash
# Install GitLeaks CLI
RUN export GITLEAKS_URL=$(wget -qO- https://api.github.com/repos/gitleaks/gitleaks/releases/latest | grep browser_download_url | grep gitleaks.*linux.*amd64.tar.gz | cut -d '"' -f 4) && \
    wget -O gitleaks.tar.gz $GITLEAKS_URL && \
    tar -xvzf gitleaks.tar.gz -C /opt && \
    rm gitleaks.tar.gz && \
    ln -s /opt/gitleaks /usr/local/bin/gitleaks
```

### Step 2: Create Configuration Directory and File
Create `gitleaks/config.yaml` with secret detection rules:

```yaml
# GitLeaks Configuration for SimpleSecCheck

# Global settings
[global]
  numWorkers = 10
  verbose = false
  verboseResults = false

# Rules for different secret types
[[rules]]
  description = "Generic API Key"
  id = "generic-api-key"
  regex = '''(?i)(api[_-]?key|apikey)\s*[=:]\s*['"]?([a-z0-9]{20,})['"]?'''
  
[[rules]]
  description = "AWS Access Key"
  id = "aws-access-key"
  regex = '''AKIA[0-9A-Z]{16}'''

[[rules]]
  description = "GitHub Token"
  id = "github-token"
  regex = '''ghp_[0-9a-zA-Z]{36}'''

[[rules]]
  description = "Private Key"
  id = "private-key"
  regex = '''-----BEGIN\s+(?:RSA|EC|DSA)\s+PRIVATE\s+KEY-----'''

[[rules]]
  description = "JWT Token"
  id = "jwt-token"
  regex = '''eyJ[A-Za-z0-9-_=]+\.eyJ[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*'''

[[rules]]
  description = "Database Password"
  id = "database-password"
  regex = '''(?i)(password|pwd|pass)[\s=:]+['"]?([a-zA-Z0-9!@#$%^&*]{8,})['"]?'''

[[rules]]
  description = "Slack Token"
  id = "slack-token"
  regex = '''xox[baprs]-([0-9a-zA-Z-]{10,48})'''

[[rules]]
  description = "Stripe API Key"
  id = "stripe-key"
  regex = '''sk_live_[0-9a-zA-Z]{24,}'''

[[rules]]
  description = "Google API Key"
  id = "google-api-key"
  regex = '''AIza[0-9A-Za-z-_]{35}'''

[[rules]]
  description = "Mailgun API Key"
  id = "mailgun-key"
  regex = '''key-[0-9a-zA-Z]{32}'''
```

### Step 3: Update security-check.sh
Add GITLEAKS_CONFIG_PATH environment variable to the tool-specific configurations section:

```bash
export GITLEAKS_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/gitleaks/config.yaml"
```

## Dependencies
- Requires: Dockerfile exists, security-check.sh exists
- Blocks: Phase 2 - Core Implementation

## Estimated Time
2 hours

## Success Criteria
- [ ] GitLeaks CLI installs successfully in Docker container
- [ ] `gitleaks/config.yaml` contains proper detection rules
- [ ] Environment variable is exported in security-check.sh
- [ ] Docker build completes without errors
- [ ] `gitleaks --version` command works in container

## Testing
- Run Docker build to verify GitLeaks installation
- Execute `gitleaks --version` inside container
- Verify configuration file is copied correctly
- Check that environment variable is exported

