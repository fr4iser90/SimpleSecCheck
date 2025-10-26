# GitLeaks Integration - Implementation Plan

## 📋 Task Overview
- **Feature/Component Name**: GitLeaks Integration
- **Priority**: High
- **Category**: security
- **Estimated Time**: 6 hours
- **Dependencies**: None
- **Related Issues**: Secret detection in repositories
- **Created**: 2025-10-26T07:30:00.000Z
- **Last Updated**: 2025-10-26T07:30:00.000Z

## 2. Technical Requirements
- **Tech Stack**: GitLeaks CLI (Go-based), Python 3, Bash scripts
- **Architecture Pattern**: Plugin-based integration following TruffleHog pattern
- **Database Changes**: None
- **API Changes**: None
- **Frontend Changes**: None
- **Backend Changes**: None

## 3. File Impact Analysis
#### Files to Modify:
- [ ] `Dockerfile` - Add GitLeaks CLI installation
- [ ] `scripts/security-check.sh` - Add GitLeaks orchestration section
- [ ] `scripts/generate-html-report.py` - Add GitLeaks import and HTML section generation

#### Files to Create:
- [ ] `gitleaks/config.yaml` - GitLeaks configuration file
- [ ] `scripts/tools/run_gitleaks.sh` - GitLeaks execution script
- [ ] `scripts/gitleaks_processor.py` - GitLeaks results processor

#### Files to Delete:
- [ ] None

## 4. Implementation Phases
#### Phase 1: Foundation Setup (2h)
- [ ] Install GitLeaks CLI in Dockerfile
- [ ] Create GitLeaks configuration directory: `gitleaks/`
- [ ] Add GitLeaks config file: `gitleaks/config.yaml`
- [ ] Set up secret detection rules and filters

#### Phase 2: Core Implementation (2h)
- [ ] Create: `scripts/tools/run_gitleaks.sh`
- [ ] Implement GitLeaks scanning script
- [ ] Support JSON output format
- [ ] Generate text reports
- [ ] Create: `scripts/gitleaks_processor.py`
- [ ] Parse GitLeaks JSON results
- [ ] Generate HTML sections for reports
- [ ] Integrate with LLM explanations

#### Phase 3: Integration & Testing (2h)
- [ ] Update `scripts/security-check.sh` to include GitLeaks
- [ ] Update HTML report generator with GitLeaks import
- [ ] Add GitLeaks to false positive whitelist
- [ ] Test with sample code projects
- [ ] Validate GitLeaks findings

## 5. Code Standards & Patterns
- **Coding Style**: Follow existing bash and Python patterns
- **Naming Conventions**: snake_case for Python, lowercase with underscores for bash
- **Error Handling**: Continue on errors, log failures
- **Logging**: Use tee to log to both file and stdout
- **Testing**: Test with real repositories
- **Documentation**: Add inline comments

## 6. Security Considerations
- [ ] Sanitize GitLeaks output to avoid exposing secrets
- [ ] Redact sensitive information in reports
- [ ] Handle verified vs unverified findings appropriately
- [ ] Add rate limiting for large repositories

## 7. Performance Requirements
- **Response Time**: < 5 minutes for standard repositories
- **Throughput**: Support repositories up to 1GB
- **Memory Usage**: < 500MB for GitLeaks process
- **Database Queries**: Not applicable
- **Caching Strategy**: Cache GitLeaks results per commit hash

## 8. Testing Strategy
#### Unit Tests:
- [ ] Test GitLeaks processor with sample JSON output
- [ ] Test HTML section generation
- [ ] Test error handling for malformed JSON

#### Integration Tests:
- [ ] Test GitLeaks scanning on sample repository
- [ ] Test full pipeline: scan -> process -> HTML report
- [ ] Test with different repository types

#### E2E Tests:
- [ ] Run full SimpleSecCheck scan with GitLeaks enabled
- [ ] Verify GitLeaks appears in HTML report
- [ ] Verify findings are correctly formatted

## 9. Documentation Requirements
- [ ] Update README with GitLeaks information
- [ ] Document configuration options
- [ ] Add examples of GitLeaks findings
- [ ] Document secret detection patterns

## 10. Deployment Checklist
- [ ] Add GitLeaks to Dockerfile
- [ ] Add run_gitleaks.sh script
- [ ] Add gitleaks_processor.py
- [ ] Update security-check.sh orchestration
- [ ] Update generate-html-report.py
- [ ] Test Docker build
- [ ] Test container execution

## 11. Rollback Plan
- [ ] Revert Dockerfile changes if GitLeaks fails to install
- [ ] Remove GitLeaks from security-check.sh orchestration
- [ ] Remove GitLeaks processor imports
- [ ] Restore previous HTML report generator

## 12. Success Criteria
- [ ] GitLeaks CLI successfully installs in Docker container
- [ ] GitLeaks scans complete without errors
- [ ] Results are correctly parsed and displayed in HTML reports
- [ ] LLM explanations are generated for findings
- [ ] No false positives in clean repositories
- [ ] Performance meets requirements (< 5 minutes for standard repos)

## 13. Risk Assessment
- [ ] **Low Risk**: GitLeaks is a mature, well-tested tool
- [ ] **Medium Risk**: Large repositories may cause performance issues
- [ ] **Low Risk**: Configuration is similar to existing TruffleHog integration

## 14. Current System Analysis
SimpleSecCheck uses a modular architecture with:
- Main orchestrator: `scripts/security-check.sh`
- Tool scripts in: `scripts/tools/`
- Processors in: `scripts/` (gitleaks_processor.py will join others)
- Docker-based execution with Ubuntu 22.04 base
- Results stored in: `results/[project]_[timestamp]/`
- HTML report generation: `scripts/generate-html-report.py`

## 15. References & Resources
- GitLeaks GitHub: https://github.com/gitleaks/gitleaks
- GitLeaks Documentation: https://github.com/gitleaks/gitleaks#configuration
- Similar Integration: TruffleHog (already implemented)
