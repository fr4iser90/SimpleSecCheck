# Brakeman Integration – Phase 1: Foundation Setup

## Overview
This phase establishes the foundation for Brakeman integration by installing Brakeman and creating configuration files.

## Objectives
- [ ] Install Brakeman gem in Docker container
- [ ] Create Brakeman configuration directory structure
- [ ] Create configuration file with proper settings
- [ ] Set up environment variables for Brakeman scanning
- [ ] Test Brakeman installation and basic functionality

## Deliverables
- Directory: `brakeman/` - Brakeman configuration directory
- File: `brakeman/config.yaml` - Brakeman configuration file
- Dockerfile: Update Dockerfile with Brakeman gem installation
- Environment: Set up environment variables for Brakeman

## Dependencies
- Requires: None
- Blocks: Phase 2 (Core Implementation)

## Estimated Time
2 hours

## Success Criteria
- [ ] Brakeman is installed in Docker container
- [ ] Configuration directory and files are created
- [ ] Environment variables are properly set up
- [ ] Basic Brakeman functionality is verified
- [ ] Configuration file is validated

## Implementation Details

### Step 1: Install Brakeman
Update the Dockerfile to install Brakeman:

```dockerfile
# Install Brakeman (Ruby on Rails security scanner)
RUN apt-get update && apt-get install -y ruby ruby-dev build-essential && \
    gem install brakeman --no-document
```

### Step 2: Create Configuration Directory
Create the Brakeman configuration directory structure:

```bash
mkdir -p brakeman
```

### Step 3: Create Configuration File
Create `brakeman/config.yaml` with scanning configuration:

```yaml
# Brakeman Configuration for SimpleSecCheck
# Purpose: Configure Brakeman for Ruby on Rails security scanning

# Output settings
output_format: json  # json, to_file, plain, tabs, csv
report_plain: true
report_verbose: true

# Scan settings
min_confidence: 1  # 0=weak, 1=medium, 2=strong, 3=certain

# Security checks to run
check_assignment: true
check_attr_accessible: true
check_basic_auth: true
check_cache: true
check_cookie_flag: true
check_create_with: true
check_cross_site_scripting: true
check_deserialize: true
check_details_escape: true
check_digest_auth: true
check_direct_use_of_model: true
check_dynamic_finders: true
check_eval: true
check_execute: true
check_file_access: true
check_filter_skip: true
check_forgery: true
check_html_escape: true
check_human_enum: true
check_ignore_mass_assignment: true
check_implicit_render: true
check_jruby_xss: true
check_known_vuln: true
check_legal: true
check_link_to_href: true
check_load_nonexistent: true
check_mail_to: true
check_manual_encoding: true
check_mass_assignment: true
check_model_attr: true
check_model_files: true
check_model_serialize: true
check_multiple_publicly_accessible: true
check_nested_attributes: true
check_nested_attributes_unpermitted: true
check_no_sql_injection: true
check_permitted_parameters: true
check_pg_advisory_lock: true
check_postgres_sql: true
check_presence_in_include: true
check_quote: true
check_rails_cve: true
check_rails4_http_only_cookies: true
check_raw_sql: true
check_render_csv: true
check_render_inline: true
check_safe_buffer_manipulation: true
check_sanitize: true
check_sanitize_css: true
check_sanitize_method: true
check_scope_filtering: true
check_select_vuln: true
check_send: true
check_serialization: true
check_session_manipulation: true
check_session_secret_key: true
check_sql_injection: true
check_static_redirects: true
check_symbol_do_cve: true
check_translate_bug: true
check_unscoped_find: true
check_unescape_html: true
check_unescape_href: true
check_user_input: true
check_validation_regex: true
check_vulnerable_content_tag: true
check_without_protection: true
check_weak_auth: true
check_weak_encryption: true
check_weak_ssl_version: true
check_xss_protection: true

# File patterns to scan
file_patterns:
  - "app/**/*.rb"
  - "lib/**/*.rb"
  - "config/**/*.rb"

# Exclude patterns
exclude_patterns:
  - "*/test/*"
  - "*/spec/*"
  - "*/vendor/*"
  - "*/node_modules/*"
```

### Step 4: Add Environment Variables
Add environment variables to `scripts/security-check.sh`:

```bash
export BRAKEMAN_CONFIG_PATH_IN_CONTAINER="$BASE_PROJECT_DIR/brakeman/config.yaml"
```

### Step 5: Test Installation
Verify Brakeman installation:

```bash
# Test that Brakeman can run
brakeman --version
```

## Notes
- Brakeman requires Ruby to run
- Works with Ruby on Rails applications primarily
- Supports both standard and Lazy initialization mode
- Can scan custom Rails engines

