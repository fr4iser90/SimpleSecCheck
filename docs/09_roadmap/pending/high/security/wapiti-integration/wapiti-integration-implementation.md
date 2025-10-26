# Wapiti Integration - Implementation Plan

## 1. Project Overview
- **Feature/Component Name**: Wapiti Integration
- **Priority**: High
- **Category**: security
- **Estimated Time**: 6 hours
- **Dependencies**: None
- **Related Issues**: Dynamic Application Security Testing (DAST)
- **Created**: 2025-10-25T23:44:26.000Z
- **Last Updated**: 2025-10-26T00:30:00.000Z

## 2. Technical Requirements
- **Tech Stack**: Python, Bash, Wapiti CLI
- **Architecture Pattern**: Modular tool integration
- **Database Changes**: None
- **API Changes**: None
- **Frontend Changes**: HTML report generation
- **Backend Changes**: Wapiti processor, script creation

## 3. Current System Analysis
SimpleSecCheck uses a modular architecture with:
- Main orchestrator: `scripts/security-check.sh`
- Tool scripts in: `scripts/tools/`
- Processors in: `scripts/` (semgrep_processor.py, trivy_processor.py, codeql_processor.py, nuclei_processor.py, owasp_dependency_check_processor.py, safety_processor.py, snyk_processor.py, sonarqube_processor.py, terraform_security_processor.py, trufflehog_processor.py, zap_processor.py)
- Docker-based execution with Ubuntu 22.04 base
- Results stored in: `results/[project]_[timestamp]/`
- HTML report generation: `scripts/generate-html-report.py`

## 4. Implementation Phases

#### Phase 1: Foundation Setup (2 hours)
- [ ] Wapiti Installation: Add Wapiti to Dockerfile
- [ ] Wapiti Configuration: Create wapiti/ directory with config.yaml
- [ ] Environment Setup: Set up Wapiti scanning parameters

#### Phase 2: Core Implementation (2 hours)
- [ ] Wapiti Script Creation: Create scripts/tools/run_wapiti.sh
- [ ] Wapiti Processor Creation: Create scripts/wapiti_processor.py
- [ ] Report Generation: Generate JSON and text reports
- [ ] LLM Integration: Integrate with LLM explanations

#### Phase 3: Integration & Testing (2 hours)
- [ ] System Integration: Update scripts/security-check.sh
- [ ] Dockerfile Updates: Add Wapiti to Dockerfile
- [ ] HTML Report Updates: Update generate-html-report.py
- [ ] Testing & Validation: Test Wapiti integration

## 5. File Impact Analysis

#### Files to Modify:
- [ ] `scripts/security-check.sh` - Add Wapiti orchestration
- [ ] `Dockerfile` - Add Wapiti installation
- [ ] `scripts/generate-html-report.py` - Add Wapiti HTML generation

#### Files to Create:
- [ ] `scripts/tools/run_wapiti.sh` - Wapiti execution script
- [ ] `scripts/wapiti_processor.py` - Wapiti result processor
- [ ] `wapiti/config.yaml` - Wapiti configuration file

#### Files to Delete:
- [ ] None

## 6. Code Standards & Patterns
- **Coding Style**: Follow existing Python and Bash patterns in processors and tools
- **Naming Conventions**: Use wapiti_ prefix for processor, run_wapiti.sh for script
- **Error Handling**: Use try-except blocks, log errors to main log file
- **Logging**: Use tee -a pattern to write to LOG_FILE
- **Testing**: Test with sample web applications
- **Documentation**: Follow existing processor documentation style

## 7. Security Considerations
- [ ] Validate target URL before scanning
- [ ] Implement rate limiting to avoid overwhelming target
- [ ] Secure storage of scan results
- [ ] Handle authentication if needed for target
- [ ] Respect robots.txt and security headers

## 8. Performance Requirements
- **Response Time**: Scan duration should be under 10 minutes for small sites
- **Throughput**: Handle concurrent scans efficiently
- **Memory Usage**: Moderate memory footprint
- **Database Queries**: None (Wapiti does not use database)
- **Caching Strategy**: Cache configuration files to avoid reload

## 9. Testing Strategy
#### Unit Tests:
- [ ] Test Wapiti processor with mock JSON output
- [ ] Test HTML section generation
- [ ] Test error handling for missing files

#### Integration Tests:
- [ ] Test Wapiti script execution with real target
- [ ] Test integration with security-check.sh
- [ ] Test HTML report generation with Wapiti data

#### E2E Tests:
- [ ] Test complete Wapiti integration workflow
- [ ] Test with sample web applications
- [ ] Test error recovery and logging

## 10. Documentation Requirements
- [ ] Update README.md with Wapiti information
- [ ] Add Wapiti usage examples
- [ ] Document configuration options
- [ ] Document scan types and modes

## 11. Deployment Checklist
- [ ] Update Dockerfile with Wapiti installation
- [ ] Update security-check.sh with Wapiti orchestration
- [ ] Update generate-html-report.py with Wapiti section
- [ ] Test in Docker container
- [ ] Verify HTML report generation

## 12. Rollback Plan
- [ ] Remove Wapiti from Dockerfile if issues occur
- [ ] Remove Wapiti orchestration from security-check.sh
- [ ] Remove Wapiti processor from generate-html-report.py
- [ ] Document rollback steps

## 13. Success Criteria
- [ ] Wapiti CLI installed in Docker container
- [ ] Wapiti configuration file created
- [ ] run_wapiti.sh script executes successfully
- [ ] wapiti_processor.py processes results correctly
- [ ] HTML report includes Wapiti section
- [ ] Integration works with security-check.sh
- [ ] Tests pass without errors

## 14. Risk Assessment
- **Low Risk**: Wapiti is a stable tool with good documentation
- **Medium Risk**: Integration with existing system may require adjustments
- **Low Risk**: Configuration and deployment are straightforward
- **Mitigation**: Follow existing patterns from ZAP and Nuclei integration

## 15. AI Auto-Implementation Instructions
- **source_type**: 'markdown_doc'
- **source_path**: 'docs/09_roadmap/pending/high/security/wapiti-integration/wapiti-integration-implementation.md'
- **category**: 'security'
- **automation_level**: 'semi_auto'
- **confirmation_required**: true
- **max_attempts**: 3
- **git_branch_required**: true
- **new_chat_required**: true

## 16. References & Resources
- Wapiti Documentation: https://wapiti.readthedocs.io/
- Wapiti GitHub: https://github.com/wapiti-scanner/wapiti
- Existing DAST integrations: ZAP, Nuclei
- SimpleSecCheck architecture patterns

## 17. Validation Marker
- **File Structure Validated**: ✅ Yes
- **Codebase Analysis Complete**: ✅ Yes
- **Implementation Plan Complete**: ✅ Yes
- **Phase Files Created**: ✅ Yes
- **Task Ready for Implementation**: ✅ Yes

