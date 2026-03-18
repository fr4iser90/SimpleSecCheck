# SimpleSecCheck Scanner

The scanner component of SimpleSecCheck is a modular security scanning engine that executes various security tools in isolated Docker containers.

## Overview

The scanner provides a unified interface for multiple security analysis tools:
- **Static Application Security Testing (SAST)**
- **Software Composition Analysis (SCA)**
- **Container Security Scanning**
- **Infrastructure as Code (IaC) Security**
- **Web Application Security Testing**

## Architecture

### Core Engine (`scanner/core/`)
- **Orchestrator**: Coordinates scanner execution and result collection
- **Scanner Registry**: Manages available scanner plugins
- **Step Registry**: Handles execution steps and workflows
- **Project Detector**: Identifies project types and technologies
- **Results Waiter**: Manages asynchronous result collection

### Plugin System (`scanner/plugins/`)
- **Modular Design**: Each scanner is a separate plugin
- **Standardized Interface**: Consistent API for all scanners
- **Easy Extension**: New scanners can be added without core changes
- **Manifest identity**: The technical tool ID is **`id` in `manifest.yaml`** (must match the plugin folder name). There is no `name` field—use **`display_name`** for UI. DB `scanner_tool_settings.scanner_key` and registry `tools_key` always equal that `id`.

### Output Processing (`scanner/output/`)
- **HTML Report Generator**: Creates web-based security reports
- **WebUI**: Interactive web interface for results
- **AI Prompt Modal**: LLM integration for security analysis

## Supported Scanners

### Static Analysis (SAST)
- **Bandit**: Python security linter
- **ESLint**: JavaScript/TypeScript security rules
- **Brakeman**: Ruby on Rails security scanner
- **Semgrep**: Multi-language static analysis
- **CodeQL**: GitHub's semantic code analysis

### Dependency Analysis (SCA)
- **Safety**: Python dependency vulnerability scanner
- **NPM Audit**: Node.js package vulnerability scanner
- **Snyk**: Comprehensive dependency security
- **Trivy**: Container and dependency scanner

### Container Security
- **Docker Bench**: Docker security best practices
- **Clair**: Container vulnerability scanner
- **Anchore**: Container image analysis

### Infrastructure as Code
- **Checkov**: Terraform, CloudFormation, Kubernetes security
- **Kube Hunter**: Kubernetes security testing
- **Kube Bench**: Kubernetes security benchmarks

### Web Application Security
- **OWASP ZAP**: Web application security scanner
- **Nikto**: Web server scanner
- **Wapiti**: Web application vulnerability scanner

### Secrets Detection
- **Gitleaks**: Git repository secrets scanner
- **TruffleHog**: Secret detection in code
- **Detect Secrets**: Multi-algorithm secret detection

## Workflow

### 1. Project Detection
```
Target Directory → Technology Detection → Scanner Selection → Configuration
```

### 2. Scanner Execution
```
Scanner Plugin → Container Start → Tool Execution → Result Collection
```

### 3. Result Processing
```
Raw Output → Parse & Normalize → Severity Mapping → Report Generation
```

### 4. Output Generation
```
Structured Data → HTML Report → WebUI Integration → AI Analysis
```

## Docker Usage

### Build Image
```bash
docker build -t simpleseccheck/scanner:latest .
```

### Run Scanner
```bash
docker run --rm \
  -v /path/to/target:/app/target \
  -v /path/to/results:/app/results \
  -e SCAN_TYPE=code \
  -e SCAN_ID=scan-123 \
  -e TARGET_MOUNT_PATH=/app/target \
  simpleseccheck/scanner:latest
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SCAN_TYPE` | `code` | Type of scan (code, container, web) |
| `SCAN_ID` | `auto-generated` | Unique scan identifier |
| `TARGET_MOUNT_PATH` | `/app/target` | Path to scan target |
| `RESULTS_DIR` | `/app/results` | Output directory |
| `FINDING_POLICY` | `default` | Policy for filtering findings |
| `COLLECT_METADATA` | `true` | Enable metadata collection |
| `EXCLUDE_PATHS` | `[]` | Paths to exclude from scan |

### Docker Compose
```yaml
scanner:
  build: ./scanner
  environment:
    - SCAN_TYPE=code
    - SCAN_ID=${SCAN_ID}
    - TARGET_MOUNT_PATH=/app/target
  volumes:
    - ./target:/app/target
    - ./results:/app/results
  command: ["python", "scanner/cli/scanner_main.py"]
```

## Configuration

### Scanner Selection
Scanners are automatically selected based on project type:
- **Python**: Bandit, Safety, Semgrep
- **JavaScript**: ESLint, NPM Audit, Semgrep
- **Ruby**: Brakeman, Bundler Audit
- **Java**: CodeQL, SpotBugs
- **Go**: GoSec, Semgrep
- **Docker**: Docker Bench, Trivy
- **Kubernetes**: Kube Hunter, Checkov

### Custom Configuration
```yaml
# scanner_config.yaml
scanners:
  bandit:
    config_file: .bandit
    exclude_files: ["tests/*", "docs/*"]
  eslint:
    config_file: .eslintrc.json
    rules: ["security/detect-unsafe-regex"]
```

### Finding Policies
```yaml
# finding_policy.yaml
severity_threshold: MEDIUM
exclude_patterns:
  - "path/to/ignore/*"
  - "test/**/*"
  - "vendor/**/*"
```

## Plugin Development

### Creating a New Scanner Plugin

