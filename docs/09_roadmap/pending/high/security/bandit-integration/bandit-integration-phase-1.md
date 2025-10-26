# Bandit Integration – Phase 1: Foundation Setup

## Overview
This phase establishes the foundation for Bandit integration by installing the Bandit package and creating configuration files.

## Objectives
- [ ] Install Bandit package in Dockerfile
- [ ] Create Bandit configuration directory and config.yaml
- [ ] Set up Bandit environment variables
- [ ] Test Bandit CLI installation

## Deliverables
- File: `Dockerfile` - Add Bandit installation command
- File: `bandit/config.yaml` - Create Bandit configuration file
- Directory: `bandit/` - Create Bandit configuration directory
- Environment: BANDIT_CONFIG_PATH set in Dockerfile

## Dependencies
- Requires: None
- Blocks: Phase 2 start

## Estimated Time
2 hours

## Success Criteria
- [ ] Bandit package successfully installed in Docker image
- [ ] Bandit CLI available and executable in container
- [ ] Config.yaml file created with proper settings
- [ ] Environment variables configured correctly
- [ ] Test Bandit installation with --version command

## Technical Details

### Dockerfile Updates
Add the following to the Dockerfile after Safety installation:
```dockerfile
# Install Bandit CLI
RUN pip3 install bandit[toml]

# Set Bandit environment variables
ENV BANDIT_CONFIG_PATH=/SimpleSecCheck/bandit/config.yaml
```

### Bandit Configuration
Create `bandit/config.yaml` with the following structure:
```yaml
# Bandit Configuration for SimpleSecCheck
# Purpose: Configure Bandit for Python code security scanning

# Output formats
output_formats:
  - json
  - text

# Scan options
scan_options:
  # Aggressive mode (more thorough scan)
  aggressive: false
  
  # Show skipped tests
  show_skipped: true
  
  # Verbose output
  verbose: true
  
  # Exclude tests by ID
  exclude_tests: []
  
  # Severity threshold (low/medium/high)
  severity_threshold: low
  
  # Confidence threshold (low/medium/high)
  confidence_threshold: low

# Include test IDs to run
include_tests:
  - B101  # assert_used
  - B102  # exec_used
  - B103  # hardcoded_password
  - B104  # hardcoded_bind_all_interfaces
  - B105  # hardcoded_password_string
  - B106  # hardcoded_password_funcarg
  - B107  # hardcoded_password_default
  - B301  # blacklist_calls
  - B302  # blacklist_imports
  - B303  # blacklist_imports
  - B304  # blacklist_imports
  - B305  # blacklist_imports
  - B306  # blacklist_imports
  - B307  # blacklist_imports
  - B308  # blacklist_imports
  - B309  # blacklist_imports
  - B401  # import_telnetlib
  - B402  # import_ftplib
  - B403  # import_pickle
  - B404  # import_subprocess
  - B405  # import_xml_etree
  - B406  # import_xmlrpclib
  - B407  # import_pycrypto
  - B501  # request_with_no_cert_validation
  - B502  # ssl_with_no_version
  - B503  # ssl_with_bad_version
  - B504  # ssl_with_bad_defaults
  - B505  # weak_cryptographic_key
  - B506  # use_of_insecure_hash_func
  - B601  # shell_injection
  - B602  # shell_injection_subprocess
  - B603  # subprocess_with_shell_equals_true
  - B604  # any_other_function_with_shell_equals_true
  - B701  # jinja2_autoescape_false
  - B702  # use_of_mako_templates
  - B801  # darglint
  - B901  # return_in_finally
  - B902  # linebreak_before_final_yield_or_return
  - B903  # blacklist_imports

# Exclude patterns
exclude_patterns:
  - "*/test*"
  - "*/tests/*"
  - "*/__pycache__/*"
  - "*/venv/*"
  - "*/env/*"
  - "*/virtualenv/*"
  - "*/migrations/*"

# Report settings
report_settings:
  # Include detailed vulnerability information
  detailed: true
  
  # Show suppressed issues
  show_suppressed: false
  
  # Output format for reports
  output_format: json

# Integration settings
integration:
  # Exit code on vulnerabilities found
  exit_on_vulnerabilities: false
  
  # Include in HTML report
  include_in_html: true
  
  # Generate separate report files
  generate_files: true
```

### Validation Steps
1. Build Docker image and verify Bandit installation
2. Run `bandit --version` in container to confirm installation
3. Check configuration file is readable
4. Validate environment variables are set correctly

## Notes
- Bandit is a security linter for Python code
- It scans Python files for known security issues
- Common findings include: hardcoded secrets, shell injection, SSL issues
- Installation with [toml] extras provides additional configuration options

## Validation Marker
✅ Phase 1 files validated and created: 2025-10-26T08:05:28.000Z

