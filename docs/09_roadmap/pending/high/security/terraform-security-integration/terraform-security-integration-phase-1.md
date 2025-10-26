# Terraform Security Integration – Phase 1: Foundation Setup

## Overview
Set up Checkov installation and configuration for Terraform security scanning in SimpleSecCheck.

## Objectives
- [ ] Install Checkov CLI in Dockerfile
- [ ] Create Terraform security configuration directory
- [ ] Set up configuration parameters
- [ ] Configure environment variables

## Deliverables
- Modified: `Dockerfile` - Add Checkov installation
- Created: `terraform-security/config.yaml` - Checkov configuration
- Feature: Checkov CLI installation
- Feature: Configuration setup

## Dependencies
- Requires: None
- Blocks: Phase 2 - Core Implementation

## Estimated Time
2 hours

## Success Criteria
- [ ] Checkov installed in Docker container
- [ ] Configuration directory created
- [ ] Configuration file created with proper settings
- [ ] Environment variables set
- [ ] Checkov executable and available

## Technical Details

### Dockerfile Modification
```dockerfile
# Install Checkov (Terraform security scanner)
RUN pip3 install checkov
```

### Configuration File Creation
Location: `terraform-security/config.yaml`

```yaml
# Checkov Configuration for SimpleSecCheck
version: "1.0"

# Scan settings
scan:
  # Terraform file patterns to scan
  file_patterns:
    - "*.tf"
    - "*.tfvars"
    - "*.tfstate"
  
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
  
  # Skip checks by ID (configured via whitelist)
  skip_checks: []
```

### Environment Variable Setup
Add to Dockerfile:
```dockerfile
# Set Terraform security environment variables
ENV TERRAFORM_SECURITY_CONFIG_PATH=/SimpleSecCheck/terraform-security/config.yaml
```

## Implementation Steps

### Step 1: Add Checkov to Dockerfile
1. Open `Dockerfile`
2. Locate pip3 install section
3. Add: `RUN pip3 install checkov`
4. Add environment variable: `ENV TERRAFORM_SECURITY_CONFIG_PATH=/SimpleSecCheck/terraform-security/config.yaml`

### Step 2: Create Configuration Directory
1. Create directory: `terraform-security/`
2. Create file: `terraform-security/config.yaml`
3. Add configuration content from Technical Details

### Step 3: Validate Installation
1. Build Docker image
2. Verify Checkov installation: `checkov --version`
3. Verify configuration file accessible in container
4. Test Checkov help command: `checkov --help`

## Testing
- Build Docker image
- Run container
- Execute Checkov command: `checkov --version`
- Verify configuration file exists

## Notes
- Checkov is Python-based, installs via pip3
- No additional system dependencies needed
- Configuration follows SimpleSecCheck patterns
- Environment variables follow existing conventions

