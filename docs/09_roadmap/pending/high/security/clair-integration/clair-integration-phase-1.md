# Clair Integration – Phase 1: Foundation Setup

## Overview
Set up the basic foundation for Clair integration by installing the Clair vulnerability scanner, creating the configuration directory, and setting up the initial configuration file with vulnerability scanning rules.

## Objectives
- [ ] Install Clair vulnerability scanner in Dockerfile
- [ ] Create Clair configuration directory: `clair/`
- [ ] Add Clair config file: `clair/config.yaml`
- [ ] Set up vulnerability database and scanning rules
- [ ] Add environment variables for Clair configuration
- [ ] Test Clair installation in Docker container

## Deliverables
- File: `Dockerfile` - Added Clair installation
- Environment Variable: `CLAIR_CONFIG_PATH` - Added in Dockerfile
- Directory: `clair/` - Created in project root
- File: `clair/config.yaml` - Clair configuration with vulnerability database settings

## Dependencies
- Requires: None (this is the first phase)
- Blocks: Phase 2 (Core Implementation)

## Estimated Time
2 hours

## Success Criteria
- [ ] Clair package successfully installs in Dockerfile
- [ ] `clair/` directory is created in project root
- [ ] `clair/config.yaml` file exists with proper configuration
- [ ] Environment variable `CLAIR_CONFIG_PATH` is set in Dockerfile
- [ ] Docker build completes without errors
- [ ] Clair CLI is accessible in container
- [ ] Clair can run with basic scan on test image

## Implementation Details

### 1. Dockerfile Updates

#### Install Clair (After line 86 or similar location)
```dockerfile
# Install Clair (container image vulnerability scanner)
RUN export CLAIR_URL=$(wget -qO- https://api.github.com/repos/quay/clair/releases/latest | grep browser_download_url | grep clair.*linux.*amd64 | cut -d '"' -f 4) && \
    wget -O clair.tar.gz $CLAIR_URL && \
    tar -xvzf clair.tar.gz -C /opt && \
    rm clair.tar.gz && \
    ln -s /opt/clair /usr/local/bin/clair
```

OR if Clair is distributed differently:
```dockerfile
# Install Clair (container image vulnerability scanner)
RUN git clone https://github.com/quay/clair.git /tmp/clair && \
    cd /tmp/clair && \
    make build && \
    mv clair /usr/local/bin/ && \
    rm -rf /tmp/clair
```

#### Add environment variable (After line 180, with other ENV declarations):
```dockerfile
# Set Clair environment variables
ENV CLAIR_CONFIG_PATH=/SimpleSecCheck/clair/config.yaml
ENV CLAIR_DB_PATH=/SimpleSecCheck/clair/db
```

### 2. Create Configuration Directory
- Create `clair/` directory in project root
- Follow existing pattern from `gitleaks/`, `trufflehog/`, `trivy/`, etc.

### 3. Create Configuration File
File: `clair/config.yaml`

Content structure:
```yaml
# Clair Configuration
version: 4
http_listen_addr: :6060
introspection_addr: :8089

indexer:
  connstring: host=localhost port=5432 user=postgres password=postgres dbname=clair sslmode=disable
  scanlock_retry: 10
  layer_scan_concurrency: 5
  migrations: true

matcher:
  connstring: host=localhost port=5432 user=postgres password=postgres dbname=clair sslmode=disable
  max_conn_pool: 100
  run: [updater]
  update_interval: 2h
  migrations: true

notifier:
  attempts: 3
  renotify_interval: 2h
  connstring: host=localhost port=5432 user=postgres password=postgres dbname=clair sslmode=disable
  migrations: true

scanner:
  package:
    - type: dpkg
  distributions:
    - version: debian:10
      updater: python
  name: string
  maximum_layer_size_bytes: 536870912
```

Note: Clair requires PostgreSQL database for vulnerability database.

### 4. Create Database Setup Script
File: `clair/setup-db.sh` (optional)

```bash
#!/bin/bash
# Setup PostgreSQL for Clair
docker run -d --name clair-db \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=clair \
  postgres:13
```

### 5. Testing
After Docker build, verify installation:
```bash
docker build -t simpleseccheck .
docker run --rm simpleseccheck clair --version
docker run --rm simpleseccheck ls /SimpleSecCheck/clair/
docker run --rm simpleseccheck cat /SimpleSecCheck/clair/config.yaml
```

## Notes
- Clair is a container image vulnerability scanner
- Clair requires PostgreSQL database for vulnerability data
- Configuration follows Clair v4+ syntax
- Database setup may need separate container
- Follow existing Trivy container scanning pattern
- Consider Clair vs Clair Core (different projects)

## Alternatives
- **Clair Core**: Simpler version of Clair without PostgreSQL requirement
- **Clair CLI**: Container-based scanning tool
- Use existing Trivy for container scanning instead

## Validation
Run these commands after implementation:
1. `docker build -t simpleseccheck .` - Should complete successfully
2. `docker run --rm simpleseccheck clair --version` - Should print version
3. `docker run --rm simpleseccheck ls /SimpleSecCheck/clair/` - Should show config.yaml
4. `docker run --rm simpleseccheck cat /SimpleSecCheck/clair/config.yaml` - Should show configuration

## Troubleshooting
- If Clair installation fails, check GitHub releases page for correct download URL
- If PostgreSQL is required, set up separate PostgreSQL container
- If Clair is too complex, consider using Trivy instead
- Check Clair documentation for latest configuration format

## Next Steps
After Phase 1 completion:
- Proceed to Phase 2: Create execution script and processor
- Test Clair with sample container image
- Verify configuration works correctly

