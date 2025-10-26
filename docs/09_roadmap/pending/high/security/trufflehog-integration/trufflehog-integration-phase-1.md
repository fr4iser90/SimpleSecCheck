# TruffleHog Integration – Phase 1: Foundation Setup

## 📋 Phase Overview
- **Phase Number**: 1
- **Phase Name**: Foundation Setup
- **Estimated Time**: 2 hours
- **Status**: Planning
- **Progress**: 0%
- **Created**: 2025-10-26T00:18:41.000Z

## 🎯 Phase Objectives
Set up TruffleHog CLI installation in the Docker container and create configuration structure for secret detection.

## 📊 Detailed Tasks

### Task 1.1: TruffleHog CLI Installation (1 hour)
- [ ] **1.1.1** Add TruffleHog CLI installation to Dockerfile
- [ ] **1.1.2** Install TruffleHog using latest release from GitHub
- [ ] **1.1.3** Set up environment variables for TruffleHog
- [ ] **1.1.4** Test TruffleHog CLI availability in container

### Task 1.2: Configuration Setup (1 hour)
- [ ] **1.2.1** Create `trufflehog/` directory structure
- [ ] **1.2.2** Create TruffleHog config file: `trufflehog/config.yaml`
- [ ] **1.2.3** Configure detection rules and filters
- [ ] **1.2.4** Test configuration file loading

## 🔧 Technical Implementation Details

### Dockerfile Installation Pattern
```dockerfile
# Install TruffleHog CLI
RUN export TRUFFLEHOG_URL=$(wget -qO- https://api.github.com/repos/trufflesecurity/trufflehog/releases/latest | grep browser_download_url | grep trufflehog.*linux.*amd64.tar.gz | cut -d '"' -f 4) && \
    wget -O trufflehog.tar.gz $TRUFFLEHOG_URL && \
    tar -xvzf trufflehog.tar.gz -C /opt && \
    rm trufflehog.tar.gz && \
    ln -s /opt/trufflehog /usr/local/bin/trufflehog
```

### Environment Variables
```dockerfile
# Set TruffleHog environment variables
ENV TRUFFLEHOG_CONFIG_PATH=/SimpleSecCheck/trufflehog/config.yaml
```

### Configuration File Template
```yaml
# trufflehog/config.yaml
detectors:
  - aws
  - azure
  - github
  - gitlab
  - git_secret
  - private_key
  - slack
  - stripe
  - jwt
  - high_entropy_string
```

## 📦 Deliverables
- File: `Dockerfile` - TruffleHog installation added
- Directory: `trufflehog/` - Created
- File: `trufflehog/config.yaml` - Configuration file
- Environment Variables: TRUFFLEHOG_CONFIG_PATH

## 🔗 Dependencies
- Requires: None
- Blocks: Phase 2 (Core Implementation)

## ⏱️ Estimated Time
2 hours

## ✅ Success Criteria
- [ ] TruffleHog CLI installed and accessible in container
- [ ] Configuration directory created
- [ ] Configuration file created with proper settings
- [ ] Basic TruffleHog scan can be executed manually
- [ ] Docker build completes successfully with new installation

## 📝 Notes
- Follow existing patterns from CodeQL and Nuclei installations
- Use latest release from GitHub
- Ensure proper file permissions for TruffleHog binary
- Test configuration loading before proceeding to Phase 2

