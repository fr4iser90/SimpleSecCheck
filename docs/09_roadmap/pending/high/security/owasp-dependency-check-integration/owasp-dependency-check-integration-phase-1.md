# OWASP Dependency Check Integration – Phase 1: Foundation Setup

## Overview
Set up OWASP Dependency Check CLI installation and basic configuration in the SimpleSecCheck Docker environment.

## Objectives
- [ ] Install OWASP Dependency Check CLI in Dockerfile
- [ ] Create configuration directory structure
- [ ] Set up basic configuration files
- [ ] Test installation and basic functionality

## Deliverables
- File: `Dockerfile` - Updated with OWASP Dependency Check installation
- Directory: `owasp-dependency-check/` - Configuration directory
- File: `owasp-dependency-check/config.yaml` - Basic configuration
- File: `owasp-dependency-check/reports/` - Reports directory
- Test: Basic CLI functionality verification

## Dependencies
- Requires: Existing Docker environment
- Blocks: Phase 2 start

## Estimated Time
2 hours

## Detailed Tasks

### Task 1.1: Dockerfile Updates (1 hour)
- [ ] **1.1.1** Add OWASP Dependency Check CLI installation to Dockerfile
- [ ] **1.1.2** Set up environment variables for OWASP Dependency Check
- [ ] **1.1.3** Create necessary directories in Docker image
- [ ] **1.1.4** Test Docker build with new installation

### Task 1.2: Configuration Setup (1 hour)
- [ ] **1.2.1** Create `owasp-dependency-check/` directory
- [ ] **1.2.2** Create `owasp-dependency-check/config.yaml` configuration file
- [ ] **1.2.3** Set up basic scan parameters and output formats
- [ ] **1.2.4** Create reports directory structure

## Technical Implementation Details

### Dockerfile Updates
```dockerfile
# Install OWASP Dependency Check CLI
RUN wget https://github.com/jeremylong/DependencyCheck/releases/latest/download/dependency-check-8.4.0-release.zip && \
    unzip dependency-check-8.4.0-release.zip -d /opt && \
    rm dependency-check-8.4.0-release.zip && \
    ln -s /opt/dependency-check/bin/dependency-check.sh /usr/local/bin/dependency-check

# Set OWASP Dependency Check environment variables
ENV OWASP_DEPENDENCY_CHECK_HOME=/opt/dependency-check
ENV OWASP_DEPENDENCY_CHECK_CONFIG_PATH=/SimpleSecCheck/owasp-dependency-check/config.yaml
```

### Configuration File Structure
```yaml
# owasp-dependency-check/config.yaml
scan:
  formats: ["JSON", "HTML"]
  failOnCVSS: 7
  enableRetired: false
  enableExperimental: false
  
output:
  json: true
  html: true
  xml: false
  
database:
  driver: "org.h2.Driver"
  connectionString: "jdbc:h2:file:${owasp.dependency.check.data}/dc;MV_STORE=FALSE;LOCK_TIMEOUT=25000"
```

## Success Criteria
- [ ] OWASP Dependency Check CLI installs successfully in Docker
- [ ] Configuration directory and files are created
- [ ] Basic CLI commands execute without errors
- [ ] Environment variables are properly set
- [ ] Docker build completes successfully

## Testing Checklist
- [ ] Run `docker build` to verify installation
- [ ] Execute `dependency-check --version` to verify CLI
- [ ] Test basic scan command with sample project
- [ ] Verify configuration file is readable
- [ ] Check directory permissions and structure
