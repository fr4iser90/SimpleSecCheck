# Anchore Integration – Phase 1: Foundation Setup

## Overview
Install Anchore Grype CLI tool in the Docker container and set up the configuration structure for container image vulnerability scanning.

## Objectives
- [ ] Install Anchore Grype CLI in Dockerfile
- [ ] Create Anchore configuration directory
- [ ] Add Anchore configuration file
- [ ] Set up vulnerability scanning parameters

## Deliverables
- File: `Dockerfile` - Anchore Grype CLI installation
- Directory: `anchore/` - Configuration directory
- File: `anchore/config.yaml` - Anchore scanning configuration
- Environment: Working Anchore CLI in container

## Implementation Steps

### 1. Install Anchore Grype CLI in Dockerfile
**Location**: `Dockerfile`  
**Action**: Add installation section for Anchore Grype CLI

```dockerfile
# Install Anchore Grype (container image vulnerability scanner)
RUN curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin
```

### 2. Create Anchore Configuration Directory
**Location**: `anchore/`  
**Action**: Create new directory for Anchore configuration files

```bash
mkdir -p anchore/
```

### 3. Create Anchore Configuration File
**Location**: `anchore/config.yaml`  
**Action**: Create configuration file with scanning parameters

```yaml
# Anchore Grype Configuration for SimpleSecCheck
# Container image vulnerability scanning configuration

# Global configuration
# Only scan for packages with known vulnerabilities
fail-on-severity: high  # Only fail on high severity

# Vulnerability database update settings
# Update vulnerability database on first run
db:
  update-url: https://toolbox-data.anchore.io/grype/databases/listing.json
  cache-dir: /tmp/grype-db
  auto-update: true

# Output configuration
output: json

# Check configuration
check-for-app-update: false

# Scan configuration
scope: AllLayers  # Scan all layers of the container image

# File matching
only-fixed: false  # Show both fixed and unfixed vulnerabilities
```

### 4. Update Docker Compose Configuration
**Location**: `docker-compose.yml`  
**Action**: Add volume mount for Anchore configuration

Add to volumes section:
```yaml
- ./anchore:/SimpleSecCheck/anchore
```

Add to environment variables:
```yaml
- ANCHORE_CONFIG_PATH_IN_CONTAINER=/SimpleSecCheck/anchore/config.yaml
- ANCHORE_IMAGE=${ANCHORE_IMAGE:-}
```

## Dependencies
- Requires: Working Dockerfile with base Ubuntu 22.04 image
- Blocks: Phase 2 (Core Implementation)

## Estimated Time
2 hours

## Success Criteria
- [ ] Anchore Grype CLI installed in Docker image
- [ ] Anchore configuration directory exists
- [ ] Configuration file is properly formatted
- [ ] Docker image builds successfully with Anchore
- [ ] Docker compose configuration includes Anchore settings

## Testing
- [ ] Build Docker image: `docker build -t simpleseccheck .`
- [ ] Verify Anchore CLI: `docker run --rm simpleseccheck grype --version`
- [ ] Check configuration: `docker run --rm simpleseccheck ls -la /SimpleSecCheck/anchore/`

## Notes
- Anchore Grype is a standalone CLI tool similar to Trivy
- It scans container images for known vulnerabilities
- Uses public vulnerability databases
- No external services required

