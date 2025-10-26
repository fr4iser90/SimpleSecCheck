# Detect-secrets Integration – Phase 1: Foundation Setup

## Overview
Set up the basic foundation for detect-secrets integration by installing the Python package, creating the configuration directory, and setting up the initial configuration file with detection rules.

## Objectives
- [ ] Install detect-secrets Python package in Dockerfile
- [ ] Create detect-secrets configuration directory: `detect-secrets/`
- [ ] Add detect-secrets config file: `detect-secrets/config.yaml`
- [ ] Set up secret detection rules and filters
- [ ] Add environment variables for detect-secrets configuration
- [ ] Test detect-secrets installation in Docker container

## Deliverables
- File: `Dockerfile` - Added detect-secrets installation (after line 56)
- Environment Variable: `DETECT_SECRETS_CONFIG_PATH` - Added in Dockerfile
- Directory: `detect-secrets/` - Created in project root
- File: `detect-secrets/config.yaml` - Detect-secrets configuration with rules and filters

## Dependencies
- Requires: None (this is the first phase)
- Blocks: Phase 2 (Core Implementation)

## Estimated Time
2 hours

## Success Criteria
- [ ] Detect-secrets package successfully installs via pip3 in Dockerfile
- [ ] `detect-secrets/` directory is created in project root
- [ ] `detect-secrets/config.yaml` file exists with proper configuration
- [ ] Environment variable `DETECT_SECRETS_CONFIG_PATH` is set in Dockerfile
- [ ] Docker build completes without errors
- [ ] Detect-secrets CLI is accessible in container via `detect-secrets` command
- [ ] Detect-secrets can run with basic scan on test file

## Implementation Details

### 1. Dockerfile Updates
Location: After Safety installation (line 56)

Add detect-secrets installation:
```dockerfile
# Install Detect-secrets (Python secret detection tool)
RUN pip3 install detect-secrets
```

Add environment variable after other ENV declarations (around line 175):
```dockerfile
# Set Detect-secrets environment variables
ENV DETECT_SECRETS_CONFIG_PATH=/SimpleSecCheck/detect-secrets/config.yaml
```

### 2. Create Configuration Directory
- Create `detect-secrets/` directory in project root
- Follow existing pattern from `gitleaks/`, `trufflehog/`, etc.

### 3. Create Configuration File
File: `detect-secrets/config.yaml`

Content structure:
```yaml
version: 0.2.0
baseline:
  path: .secrets.baseline
  # This will be auto-generated on first run
plugins:
  # High entropy string detection
  - name: HexHighEntropyString
    path: detect_secrets.plugins.high_entropy
    limit: 4.5
  - name: Base64HighEntropyString
    path: detect_secrets.plugins.high_entropy
    limit: 4.5
  # AWS detection
  - name: AWSKeyDetector
    path: detect_secrets.plugins.aws
    verify: false  # Disable verification for speed
  - name: AWSSecretKeyDetector
    path: detect_secrets.plugins.aws_secret
  # GitHub token detection
  - name: GitHubTokenDetector
    path: detect_secrets.plugins.github
  # Slack token detection
  - name: SlackDetector
    path: detect_secrets.plugins.slack
  # Generic password detection
  - name: PrivateKeyDetector
    path: detect_secrets.plugins.private_key
  # API key patterns
  - name: ArtifactoryDetector
    path: detect_secrets.plugins.artifactory
  - name: DiscordDetector
    path: detect_secrets.plugins.discord
  - name: StripeDetector
    path: detect_secrets.plugins.stripe
  - name: TwilioKeyDetector
    path: detect_secrets.plugins.twilio
  # Database credentials
  - name: PostgreSQLPasswordDetector
    path: detect_secrets.plugins.postgres
  - name: MySQLDetector
    path: detect_secrets.plugins.mysql
  # Certificate detection
  - name: PEMKeyDetector
    path: detect_secrets.plugins.pem
exclude_regexes:
  - '(?i)(comment|example|test|sample|demo|placeholder)'
  - '\.baseline$'
  - '\.lock$'
  - 'node_modules'
  - '\.git'
  - '\.venv'
  - '\.cache'
```

### 4. Testing
After Docker build, verify installation:
```bash
docker run --rm simpleseccheck detect-secrets --version
docker run --rm simpleseccheck detect-secrets scan --help
```

## Notes
- Detect-secrets is a Python package, installed via pip3
- Configuration follows plugin-based architecture
- Exclude patterns help reduce false positives
- Baseline file will be generated on first scan
- Follows existing GitLeaks/TruffleHog integration pattern

## Validation
Run these commands after implementation:
1. `docker build -t simpleseccheck .` - Should complete successfully
2. `docker run --rm simpleseccheck detect-secrets --version` - Should print version
3. `docker run --rm simpleseccheck ls /SimpleSecCheck/detect-secrets/` - Should show config.yaml
4. `docker run --rm simpleseccheck cat /SimpleSecCheck/detect-secrets/config.yaml` - Should show configuration

