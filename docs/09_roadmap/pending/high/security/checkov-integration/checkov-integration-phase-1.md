# Checkov Integration – Phase 1: Foundation Setup

## Overview
Set up Checkov configuration and verify installation in the Docker container. This phase focuses on creating the basic configuration structure and environment setup needed for Checkov scanning.

## Objectives
- [ ] Verify Checkov installation in Dockerfile
- [ ] Create checkov/ directory structure
- [ ] Create checkov/config.yaml configuration file
- [ ] Set up environment variables for Checkov
- [ ] Document Checkov integration setup

## Deliverables
- File: `checkov/config.yaml` - Checkov configuration file
- File: `checkov/README.md` - Checkov usage documentation

## Dependencies
- Requires: Docker environment with Checkov installed
- Blocks: Phase 2 - Core Implementation

## Estimated Time
2 hours

## Success Criteria
- [ ] Checkov directory exists with config.yaml
- [ ] Configuration file includes all necessary settings
- [ ] Environment variables documented
- [ ] No errors in configuration validation
- [ ] Documentation complete

## Implementation Steps

### Step 1: Verify Dockerfile Installation
Check that Checkov is installed in the Dockerfile at line 62:
```dockerfile
# Install Checkov (Terraform security scanner)
RUN pip3 install checkov
```

### Step 2: Create Checkov Directory
Create the checkov configuration directory:
```bash
mkdir -p checkov/
```

### Step 3: Create Configuration File
Create `checkov/config.yaml`:
```yaml
# Checkov Configuration for SimpleSecCheck
version: "1.0"

# Scan settings
scan:
  # Infrastructure file patterns to scan
  file_patterns:
    - "*.tf"
    - "*.tfvars"
    - "*.tfstate"
    - "*.yml"
    - "*.yaml"
    - "Dockerfile"
    - "*.json"
  
  # Severity levels to include
  severity_levels:
    - CRITICAL
    - HIGH
    - MEDIUM
    - LOW
  
  # Output formats
  output_formats:
    - json
    - text
  
  # Framework support
  frameworks:
    - terraform
    - cloudformation
    - kubernetes
    - docker
    - arm
  
  # Skip checks by ID (configured via whitelist)
  skip_checks: []
```

### Step 4: Update Environment Variables
Ensure environment variables are set in Dockerfile:
```dockerfile
# Set Checkov environment variables
ENV CHECKOV_CONFIG_PATH=/SimpleSecCheck/checkov/config.yaml
```

## Notes
- Checkov is already installed in the Dockerfile
- This phase focuses on creating a separate Checkov integration if different from Terraform security scanning
- If this task is redundant with terraform-security-integration, consider marking this task as duplicate or consolidating

