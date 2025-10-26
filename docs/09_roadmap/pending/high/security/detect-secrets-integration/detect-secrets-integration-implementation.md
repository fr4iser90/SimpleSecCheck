# Detect-secrets Integration - Implementation Plan

## 📋 Task Overview
- **Feature/Component Name**: Detect-secrets Integration
- **Priority**: High
- **Category**: security
- **Estimated Time**: 6 hours
- **Dependencies**: None
- **Related Issues**: Secret detection in code projects
- **Created**: 2025-10-26T07:43:46.000Z
- **Last Updated**: 2025-10-26T07:43:46.000Z

## 2. Technical Requirements
- **Tech Stack**: Detect-secrets Python CLI, Python 3, Bash scripts
- **Architecture Pattern**: Plugin-based integration following GitLeaks and TruffleHog pattern
- **Database Changes**: None
- **API Changes**: None
- **Frontend Changes**: None
- **Backend Changes**: None

## 3. File Impact Analysis
#### Files to Modify:
- [ ] `Dockerfile` - Add detect-secrets Python package installation
- [ ] `scripts/security-check.sh` - Add detect-secrets orchestration section
- [ ] `scripts/generate-html-report.py` - Add detect-secrets import and HTML section generation
- [ ] `conf/fp_whitelist.json` - Add detect-secrets false positive handling

#### Files to Create:
- [ ] `detect-secrets/config.yaml` - Detect-secrets configuration file
- [ ] `scripts/tools/run_detect_secrets.sh` - Detect-secrets execution script
- [ ] `scripts/detect_secrets_processor.py` - Detect-secrets results processor

#### Files to Delete:
- [ ] None

## 4. Implementation Phases
#### Phase 1: Foundation Setup (2h)
- [ ] Install detect-secrets Python package in Dockerfile
- [ ] Create detect-secrets configuration directory: `detect-secrets/`
- [ ] Add detect-secrets config file: `detect-secrets/config.yaml`
- [ ] Set up secret detection rules and filters

#### Phase 2: Core Implementation (2h)
- [ ] Create: `scripts/tools/run_detect_secrets.sh`
- [ ] Implement detect-secrets scanning script
- [ ] Support JSON output format
- [ ] Generate text reports
- [ ] Create: `scripts/detect_secrets_processor.py`
- [ ] Parse detect-secrets JSON results
- [ ] Generate HTML sections for reports
- [ ] Integrate with LLM explanations

#### Phase 3: Integration & Testing (2h)
- [ ] Update `scripts/security-check.sh` to include detect-secrets
- [ ] Update HTML report generator with detect-secrets import
- [ ] Add detect-secrets to false positive whitelist
- [ ] Test with sample code projects
- [ ] Validate detect-secrets findings

## 5. Code Standards & Patterns
- **Coding Style**: Follow existing bash and Python patterns
- **Naming Conventions**: snake_case for Python, lowercase with underscores for bash
- **Error Handling**: Continue on errors, log failures
- **Logging**: Use tee to log to both file and stdout
- **Testing**: Test with real repositories
- **Documentation**: Add inline comments

## 6. Security Considerations
- [ ] Sanitize detect-secrets output to avoid exposing secrets
- [ ] Redact sensitive information in reports
- [ ] Handle verified vs unverified findings appropriately
- [ ] Add rate limiting for large codebases
- [ ] Ensure secure handling of detected secrets

## 7. Performance Requirements
- **Response Time**: < 5 minutes for standard codebases
- **Throughput**: Support codebases up to 1GB
- **Memory Usage**: < 500MB for detect-secrets process
- **Database Queries**: Not applicable
- **Caching Strategy**: Cache results per file hash

## 8. Testing Strategy
#### Unit Tests:
- [ ] Test detect-secrets processor with sample JSON output
- [ ] Test HTML section generation
- [ ] Test error handling for malformed JSON
- [ ] Test configuration parsing

#### Integration Tests:
- [ ] Test detect-secrets scanning on sample codebase
- [ ] Test full pipeline: scan -> process -> HTML report
- [ ] Test with different codebase types
- [ ] Test false positive handling

#### E2E Tests:
- [ ] Run full SimpleSecCheck scan with detect-secrets enabled
- [ ] Verify detect-secrets appears in HTML report
- [ ] Verify findings are correctly formatted
- [ ] Verify LLM explanations are generated

## 9. Documentation Requirements
- [ ] Update README with detect-secrets information
- [ ] Document configuration options
- [ ] Add examples of detect-secrets findings
- [ ] Document secret detection patterns
- [ ] Update CHANGELOG

## 10. Deployment Checklist
- [ ] Add detect-secrets to Dockerfile
- [ ] Add run_detect_secrets.sh script
- [ ] Add detect_secrets_processor.py
- [ ] Update security-check.sh orchestration
- [ ] Update generate-html-report.py
- [ ] Test Docker build
- [ ] Test container execution

## 11. Rollback Plan
- [ ] Revert Dockerfile changes if detect-secrets fails to install
- [ ] Remove detect-secrets from security-check.sh orchestration
- [ ] Remove detect-secrets processor imports
- [ ] Restore previous HTML report generator

## 12. Success Criteria
- [ ] Detect-secrets Python package successfully installs in Docker container
- [ ] Detect-secrets scans complete without errors
- [ ] Results are correctly parsed and displayed in HTML reports
- [ ] LLM explanations are generated for findings
- [ ] No false positives in clean codebases
- [ ] Performance meets requirements (< 5 minutes for standard codebases)
- [ ] Integration follows existing GitLeaks and TruffleHog patterns

