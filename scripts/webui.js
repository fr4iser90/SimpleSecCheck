// webui.js: SecuLite WebUI Features

let scanInProgress = false;
let autoRefreshInterval = null;

function setScanStatus(msg, isLoading = false) {
  const el = document.getElementById('scan-status');
  if (el) {
    el.innerText = msg;
    el.style.color = isLoading ? '#e6b800' : '#007bff';
  }
  const scanBtn = document.getElementById('scan-btn');
  if (scanBtn) scanBtn.disabled = isLoading;
  const spinner = document.getElementById('scan-spinner');
  if (spinner) spinner.style.display = isLoading ? 'inline-block' : 'none';
}

function updateScanStatus(autoRefresh = false) {
  fetch('/status')
    .then(r => r.json())
    .then(data => {
      if (data.status === 'running') {
        setScanStatus('Scan running...', true);
        if (autoRefresh && !autoRefreshInterval) {
          autoRefreshInterval = setInterval(() => updateScanStatus(true), 2000);
        }
      } else {
        setScanStatus('Idle', false);
        if (autoRefreshInterval) {
          clearInterval(autoRefreshInterval);
          autoRefreshInterval = null;
          // Auto-refresh the dashboard after scan completion
          window.location.reload();
        }
      }
    })
    .catch(() => setScanStatus('Status unavailable.', false));
}

function triggerScan() {
  setScanStatus('Starting scan...', true);
  fetch('/scan', {method: 'POST'})
    .then(r => r.json())
    .then(data => {
      if (data.status === 'success') {
        setScanStatus('Scan started!', true);
        updateScanStatus(true);
      } else if (data.status === 'error') {
        setScanStatus('Scan already running!', true);
      } else {
        setScanStatus('Failed to start scan.', false);
      }
    })
    .catch(() => setScanStatus('Connection error.', false));
}

// LLM Chat UI
const llmProviders = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'gemini', label: 'Gemini' },
  { value: 'huggingface', label: 'HuggingFace' },
  { value: 'groq', label: 'Groq' },
  { value: 'mistral', label: 'Mistral' },
  { value: 'anthropic', label: 'Anthropic' },
];

function createLLMChatUI() {
  const container = document.createElement('div');
  container.id = 'llm-chat-container';
  container.innerHTML = `
    <div id="llm-chat-header">LLM Chat</div>
    <div id="llm-chat-controls">
      <select id="llm-provider-select">
        ${llmProviders.map(p => `<option value="${p.value}">${p.label}</option>`).join('')}
      </select>
      <input id="llm-api-key" type="password" placeholder="API Key (optional)" />
      <input id="llm-model" type="text" placeholder="Model (optional)" />
    </div>
    <div id="llm-chat-messages"></div>
    <textarea id="llm-chat-input" placeholder="Ask the LLM..."></textarea>
    <button id="llm-chat-send">Send</button>
  `;
  document.body.appendChild(container);

  document.getElementById('llm-chat-send').onclick = async function() {
    const provider = document.getElementById('llm-provider-select').value;
    const apiKey = document.getElementById('llm-api-key').value;
    const model = document.getElementById('llm-model').value;
    const prompt = document.getElementById('llm-chat-input').value;
    if (!prompt) return;
    const msgDiv = document.getElementById('llm-chat-messages');
    msgDiv.innerHTML += `<div class='user-msg'>${prompt}</div>`;
    document.getElementById('llm-chat-input').value = '';
    // Send to backend
    const res = await fetch('/llm/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider, api_key: apiKey, model, prompt })
    });
    const data = await res.json();
    msgDiv.innerHTML += `<div class='ai-msg'>${data.response || '[No response]'}</div>`;
    msgDiv.scrollTop = msgDiv.scrollHeight;
  };
}

window.addEventListener('DOMContentLoaded', function() {
  const scanBtn = document.getElementById('scan-btn');
  const statusBtn = document.getElementById('refresh-status-btn');
  if (scanBtn) scanBtn.onclick = triggerScan;
  if (statusBtn) statusBtn.onclick = () => updateScanStatus(false);
  // Add spinner if not present
  if (!document.getElementById('scan-spinner')) {
    const spinner = document.createElement('span');
    spinner.id = 'scan-spinner';
    spinner.style.display = 'none';
    spinner.innerHTML = ' <span style="display:inline-block;width:16px;height:16px;border:2px solid #eee;border-top:2px solid #007bff;border-radius:50%;animation:spin 1s linear infinite;vertical-align:middle;"></span>';
    const statusEl = document.getElementById('scan-status');
    if (statusEl) statusEl.parentNode.insertBefore(spinner, statusEl.nextSibling);
  }
  updateScanStatus(false);
  createLLMChatUI();
}); 