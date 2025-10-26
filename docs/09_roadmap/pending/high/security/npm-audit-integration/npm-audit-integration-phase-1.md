# npm audit Integration – Phase 1: Foundation Setup

## Overview
Set up npm audit configuration and verify npm availability in the Docker environment.

## Objectives
- [ ] Verify npm is available in Docker container
- [ ] Create npm-audit configuration directory
- [ ] Create npm-audit/config.yaml configuration file
- [ ] Set up environment variables for npm audit

## Deliverables
- Directory: `npm-audit/` - Configuration directory
- File: `npm-audit/config.yaml` - npm audit configuration
- Documentation: Configuration options documented
- Verification: npm command working in container

## Dependencies
- Requires: None
- Blocks: Phase 2 - Core Implementation

## Estimated Time
2 hours

## Success Criteria
- [ ] npm-audit/ directory created
- [ ] config.yaml file created with proper structure
- [ ] npm command verified working in Docker
- [ ] npm audit command tested and working
- [ ] Configuration options documented

## Technical Details

### Configuration Directory Structure
```
npm-audit/
└── config.yaml
```

### config.yaml Structure
```yaml
npm_audit:
  # Enable or disable npm audit scanning
  enabled: true
  
  # Audit level: low, moderate, high, critical
  audit_level: "moderate"
  
  # Scan all dependencies including devDependencies
  include_dev_dependencies: true
  
  # Fix vulnerabilities automatically (use with caution)
  auto_fix: false
  
  # Ignore specific packages or advisories
  ignore_advisories: []
  ignore_packages: []
  
  # Output format
  output_format: "json"
  
  # Timeout for npm audit in seconds
  timeout: 300
```

### npm Verification Commands
```bash
# Check if npm is installed
npm --version

# Check if npm audit is available
npm audit --version

# Test npm audit with a sample
npm audit --json
```

### Environment Variables
Add to `Dockerfile` if needed:
```dockerfile
ENV NPM_AUDIT_CONFIG_PATH=/SimpleSecCheck/npm-audit/config.yaml
```

### Implementation Steps
1. Create `npm-audit/` directory in project root
2. Create `npm-audit/config.yaml` with default configuration
3. Verify npm is available in Dockerfile (should already be installed with Node.js)
4. Test npm audit command in container
5. Document configuration options in config.yaml comments

### Testing Checklist
- [ ] Verify npm command works in container
- [ ] Verify npm audit command works
- [ ] Test npm audit with sample package.json
- [ ] Verify config.yaml loads correctly
- [ ] Test all configuration options

### Notes
- npm comes pre-installed with Node.js in Ubuntu 22.04
- No additional installation needed
- npm audit uses the npm vulnerability database
- Works with package.json and package-lock.json files

