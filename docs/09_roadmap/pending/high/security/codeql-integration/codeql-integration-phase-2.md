# Phase 2: CodeQL Script and Processor

## 📋 Phase Overview
- **Phase Number**: 2
- **Phase Name**: CodeQL Script and Processor
- **Estimated Time**: 2 hours
- **Status**: Planning
- **Progress**: 0%

## 🎯 Phase Objectives
Create CodeQL execution script, result processor, and configuration files.

## 📊 Detailed Tasks

### Task 2.1: CodeQL Script Creation (1 hour)
- [ ] **2.1.1** Create `scripts/tools/run_codeql.sh` script
- [ ] **2.1.2** Implement CodeQL execution logic
- [ ] **2.1.3** Add error handling and logging
- [ ] **2.1.4** Test CodeQL script execution

### Task 2.2: CodeQL Processor Creation (1 hour)
- [ ] **2.2.1** Create `scripts/codeql_processor.py` processor
- [ ] **2.2.2** Implement CodeQL result processing
- [ ] **2.2.3** Add result formatting for HTML reports
- [ ] **2.2.4** Test CodeQL processor functionality

## 🔧 Technical Implementation Details

### CodeQL Script Template
```bash
#!/bin/bash
# Individual CodeQL Scan Script for SimpleSecCheck Plugin System

TARGET_PATH="${TARGET_PATH:-/target}"
RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
CODEQL_CONFIG_PATH="${CODEQL_CONFIG_PATH:-/SimpleSecCheck/conf/codeql_config.json}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_codeql.sh] Initializing CodeQL scan..." | tee -a "$LOG_FILE"

if command -v codeql &>/dev/null; then
  echo "[run_codeql.sh][CodeQL] Running semantic code analysis on $TARGET_PATH..." | tee -a "$LOG_FILE"
  
  CODEQL_JSON="$RESULTS_DIR/codeql.json"
  CODEQL_TEXT="$RESULTS_DIR/codeql.txt"
  
  # Run CodeQL with configuration
  codeql database create --language=python --source-root="$TARGET_PATH" /tmp/codeql-db 2>>"$LOG_FILE" || {
    echo "[run_codeql.sh][CodeQL] Database creation failed." >> "$LOG_FILE"
  }
  
  codeql database analyze /tmp/codeql-db --format=sarif-latest -o "$CODEQL_JSON" 2>>"$LOG_FILE" || {
    echo "[run_codeql.sh][CodeQL] JSON report generation failed." >> "$LOG_FILE"
  }
  
  # Generate text report
  codeql database analyze /tmp/codeql-db --format=text -o "$CODEQL_TEXT" 2>>"$LOG_FILE" || {
    echo "[run_codeql.sh][CodeQL] Text report generation failed." >> "$LOG_FILE"
  }

  if [ -f "$CODEQL_JSON" ] || [ -f "$CODEQL_TEXT" ]; then
    echo "[run_codeql.sh][CodeQL] Report(s) successfully generated:" | tee -a "$LOG_FILE"
    [ -f "$CODEQL_JSON" ] && echo "  - $CODEQL_JSON" | tee -a "$LOG_FILE"
    [ -f "$CODEQL_TEXT" ] && echo "  - $CODEQL_TEXT" | tee -a "$LOG_FILE"
    echo "[CodeQL] Semantic code analysis complete." >> "$SUMMARY_TXT"
    exit 0
  else
    echo "[run_codeql.sh][CodeQL][ERROR] No CodeQL report was generated!" | tee -a "$LOG_FILE"
    exit 1
  fi
else
  echo "[run_codeql.sh][ERROR] codeql not found, skipping semantic code analysis." | tee -a "$LOG_FILE"
  exit 1
fi
```

### CodeQL Processor Template
```python
#!/usr/bin/env python3
"""
CodeQL Result Processor for SimpleSecCheck
Processes CodeQL scan results and integrates with HTML report generation
"""

import json
import os
import sys
from pathlib import Path

def process_codeql_results(results_dir):
    """Process CodeQL scan results and return structured data"""
    codeql_json_path = os.path.join(results_dir, 'codeql.json')
    
    if not os.path.exists(codeql_json_path):
        return None
    
    try:
        with open(codeql_json_path, 'r') as f:
            codeql_data = json.load(f)
        
        # Process CodeQL SARIF data structure
        processed_results = {
            'tool': 'CodeQL',
            'type': 'SAST',
            'findings': [],
            'summary': {
                'total_findings': 0,
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0,
                'info': 0
            }
        }
        
        # Process findings from SARIF format
        for run in codeql_data.get('runs', []):
            for result in run.get('results', []):
                # Map SARIF severity to SimpleSecCheck severity
                severity_mapping = {
                    'error': 'critical',
                    'warning': 'high',
                    'note': 'medium',
                    'info': 'low'
                }
                
                severity = severity_mapping.get(result.get('level', 'info'), 'info')
                
                processed_finding = {
                    'severity': severity,
                    'title': result.get('message', {}).get('text', 'Unknown Issue'),
                    'description': result.get('message', {}).get('text', ''),
                    'file': result.get('locations', [{}])[0].get('physicalLocation', {}).get('fileLocation', {}).get('uri', ''),
                    'line': result.get('locations', [{}])[0].get('physicalLocation', {}).get('region', {}).get('startLine', 0),
                    'rule_id': result.get('ruleId', ''),
                    'solution': 'Review and fix the identified issue'
                }
                
                processed_results['findings'].append(processed_finding)
                processed_results['summary']['total_findings'] += 1
                processed_results['summary'][severity] += 1
        
        return processed_results
        
    except Exception as e:
        print(f"Error processing CodeQL results: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 codeql_processor.py <results_dir>")
        sys.exit(1)
    
    results_dir = sys.argv[1]
    results = process_codeql_results(results_dir)
    
    if results:
        print(json.dumps(results, indent=2))
    else:
        print("No CodeQL results to process")
        sys.exit(1)
```

### CodeQL Configuration Template
```json
{
  "codeql": {
    "database": {
      "language": "python",
      "source_root": "/target",
      "output_path": "/tmp/codeql-db"
    },
    "analysis": {
      "format": "sarif-latest",
      "output_path": "/SimpleSecCheck/results/codeql.json",
      "queries": [
        "security-and-quality",
        "security-extended",
        "security-experimental"
      ]
    },
    "logging": {
      "level": "info",
      "file": "/SimpleSecCheck/logs/codeql.log"
    }
  }
}
```

## 🧪 Testing Strategy

### Unit Tests
- [ ] Test CodeQL script execution
- [ ] Test CodeQL processor with sample data
- [ ] Test configuration file loading
- [ ] Test error handling

### Integration Tests
- [ ] Test CodeQL script with sample code
- [ ] Test CodeQL processor integration
- [ ] Test result file generation
- [ ] Test HTML report generation

## 📝 Documentation Updates

### Code Documentation
- [ ] Document CodeQL script functionality
- [ ] Document CodeQL processor functionality
- [ ] Document configuration options
- [ ] Document troubleshooting

### User Documentation
- [ ] CodeQL script usage guide
- [ ] CodeQL processor usage guide
- [ ] Configuration examples
- [ ] Common issues and solutions

## 🚀 Success Criteria
- [ ] CodeQL script created and functional
- [ ] CodeQL processor created and functional
- [ ] Configuration file created
- [ ] All components tested
- [ ] Documentation complete

## 🔄 Next Phase
After completing Phase 2, proceed to Phase 3: Integration and Testing
