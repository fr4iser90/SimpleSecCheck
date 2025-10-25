# Phase 3: Integration and Testing

## 📋 Phase Overview
- **Phase Number**: 3
- **Phase Name**: Integration and Testing
- **Estimated Time**: 2 hours
- **Status**: Planning
- **Progress**: 0%

## 🎯 Phase Objectives
Integrate CodeQL with SimpleSecCheck orchestrator and perform complete testing.

## 📊 Detailed Tasks

### Task 3.1: Main Integration (1 hour)
- [ ] **3.1.1** Update main `scripts/security-check.sh` orchestrator
- [ ] **3.1.2** Add CodeQL tool execution to orchestrator
- [ ] **3.1.3** Update HTML report generation
- [ ] **3.1.4** Test orchestrator integration

### Task 3.2: Complete Testing (1 hour)
- [ ] **3.2.1** Test complete CodeQL integration
- [ ] **3.2.2** Test HTML report generation
- [ ] **3.2.3** Test error handling
- [ ] **3.2.4** Update documentation

## 🔧 Technical Implementation Details

### Updated security-check.sh Orchestrator
```bash
#!/bin/bash
# SimpleSecCheck - Main Security Check Orchestrator (UPDATED)
# Purpose: Coordinates various security scanning tools including CodeQL

# ... existing code ...

# === Tool Execution ===
log_message "Starting security scan..."

# SAST Tools
log_message "Running SAST tools..."
"$TOOL_SCRIPTS_DIR/run_semgrep.sh" &
"$TOOL_SCRIPTS_DIR/run_codeql.sh" &  # NEW: CodeQL integration
"$TOOL_SCRIPTS_DIR/run_bandit.sh" &
"$TOOL_SCRIPTS_DIR/run_eslint_security.sh" &
"$TOOL_SCRIPTS_DIR/run_brakeman.sh" &

# DAST Tools
log_message "Running DAST tools..."
"$TOOL_SCRIPTS_DIR/run_zap.sh" &

# Dependency Scanning Tools
log_message "Running dependency scanning tools..."
"$TOOL_SCRIPTS_DIR/run_trivy.sh" &

# Wait for all tools to complete
wait

log_message "All security tools completed. Generating consolidated report..."

# ... existing report generation code ...
```

### Updated HTML Report Generation
```python
def generate_html_report(results_dir):
    """Generate HTML report with CodeQL results"""
    
    # Process all tool results
    all_results = []
    
    # SAST Tools
    all_results.extend(process_semgrep_results(results_dir))
    all_results.extend(process_codeql_results(results_dir))  # NEW: CodeQL results
    all_results.extend(process_bandit_results(results_dir))
    all_results.extend(process_eslint_security_results(results_dir))
    all_results.extend(process_brakeman_results(results_dir))
    
    # DAST Tools
    all_results.extend(process_zap_results(results_dir))
    
    # Dependency Scanning Tools
    all_results.extend(process_trivy_results(results_dir))
    
    # Generate HTML report
    return generate_html_report(all_results)
```

### Updated html_utils.py
```python
def format_codeql_findings(findings):
    """Format CodeQL findings for HTML display"""
    formatted_findings = []
    
    for finding in findings:
        formatted_finding = {
            'tool': 'CodeQL',
            'type': 'SAST',
            'severity': finding['severity'],
            'title': finding['title'],
            'description': finding['description'],
            'file': finding['file'],
            'line': finding['line'],
            'rule_id': finding['rule_id'],
            'solution': finding['solution'],
            'category': 'Semantic Code Analysis'
        }
        formatted_findings.append(formatted_finding)
    
    return formatted_findings
```

## 🧪 Testing Strategy

### Unit Tests
- [ ] Test orchestrator integration
- [ ] Test HTML report generation
- [ ] Test error handling
- [ ] Test configuration loading

### Integration Tests
- [ ] Test complete CodeQL workflow
- [ ] Test with sample code
- [ ] Test result aggregation
- [ ] Test HTML report generation

### E2E Tests
- [ ] Test complete security scan with CodeQL
- [ ] Test error scenarios
- [ ] Test performance
- [ ] Test user experience

## 📝 Documentation Updates

### Code Documentation
- [ ] Update README with CodeQL functionality
- [ ] Update CHANGELOG with CodeQL integration
- [ ] Document CodeQL configuration options
- [ ] Document troubleshooting guide

### User Documentation
- [ ] CodeQL usage guide
- [ ] Configuration examples
- [ ] Best practices
- [ ] Common issues and solutions

## 🚀 Success Criteria
- [ ] CodeQL integrated with orchestrator
- [ ] HTML reports include CodeQL results
- [ ] Complete integration tested
- [ ] Performance within acceptable limits
- [ ] Documentation complete and accurate
- [ ] All tests passing

## 🔄 Project Completion
After completing Phase 3, the CodeQL Integration will be complete with:
- **CodeQL CLI** installed and functional
- **CodeQL Script** created and tested
- **CodeQL Processor** created and tested
- **Complete Integration** with SimpleSecCheck
- **HTML Reports** including CodeQL results
- **Full Documentation** and user guides
- **Production Ready** deployment
