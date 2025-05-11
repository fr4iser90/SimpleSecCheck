from flask import Flask, send_from_directory, request, jsonify
import subprocess
import os
import threading

app = Flask(__name__)

SCAN_LOCK = threading.Lock()
SCAN_STATUS = {'status': 'idle'}
RESULTS_DIR = '/results'

@app.route('/')
def serve_dashboard():
    summary_path = os.path.join(RESULTS_DIR, 'security-summary.html')
    if os.path.exists(summary_path):
        return send_from_directory(RESULTS_DIR, 'security-summary.html')
    else:
        return send_from_directory(os.path.dirname(__file__), 'loading.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(RESULTS_DIR, filename)

@app.route('/scan', methods=['POST'])
def trigger_scan():
    if not SCAN_LOCK.acquire(blocking=False):
        return jsonify({'status': 'error', 'message': 'Scan already running'}), 409
    def run_scan():
        try:
            SCAN_STATUS['status'] = 'running'
            subprocess.run(['./scripts/security-check.sh'], check=False)
        finally:
            SCAN_STATUS['status'] = 'idle'
            SCAN_LOCK.release()
    threading.Thread(target=run_scan, daemon=True).start()
    return jsonify({'status': 'success', 'message': 'Scan started'})

@app.route('/status')
def scan_status():
    lock_file = os.path.join(RESULTS_DIR, '.scan-running')
    if os.path.exists(lock_file):
        return jsonify({'status': 'running'})
    return jsonify({'status': 'idle'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 