# Safety Integration – Phase 1: Foundation Setup

## Overview
Set up Safety CLI installation and basic configuration for Python dependency vulnerability scanning.

## Objectives
- [ ] Install Safety CLI in Docker container
- [ ] Create Safety configuration directory and files
- [ ] Set up Safety environment variables
- [ ] Test Safety CLI installation and basic functionality

## Deliverables
- File: `Dockerfile` - Updated with Safety CLI installation
- File: `safety/config.yaml` - Safety configuration file
- File: `safety/requirements.txt` - Safety requirements template
- Environment: Safety CLI functional in container

## Dependencies
- Requires: Docker container setup
- Blocks: Phase 2 - Core Implementation

## Estimated Time
2 hours

## Success Criteria
- [ ] Safety CLI successfully installed in Docker container
- [ ] Safety configuration directory created
- [ ] Safety environment variables set
- [ ] Safety CLI responds to basic commands
- [ ] Safety can scan sample Python dependencies

## Technical Details

### Dockerfile Updates
```dockerfile
# Install Safety CLI
RUN pip3 install safety

# Set Safety environment variables
ENV SAFETY_CONFIG_PATH=/SimpleSecCheck/safety/config.yaml
```

### Safety Configuration
```yaml
# safety/config.yaml
safety:
  output_format: json
  check_requirements: true
  check_pipfile: true
  ignore_ids: []
  ignore_severity: []
  output_file: safety-results.json
```

### Environment Variables
```bash
export SAFETY_CONFIG_PATH="/SimpleSecCheck/safety/config.yaml"
export SAFETY_OUTPUT_DIR="/SimpleSecCheck/results"
```

### Testing Commands
```bash
# Test Safety installation
safety --version

# Test Safety with sample requirements
safety check --file /tmp/sample-requirements.txt

# Test Safety JSON output
safety check --json --file /tmp/sample-requirements.txt
```