1. **Create Plugin Directory**
```bash
mkdir scanner/plugins/my_scanner
```

2. **Implement Scanner Interface**
```python
from scanner.core.base_scanner import BaseScanner

class MyScanner(BaseScanner):
    def __init__(self, config):
        super().__init__(config)
        
    def scan(self, target_path):
        # Implement scanning logic
        pass
        
    def parse_results(self, output):
        # Parse scanner output
        pass
```

3. **Register Plugin**
```python
# scanner/core/scanner_registry.py
from scanner.plugins.my_scanner import MyScanner

SCANNER_REGISTRY = {
    'my_scanner': MyScanner,
    # ... existing scanners
}
```

4. **Add Configuration**
```yaml
# scanner_config.yaml
scanners:
  my_scanner:
    enabled: true
    config_file: .my_scanner_config
```

### Plugin Interface Requirements

Every scanner plugin must implement:
- **scan()**: Execute the security scan
- **parse_results()**: Parse and normalize output
- **get_metadata()**: Return scanner information
- **is_supported()**: Check if target is supported

## Output Formats

### JSON Results
```json
{
  "scan_id": "scan-123",
  "scanner": "bandit",
  "findings": [
    {
      "id": "B101",
      "severity": "HIGH",
      "confidence": "HIGH",
      "title": "Use of assert detected",
      "description": "Assert used in production code",
      "file": "app.py",
      "line": 42,
      "code": "assert condition"
    }
  ],
  "metadata": {
    "scanner_version": "1.7.5",
    "scan_time": "2024-01-01T12:00:00Z"
  }
}
```

### HTML Reports
- Interactive web-based reports
- Filterable by severity, scanner, file
- Trend analysis and comparison
- Export functionality

### WebUI Integration
- Real-time scan progress
- Interactive result exploration
- AI-powered analysis suggestions
- Team collaboration features

## Performance Optimization

### Resource Management
```bash
# Limit memory usage
-e SCANNER_MEMORY_LIMIT=2g

# Limit CPU usage
-e SCANNER_CPU_LIMIT=1.0

# Set timeout
-e SCANNER_TIMEOUT=30m
```

### Parallel Execution
```yaml
# scanner_config.yaml
parallel_scanners: 3
scanner_timeout: 30m
```

### Caching
```bash
# Enable dependency caching
-e ENABLE_CACHE=true
-v /cache:/app/cache
```

## Security Considerations

### Container Isolation
- Each scanner runs in isolated container
- Limited network access
- Read-only target directories
- Resource limits enforced

### Input Validation
- Target path validation
- Configuration sanitization
- Output validation and sanitization

### Secrets Management
- No secrets stored in containers
- Environment variables for credentials
- Secure credential passing

## Troubleshooting

### Common Issues

1. **Scanner Not Found**
   ```bash
   # Check available scanners
   docker run simpleseccheck/scanner:latest list-scanners
   
   # Verify scanner registration
   docker run simpleseccheck/scanner:latest check-scanner bandit
   ```

2. **Permission Denied**
   ```bash
   # Check target directory permissions
   ls -la /path/to/target
   
   # Run with proper permissions
   docker run -u $(id -u):$(id -g) simpleseccheck/scanner:latest
   ```

3. **Memory Issues**
   ```bash
   # Increase memory limit
   docker run -m 4g simpleseccheck/scanner:latest
   
   # Enable swap
   docker run --memory-swap=8g simpleseccheck/scanner:latest
   ```

4. **Network Issues**
   ```bash
   # Disable network access
   docker run --network none simpleseccheck/scanner:latest
   
   # Use proxy
   docker run -e HTTP_PROXY=http://proxy:8080 simpleseccheck/scanner:latest
   ```

### Debug Mode
```bash
# Enable verbose logging
docker run -e DEBUG=true simpleseccheck/scanner:latest

# Run with shell access
docker run -it --entrypoint /bin/bash simpleseccheck/scanner:latest

# Check scanner output
docker run -e LOG_LEVEL=DEBUG simpleseccheck/scanner:latest
```

## Development

### Local Testing
```bash
# Run specific scanner
python scanner/cli/scanner_main.py --scanner bandit --target /path/to/code

# Test with sample projects
python scanner/cli/scanner_main.py --scanner bandit --target ./samples/python

# Debug mode
python scanner/cli/scanner_main.py --debug --scanner eslint
```

### Adding New Scanner Types
1. Create scanner plugin
2. Register in scanner registry
3. Add configuration schema
4. Update documentation
5. Add tests

### Testing Framework
```bash
# Run unit tests
python -m pytest tests/

# Run integration tests
python -m pytest tests/integration/

# Test specific scanner
python -m pytest tests/test_bandit.py
```

## Integration

### CI/CD Pipeline
```yaml
# GitHub Actions
- name: Run Security Scan
  uses: simpleseccheck/scanner-action@v1
  with:
    target: ${{ github.workspace }}
    output: results/
    scanners: bandit,eslint,safety
```

### API Integration
```bash
# Start scan via API
curl -X POST http://scanner:8080/scan \
  -H "Content-Type: application/json" \
  -d '{"target": "/app", "scanners": ["bandit", "eslint"]}'

# Get scan results
curl http://scanner:8080/results/scan-123
```

### Webhook Notifications
```yaml
# scanner_config.yaml
webhooks:
  - url: https://example.com/webhook
    events: ["scan_started", "scan_completed", "scan_failed"]
    headers:
      Authorization: "Bearer token"