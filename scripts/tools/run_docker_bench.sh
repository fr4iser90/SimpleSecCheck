#!/bin/bash
# Docker Bench Docker Daemon Compliance Testing Script for SimpleSecCheck

# Expected Environment Variables:
# DOCKER_BENCH_CONFIG_PATH: Path to Docker Bench configuration file
# RESULTS_DIR: Directory to store results (e.g., /SimpleSecCheck/results)
# LOG_FILE: Path to the main log file (e.g., /SimpleSecCheck/logs/security-check.log)

RESULTS_DIR="${RESULTS_DIR:-/SimpleSecCheck/results}"
LOG_FILE="${LOG_FILE:-/SimpleSecCheck/logs/security-check.log}"
DOCKER_BENCH_CONFIG_PATH="${DOCKER_BENCH_CONFIG_PATH:-/SimpleSecCheck/docker-bench/config.yaml}"
SUMMARY_TXT="$RESULTS_DIR/security-summary.txt"

mkdir -p "$RESULTS_DIR" "$(dirname "$LOG_FILE")"

echo "[run_docker_bench.sh] Initializing Docker Bench scan..." | tee -a "$LOG_FILE"


if command -v docker-bench-security &>/dev/null; then
  echo "[run_docker_bench.sh][Docker Bench] Running Docker daemon compliance scan..." | tee -a "$LOG_FILE"
  
  DOCKER_BENCH_JSON="$RESULTS_DIR/docker-bench.json"
  DOCKER_BENCH_TEXT="$RESULTS_DIR/docker-bench.txt"
  
  # Run Docker Bench scan with JSON output
  echo "[run_docker_bench.sh][Docker Bench] Running compliance scan..." | tee -a "$LOG_FILE"
  
  # Check if Docker socket is accessible
  if [ ! -S /var/run/docker.sock ]; then
    echo "[run_docker_bench.sh][Docker Bench][ERROR] Docker socket /var/run/docker.sock not accessible." | tee -a "$LOG_FILE"
    echo "[run_docker_bench.sh][Docker Bench][ERROR] Skipping Docker Bench scan." | tee -a "$LOG_FILE"
    exit 1
  fi
  
  # Run docker-bench-security from its directory with JSON and text outputs
  cd /opt/docker-bench-security
  ./docker-bench-security.sh > "$DOCKER_BENCH_TEXT" 2>/dev/null || {
    echo "[run_docker_bench.sh][Docker Bench] Text report generation failed." >> "$LOG_FILE"
  }
  cd "$(dirname "$0")/../.."
  
  # Convert text output to JSON format (basic conversion)
  if [ -f "$DOCKER_BENCH_TEXT" ]; then
    # Parse text output and convert to JSON
    python3 - "$DOCKER_BENCH_TEXT" > "$DOCKER_BENCH_JSON" 2>/dev/null << 'PYEOF'
import json
import re
import sys

findings = []
current_check = {}

try:
    txt_path = sys.argv[1]
    with open(txt_path, 'r') as f:
        lines = f.readlines()
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Parse PASS, WARN, INFO, NOTE lines (with ANSI codes)
        pass_match = re.search(r'\[PASS\][\x1b\[\d+m\[0m]*\s*(.+?)(?:\x1b\[|$)', line)
        if pass_match:
            findings.append({
                'test': pass_match.group(1).strip(),
                'result': 'PASS',
                'group': 'Docker Bench Security'
            })
            continue
            
        warn_match = re.search(r'\[WARN\][\x1b\[\d+m\[0m]*\s*(.+?)(?:\x1b\[|$)', line)
        if warn_match:
            findings.append({
                'test': warn_match.group(1).strip(),
                'result': 'WARN',
                'group': 'Docker Bench Security'
            })
            continue
            
        info_match = re.search(r'\[INFO\][\x1b\[\d+m\[0m]*\s*(.+?)(?:\x1b\[|$)', line)
        if info_match:
            findings.append({
                'test': info_match.group(1).strip(),
                'result': 'INFO',
                'group': 'Docker Bench Security'
            })
            continue
            
        note_match = re.search(r'\[NOTE\][\x1b\[\d+m\[0m]*\s*(.+?)(?:\x1b\[|$)', line)
        if note_match:
            findings.append({
                'test': note_match.group(1).strip(),
                'result': 'NOTE',
                'group': 'Docker Bench Security'
            })
            continue
except Exception as e:
    pass

output = {
    'benchmark': 'Docker Bench Security',
    'tests': [{
        'group': 'Docker Compliance',
        'summary': {},
        'checks': findings
    }]
}

print(json.dumps(output, indent=2))
PYEOF
  fi

  if [ -f "$DOCKER_BENCH_JSON" ] || [ -f "$DOCKER_BENCH_TEXT" ]; then
    echo "[run_docker_bench.sh][Docker Bench] Report(s) successfully generated:" | tee -a "$LOG_FILE"
    [ -f "$DOCKER_BENCH_JSON" ] && echo "  - $DOCKER_BENCH_JSON" | tee -a "$LOG_FILE"
    [ -f "$DOCKER_BENCH_TEXT" ] && echo "  - $DOCKER_BENCH_TEXT" | tee -a "$LOG_FILE"
    echo "[Docker Bench] Docker daemon compliance scan complete." >> "$SUMMARY_TXT"
    exit 0
  else
    echo "[run_docker_bench.sh][Docker Bench][ERROR] No Docker Bench report was generated!" | tee -a "$LOG_FILE"
    exit 1
  fi
else
  echo "[run_docker_bench.sh][ERROR] docker-bench-security not found, skipping Docker daemon compliance scan." | tee -a "$LOG_FILE"
  exit 1
fi

