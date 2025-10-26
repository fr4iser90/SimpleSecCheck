# Brakeman Integration - Implementation Plan

## 1. Project Overview
- **Feature/Component Name**: Brakeman Integration
- **Priority**: High
- **Category**: security
- **Estimated Time**: 6 hours
- **Dependencies**: None
- **Related Issues**: Static Application Security Testing (SAST) for Ruby applications
- **Created**: 2025-10-26T08:01:24.000Z
- **Last Updated**: 2025-10-26T08:01:24.000Z

## 2. Technical Requirements
- **Tech Stack**: Python, Bash, Ruby, Brakeman Gem
- **Architecture Pattern**: Modular tool integration
- **Database Changes**: None
- **API Changes**: None
- **Frontend Changes**: HTML report generation
- **Backend Changes**: Brakeman processor, script creation

## 3. Current System Analysis
SimpleSecCheck uses a modular architecture with:
- Main orchestrator: `scripts/security-check.sh`
- Tool scripts in: `scripts/tools/`
- Processors in: `scripts/` (semgrep_processor.py, trivy_processor.py, codeql_processor.py, nuclei_processor.py, owasp_dependency_check_processor.py, safety_processor.py, snyk_processor.py, sonarqube_processor.py, terraform_security_processor.py, trufflehog_processor.py, wapiti_processor.py, nikto_processor.py, zap_processor.py, eslint_processor.py, burp_processor.py)
- Docker-based execution with Ubuntu 22.04 base
- Results stored in: `results/[project]_[timestamp]/`
- HTML report generation: `scripts/generate-html-report.py`

## 4. Brakeman Integration Details

### 4.1 Brakeman Overview
- **Type**: Static Application Security Testing (SAST) for Ruby applications
- **Purpose**: Analyzes Ruby on Rails code for security vulnerabilities
- **Output**: JSON format with vulnerability findings
- **Common Findings**: SQL injection, XSS, mass assignment, insecure redirects, CSRF

### 4.2 Integration Strategy
- Install Brakeman as Ruby gem in Docker container
- Use CLI mode for automated scanning
- Generate JSON reports for processing
- Follow existing SAST tool patterns (Semgrep, CodeQL, Trivy)
- Scan Ruby/Rails files for security issues

## 5. Implementation Phases

#### Phase 1: Foundation Setup (2 hours)
- [ ] Brakeman Installation: Install Brakeman gem in Dockerfile
- [ ] Brakeman Configuration: Create brakeman/ directory with config.yaml
- [ ] Environment Setup: Set up Brakeman scanning parameters

#### Phase 2: Core Implementation (2 hours)
- [ ] Brakeman Script Creation: Create scripts/tools/run_brakeman.sh
- [ ] Brakeman Processor Creation: Create scripts/brakeman_processor.py
- [ ] Report Generation: Generate JSON and text reports
- [ ] LLM Integration: Integrate with LLM explanations

#### Phase 3: Integration & Testing (2 hours)
- [ ] System Integration: Update scripts/security-check.sh
- [ ] Dockerfile Updates: Add Brakeman installation to Dockerfile
- [ ] HTML Report Updates: Update generate-html-report.py
- [ ] Testing: Test with sample Ruby/Rails projects

## 6. File Impact Analysis
#### Files to Modify:
- [ ] `Dockerfile` - Add Brakeman gem installation
- [ ] `scripts/security-check.sh` - Add Brakeman orchestration
- [ ] `scripts/generate-html-report.py` - Add Brakeman report integration
- [ ] `conf/fp_whitelist.json` - Add Brakeman false positive handling

#### Files to Create:
- [ ] `brakeman/config.yaml` - Brakeman configuration
- [ ] `scripts/tools/run_brakeman.sh` - Brakeman execution script
- [ ] `scripts/brakeman_processor.py` - Brakeman result processor

#### Files to Delete:
- [ ] None

## 7. Code Standards & Patterns
- **Coding Style**: Follow existing Python and Bash patterns
- **Naming Conventions**: snake_case for files, consistent with existing tools
- **Error Handling**: Handle errors appropriately with logging
- **Logging**: Use existing log_message function
- **Testing**: Manual testing with sample Ruby/Rails applications
- **Documentation**: Inline comments and README updates

## 8. Security Considerations
- [ ] Validate Ruby project structure
- [ ] Sanitize report data in output
- [ ] Handle sensitive code snippets in reports
- [ ] Configure appropriate Brakeman checks
- [ ] Manage scan timeouts for large applications

## 9. Performance Requirements
- **Response Time**: < 2 minutes for standard Ruby application
- **Memory Usage**: < 500MB additional memory
- **Scan Scope**: Rails-specific security checks
- **Caching Strategy**: Cache scan results

## 10. Testing Strategy
#### Unit Tests:
- [ ] Test Brakeman processor functions
- [ ] Test configuration parsing
- [ ] Test result formatting

#### Integration Tests:
- [ ] Test with sample Ruby/Rails applications
- [ ] Test report generation
- [ ] Test error handling scenarios

#### E2E Tests:
- [ ] Test complete scan workflow
- [ ] Test HTML report integration
- [ ] Test false positive handling

## 11. Documentation Requirements
- [ ] Update README with Brakeman information
- [ ] Document Brakeman configuration options
- [ ] Add troubleshooting guide
- [ ] Update CHANGELOG

## 12. Deployment Checklist
- [ ] Verify Brakeman installation in Docker
- [ ] Test configuration file
- [ ] Validate script permissions
- [ ] Test report generation
- [ ] Verify error handling

## 13. Success Criteria
- [ ] Brakeman successfully scans Ruby/Rails applications
- [ ] Results are properly parsed and formatted
- [ ] HTML reports include Brakeman findings
- [ ] Error handling works correctly
- [ ] Performance meets requirements
- [ ] Documentation is complete

## 14. Risk Assessment
- [ ] Ruby version compatibility
- [ ] Performance impact on scan time
- [ ] False positive management
- [ ] Scan timeout for large applications

## 15. AI Auto-Implementation Instructions
- **source_type**: 'markdown_doc'
- **source_path**: 'docs/09_roadmap/pending/high/security/brakeman-integration/brakeman-integration-implementation.md'
- **category**: 'security'
- **automation_level**: 'semi_auto'
- **confirmation_required**: true
- **max_attempts**: 3
- **git_branch_required**: true
- **new_chat_required**: true

## 16. References & Resources
- [Brakeman Documentation](https://brakemanscanner.org/docs/)
- [Brakeman GitHub](https://github.com/presidentbeef/brakeman)
- [Ruby on Rails Security Guide](https://guides.rubyonrails.org/security.html)
- SimpleSecCheck Architecture
- Existing SAST Tool Integration Patterns

## 17. Brakeman-Specific Configuration
### Common Vulnerability Checks
- SQL injection vulnerabilities
- Cross-Site Scripting (XSS) issues
- Mass assignment vulnerabilities
- Insecure redirect and forward issues
- CSRF protection issues
- Authentication and authorization problems
- Cryptography weaknesses
- Information disclosure issues
- Insecure deserialization
- Server misconfiguration

## 18. Integration Details
### Ruby File Detection
- Detect `.rb`, `.rake`, Gemfile, config files
- Parse Rails application structure
- Run Brakeman scan on detected Ruby projects

### Report Format
- JSON output for machine-readable results
- Text output for human-readable summaries
- HTML integration for web-based reports