## 13. Risk Assessment
- [ ] **Low Risk**: Detect-secrets is a mature, well-tested Python tool
- [ ] **Medium Risk**: Large codebases may cause performance issues
- [ ] **Low Risk**: Configuration is similar to existing GitLeaks and TruffleHog integrations
- [ ] **Low Risk**: Python-based tool integrates smoothly with existing Python ecosystem

## 14. Current System Analysis
SimpleSecCheck uses a modular architecture with:
- Main orchestrator: `scripts/security-check.sh`
- Tool scripts in: `scripts/tools/`
- Processors in: `scripts/` (detect_secrets_processor.py will join others)
- Docker-based execution with Ubuntu 22.04 base
- Results stored in: `results/[project]_[timestamp]/`
- HTML report generation: `scripts/generate-html-report.py`
- Existing secret detection tools: GitLeaks and TruffleHog already integrated
- Pattern to follow: GitLeaks integration (Python processor with LLM support)

## 15. References & Resources
- Detect-secrets GitHub: https://github.com/Yelp/detect-secrets
- Detect-secrets Documentation: https://github.com/Yelp/detect-secrets/blob/main/docs/README.md
- Similar Integrations: GitLeaks and TruffleHog (already implemented)
- Existing Processors: `scripts/gitleaks_processor.py`, `scripts/trufflehog_processor.py`
- Existing Tool Scripts: `scripts/tools/run_gitleaks.sh`, `scripts/tools/run_trufflehog.sh`

## 🔍 Validation Results - 2025-10-26T07:43:46.000Z

### ✅ Architecture Analysis Complete
- **Current System**: Modular tool integration with clear separation
- **Tool Scripts**: Located in `scripts/tools/` with consistent patterns
- **Processors**: Located in `scripts/` with standardized interfaces
- **Orchestrator**: `scripts/security-check.sh` handles tool coordination
- **Report Generation**: `scripts/generate-html-report.py` consolidates results
- **Existing Secret Detection**: GitLeaks (Go) and TruffleHog (Go) already integrated

### ✅ Pattern Analysis Complete
- **Tool Scripts**: Follow `run_[tool].sh` naming convention
- **Processors**: Follow `[tool]_processor.py` naming convention
- **Environment Variables**: Consistent `TARGET_PATH`, `RESULTS_DIR`, `LOG_FILE`
- **Output Formats**: JSON + text reports for each tool
- **Error Handling**: Comprehensive error handling with logging
- **HTML Integration**: Each processor has `generate_[tool]_html_section()` function
- **Python Processors**: Use sys.path.insert, import LLM client, have debug() function
- **Python Processors**: Parse JSON results, generate HTML, integrate with LLM explanations

### ✅ Gap Analysis Complete
#### Missing Components Identified:
1. **Detect-secrets Python Installation**: Not present in Dockerfile (line 56 shows Safety, but no detect-secrets)
2. **Detect-secrets Configuration**: No detect-secrets/ directory structure
3. **Detect-secrets Execution Script**: Missing run_detect_secrets.sh
4. **Detect-secrets Processor**: Missing detect_secrets_processor.py
5. **Orchestrator Integration**: Detect-secrets not integrated in security-check.sh
6. **Report Integration**: Detect-secrets not integrated in HTML report generator
7. **False Positive Handling**: No detect-secrets entries in fp_whitelist.json
8. **Environment Variables**: No DETECT_SECRETS_CONFIG_PATH in Dockerfile

#### Architecture Consistency Verified:
- ✅ Follows existing tool integration patterns (GitLeaks, TruffleHog)
- ✅ Compatible with current Docker-based architecture
- ✅ Aligns with code scan mode (SCAN_TYPE="code")
- ✅ Uses established environment variable patterns
- ✅ Compatible with existing HTML report structure
- ✅ Python-based processor matches existing Python processors
- ✅ LLM integration pattern matches existing processors

### ✅ Task Splitting Assessment Complete
#### Current Task Analysis:
- **Estimated Time**: 6 hours (within 8-hour limit)
- **Files to Modify**: 4 files (within 10-file limit)
- **Files to Create**: 3 files (within 10-file limit)
- **Implementation Phases**: 3 phases (within 5-phase limit)
- **Complexity**: Low-Medium (follow existing GitLeaks/TruffleHog pattern)

#### Splitting Recommendation: **NO SPLITTING REQUIRED**
- Task size is appropriate (6 hours)
- File count is manageable (7 total files)
- Phase count is optimal (3 phases)
- Dependencies are clear and sequential
- Each phase is independently testable
- Risk level is low (follows established patterns)

#### Phase Validation:
- **Phase 1**: Foundation Setup (2h) - ✅ Appropriate size
- **Phase 2**: Core Implementation (2h) - ✅ Appropriate size
- **Phase 3**: Integration & Testing (2h) - ✅ Appropriate size

## 🤖 AI Auto-Implementation Instructions
- **source_type**: 'markdown_doc'
- **source_path**: 'docs/09_roadmap/pending/high/security/detect-secrets-integration/detect-secrets-integration-implementation.md'
- **category**: 'security'
- **automation_level**: 'semi_auto'
- **confirmation_required**: true
- **max_attempts**: 3
- **git_branch_required**: true
- **new_chat_required**: true

