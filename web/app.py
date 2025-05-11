from flask import Flask, send_from_directory, request, jsonify
import subprocess
import os
import threading
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

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

@app.route('/llm/chat', methods=['POST'])
def llm_chat():
    data = request.get_json(force=True)
    provider = (data.get('provider') or os.environ.get('LLM_PROVIDER', 'openai')).lower()
    api_key = data.get('api_key') or ''
    model = data.get('model') or ''
    prompt = data.get('prompt') or ''
    # Dynamische LLM-Client-Auswahl
    llm_config = {
        'OPENAI_API_KEY': api_key if provider == 'openai' and api_key else os.environ.get('OPENAI_API_KEY', ''),
        'OPENAI_MODEL': model if provider == 'openai' and model else os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo'),
        'OPENAI_ENDPOINT': os.environ.get('OPENAI_ENDPOINT', 'https://api.openai.com/v1/chat/completions'),
        'GEMINI_API_KEY': api_key if provider == 'gemini' and api_key else os.environ.get('GEMINI_API_KEY', ''),
        'GEMINI_MODEL': model if provider == 'gemini' and model else os.environ.get('GEMINI_MODEL', 'gemini-pro'),
        'GEMINI_ENDPOINT': os.environ.get('GEMINI_ENDPOINT', 'https://generativelanguage.googleapis.com/v1beta/models'),
        'HF_API_KEY': api_key if provider == 'huggingface' and api_key else os.environ.get('HF_API_KEY', ''),
        'HF_MODEL': model if provider == 'huggingface' and model else os.environ.get('HF_MODEL', 'bigcode/starcoder2-15b'),
        'HF_ENDPOINT': os.environ.get('HF_ENDPOINT', 'https://api-inference.huggingface.co/models'),
        'GROQ_API_KEY': api_key if provider == 'groq' and api_key else os.environ.get('GROQ_API_KEY', ''),
        'GROQ_MODEL': model if provider == 'groq' and model else os.environ.get('GROQ_MODEL', 'llama3-70b-8192'),
        'GROQ_ENDPOINT': os.environ.get('GROQ_ENDPOINT', 'https://api.groq.com/openai/v1/chat/completions'),
        'MISTRAL_API_KEY': api_key if provider == 'mistral' and api_key else os.environ.get('MISTRAL_API_KEY', ''),
        'MISTRAL_MODEL': model if provider == 'mistral' and model else os.environ.get('MISTRAL_MODEL', 'mistral-medium'),
        'MISTRAL_ENDPOINT': os.environ.get('MISTRAL_ENDPOINT', 'https://api.mistral.ai/v1/chat/completions'),
        'ANTHROPIC_API_KEY': api_key if provider == 'anthropic' and api_key else os.environ.get('ANTHROPIC_API_KEY', ''),
        'ANTHROPIC_MODEL': model if provider == 'anthropic' and model else os.environ.get('ANTHROPIC_MODEL', 'claude-3-opus-20240229'),
        'ANTHROPIC_ENDPOINT': os.environ.get('ANTHROPIC_ENDPOINT', 'https://api.anthropic.com/v1/messages'),
    }
    try:
        if provider == 'openai':
            from llm.llm_client_openai import OpenAILLMClient
            llm_client = OpenAILLMClient(llm_config)
        elif provider == 'gemini':
            from llm.llm_client_gemini import GeminiLLMClient
            llm_client = GeminiLLMClient(llm_config)
        elif provider == 'huggingface':
            from llm.llm_client_huggingface import HuggingFaceLLMClient
            llm_client = HuggingFaceLLMClient(llm_config)
        elif provider == 'groq':
            from llm.llm_client_groq import GroqLLMClient
            llm_client = GroqLLMClient(llm_config)
        elif provider == 'mistral':
            from llm.llm_client_mistral import MistralLLMClient
            llm_client = MistralLLMClient(llm_config)
        elif provider == 'anthropic':
            from llm.llm_client_anthropic import AnthropicLLMClient
            llm_client = AnthropicLLMClient(llm_config)
        else:
            from llm.llm_client_openai import OpenAILLMClient
            llm_client = OpenAILLMClient(llm_config)
        response = llm_client.query(prompt)
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'response': f'[LLM error: {str(e)}]'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 