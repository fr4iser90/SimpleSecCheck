# SonarQube Integration – Phase 1: Foundation Setup

## Overview
Set up SonarQube Scanner CLI installation and basic configuration for code quality and security scanning.

## Objectives
- [ ] Install SonarQube Scanner CLI in Docker container
- [ ] Create SonarQube configuration directory and files
- [ ] Set up SonarQube environment variables
- [ ] Test SonarQube Scanner CLI installation and basic functionality

## Deliverables
- File: `Dockerfile` - Updated with SonarQube Scanner CLI installation
- File: `sonarqube/config.yaml` - SonarQube configuration file
- File: `sonarqube/project-template.properties` - SonarQube project template
- Environment: SonarQube Scanner CLI functional in container

## Dependencies
- Requires: Docker container setup
- Blocks: Phase 2 - Core Implementation

## Estimated Time
2 hours

## Success Criteria
- [ ] SonarQube Scanner CLI successfully installed in Docker container
- [ ] SonarQube configuration directory created
- [ ] SonarQube environment variables set
- [ ] SonarQube Scanner CLI responds to basic commands
- [ ] SonarQube can analyze sample code

## Technical Details

### Dockerfile Updates
```dockerfile
# Install SonarQube Scanner CLI
RUN export SONAR_SCANNER_URL=$(wget -qO- https://api.github.com/repos/SonarSource/sonar-scanner-cli/releases/latest | grep browser_download_url | grep sonar-scanner-cli.*linux-x86_64.tar.gz | cut -d '"' -f 4) && \
    wget -O sonar-scanner.tar.gz $SONAR_SCANNER_URL && \
    tar -xvzf sonar-scanner.tar.gz -C /opt && \
    rm sonar-scanner.tar.gz && \
    ln -s /opt/sonar-scanner-*/bin/sonar-scanner /usr/local/bin/sonar-scanner

# Set SonarQube environment variables
ENV SONARQUBE_CONFIG_PATH=/SimpleSecCheck/sonarqube/config.yaml
ENV SONARQUBE_SCANNER_HOME=/opt/sonar-scanner
```

### SonarQube Configuration
```yaml
# sonarqube/config.yaml
project:
  name: SimpleSecCheck-Analysis
  version: 1.0.0

analysis:
  source_dir: "/target"
  languages:
    auto_detect: true
  
  quality_gate:
    pass_threshold: "default"
    severity_levels:
      - blocker
      - critical
      - major

output:
  formats:
    - json
    - text
  detailed: true
  code_snippets: true

exclusions:
  patterns:
    - "*/test*"
    - "*/tests/*"
    - "*/__pycache__/*"
    - "*/node_modules/*"
    - "*/venv/*"

integration:
  exit_on_issues: false
  include_in_html: true
```

### Environment Variables
```bash
export SONARQUBE_CONFIG_PATH="/SimpleSecCheck/sonarqube/config.yaml"
export SONARQUBE_SCANNER_HOME="/opt/sonar-scanner"
export SONARQUBE_OUTPUT_DIR="/SimpleSecCheck/results"
```

### Testing Commands
```bash
# Test SonarQube Scanner installation
sonar-scanner --version

# Test SonarQube with sample project
cd /tmp && sonar-scanner -X

# Test SonarQube analysis
cd /target && sonar-scanner -Dsonar.projectKey=test -Dsonar.sources=. -X
```

### Directory Structure
```
SimpleSecCheck/
├── sonarqube/
│   ├── config.yaml
│   └── project-template.properties
```

## Step-by-Step Implementation

### Step 1: Update Dockerfile (30 min)
1. Add SonarQube Scanner CLI installation section
2. Add environment variables for SonarQube
3. Set up PATH for sonar-scanner command
4. Test Docker build

### Step 2: Create Configuration Directory (15 min)
1. Create `sonarqube/` directory
2. Create `sonarqube/config.yaml` file
3. Add basic configuration settings
4. Test configuration loading

### Step 3: Create Project Template (15 min)
1. Create `sonarqube/project-template.properties` file
2. Add basic project properties
3. Set up default exclusions
4. Test template application

### Step 4: Set Up Environment Variables (15 min)
1. Add SonarQube environment variables to Dockerfile
2. Add to orchestrator environment
3. Test environment variable access
4. Validate configuration paths

### Step 5: Test Installation (45 min)
1. Build Docker image with SonarQube
2. Test SonarQube Scanner CLI installation
3. Test SonarQube with sample code
4. Validate configuration files
5. Verify environment variables

## Validation
- SonarQube Scanner CLI responds to `--version` command
- SonarQube configuration file loads correctly
- Environment variables are accessible in container
- SonarQube can scan sample code
- SonarQube generates basic reports

## Next Steps
- Proceed to Phase 2: Core Implementation
- Create SonarQube execution script
- Create SonarQube processor

