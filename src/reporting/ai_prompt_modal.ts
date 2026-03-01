// AI Prompt Modal for standalone HTML reports (when opened directly, not in WebUI)

type Language = 'english' | 'chinese' | 'german';

interface PromptData {
  prompt: string;
  findings_count: number;
  language: string;
}

let aiPromptModal: HTMLDivElement | null = null;
let currentPrompt: string = '';
let currentLanguage: Language = 'english';
let currentPolicyPath: string = 'config/finding-policy.json';

function openAIPromptModal(): void {
  if (!aiPromptModal) {
    // Create modal if it doesn't exist
    aiPromptModal = document.createElement('div');
    aiPromptModal.id = 'ai-prompt-modal';
    aiPromptModal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.8);
      backdrop-filter: blur(5px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 10000;
      padding: 2rem;
    `;
    aiPromptModal.innerHTML = `
      <div style="
        max-width: 900px;
        width: 100%;
        max-height: 90vh;
        background: var(--glass-bg-dark);
        backdrop-filter: blur(20px);
        border-radius: 16px;
        border: 1px solid var(--glass-border-dark);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        display: flex;
        flex-direction: column;
        overflow: hidden;
      ">
        <div style="
          padding: 1.5rem;
          border-bottom: 1px solid var(--glass-border-dark);
          display: flex;
          justify-content: space-between;
          align-items: center;
        ">
          <h2 style="margin: 0;">🤖 AI Prompt Generator</h2>
          <button onclick="closeAIPromptModal()" style="
            background: transparent;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: var(--text-dark);
            padding: 0.25rem 0.5rem;
            line-height: 1;
          ">✕</button>
        </div>
        <div style="
          flex: 1;
          overflow: hidden;
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
          padding: 1.5rem;
        ">
          <div style="flex: 1; display: flex; flex-direction: column; min-height: 0;">
            <label style="margin-bottom: 0.5rem; font-weight: 600;">📋 Prompt Preview:</label>
            <div id="ai-prompt-loading" style="
              flex: 1;
              display: none;
              align-items: center;
              justify-content: center;
              padding: 2rem;
              background: var(--glass-bg-dark);
              border-radius: 8px;
              border: 1px solid var(--glass-border-dark);
            ">
              <div style="opacity: 0.7;">⏳ Loading prompt...</div>
            </div>
            <div id="ai-prompt-error" style="
              display: none;
              padding: 1rem;
              background: rgba(220, 53, 69, 0.2);
              border: 1px solid #dc3545;
              border-radius: 8px;
              color: #dc3545;
            "></div>
            <textarea
              id="ai-prompt-textarea"
              style="
                flex: 1;
                min-height: 400px;
                background: #000;
                border: 1px solid var(--glass-border-dark);
                border-radius: 8px;
                padding: 1rem;
                color: #f8f9fa;
                font-family: 'Courier New', monospace;
                font-size: 0.9rem;
                resize: vertical;
                white-space: pre-wrap;
                word-wrap: break-word;
                display: none;
              "
              placeholder="Prompt will appear here..."
            ></textarea>
          </div>
          <div style="
            background: var(--glass-bg-dark);
            border: 1px solid var(--glass-border-dark);
            border-radius: 8px;
            padding: 1rem;
          ">
            <div style="margin-bottom: 1rem; font-weight: 600;">⚙️ Settings:</div>
            <div style="display: flex; flex-direction: column; gap: 1rem;">
              <div>
                <label style="margin-bottom: 0.5rem; display: block;">Language:</label>
                <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                  <button onclick="setAIPromptLanguage('english')" id="lang-english" style="
                    padding: 0.5rem 1rem;
                    border-radius: 8px;
                    cursor: pointer;
                    border: 1px solid var(--glass-border-dark);
                    background: var(--glass-bg-dark);
                    color: var(--text-dark);
                  ">🇬🇧 English</button>
                  <button onclick="setAIPromptLanguage('chinese')" id="lang-chinese" style="
                    padding: 0.5rem 1rem;
                    border-radius: 8px;
                    cursor: pointer;
                    border: 1px solid var(--glass-border-dark);
                    background: var(--glass-bg-dark);
                    color: var(--text-dark);
                  ">🇨🇳 中文</button>
                  <button onclick="setAIPromptLanguage('german')" id="lang-german" style="
                    padding: 0.5rem 1rem;
                    border-radius: 8px;
                    cursor: pointer;
                    border: 1px solid var(--glass-border-dark);
                    background: var(--glass-bg-dark);
                    color: var(--text-dark);
                  ">🇩🇪 Deutsch</button>
                </div>
              </div>
              <div>
                <label style="margin-bottom: 0.5rem; display: block;">Policy Path:</label>
                <input
                  type="text"
                  id="ai-prompt-policy-path"
                  value="config/finding-policy.json"
                  onchange="updateAIPromptPolicyPath(this.value)"
                  placeholder="config/finding-policy.json"
                  style="
                    width: 100%;
                    padding: 0.75rem;
                    background: var(--glass-bg-dark);
                    border: 1px solid var(--glass-border-dark);
                    border-radius: 8px;
                    color: var(--text-dark);
                  "
                />
              </div>
            </div>
          </div>
          <div id="ai-prompt-stats" style="
            display: none;
            padding: 0.75rem;
            background: var(--glass-bg-dark);
            border: 1px solid var(--glass-border-dark);
            border-radius: 8px;
            font-size: 0.9rem;
            opacity: 0.8;
          "></div>
          <div style="display: flex; gap: 1rem; justify-content: flex-end;">
            <button onclick="closeAIPromptModal()" style="
              background: var(--glass-bg-dark);
              border: 1px solid var(--glass-border-dark);
              padding: 0.75rem 1.5rem;
              border-radius: 8px;
              color: var(--text-dark);
              cursor: pointer;
            ">❌ Cancel</button>
            <button onclick="copyAIPrompt()" id="ai-prompt-copy-btn" style="
              padding: 0.75rem 1.5rem;
              border-radius: 8px;
              background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
              border: none;
              color: white;
              cursor: pointer;
              font-weight: 600;
            ">📋 Copy</button>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(aiPromptModal);
    
    // Close modal on overlay click
    aiPromptModal.addEventListener('click', (e: MouseEvent) => {
      if (e.target === aiPromptModal) {
        closeAIPromptModal();
      }
    });
  }
  if (aiPromptModal) {
    aiPromptModal.style.display = 'flex';
  }
  loadAIPrompt();
}

function closeAIPromptModal(): void {
  if (aiPromptModal) {
    aiPromptModal.style.display = 'none';
  }
}

function setAIPromptLanguage(lang: Language): void {
  currentLanguage = lang;
  // Update button styles
  const languages: Language[] = ['english', 'chinese', 'german'];
  languages.forEach((l: Language) => {
    const btn = document.getElementById(`lang-${l}`);
    if (btn) {
      if (l === lang) {
        btn.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
        btn.style.borderColor = '#667eea';
        btn.style.fontWeight = '600';
      } else {
        btn.style.background = 'var(--glass-bg-dark)';
        btn.style.borderColor = 'var(--glass-border-dark)';
        btn.style.fontWeight = '400';
      }
    }
  });
  loadAIPrompt();
}

function updateAIPromptPolicyPath(path: string): void {
  currentPolicyPath = path;
  loadAIPrompt();
}

async function loadAIPrompt(): Promise<void> {
  const loading = document.getElementById('ai-prompt-loading') as HTMLDivElement | null;
  const error = document.getElementById('ai-prompt-error') as HTMLDivElement | null;
  const textarea = document.getElementById('ai-prompt-textarea') as HTMLTextAreaElement | null;
  const stats = document.getElementById('ai-prompt-stats') as HTMLDivElement | null;
  
  if (!loading || !error || !textarea || !stats) return;
  
  loading.style.display = 'flex';
  error.style.display = 'none';
  textarea.style.display = 'none';
  stats.style.display = 'none';
  
  try {
    // Try to get API URL - if in WebUI, use relative path, otherwise try to detect
    let apiUrl: string = '';
    if (window.location.origin.includes('localhost:8080') || window.location.origin.includes('127.0.0.1:8080')) {
      apiUrl = window.location.origin;
    } else {
      // For standalone reports, try common WebUI ports
      apiUrl = 'http://localhost:8080';
    }
    
    const response = await fetch(`${apiUrl}/api/scan/ai-prompt?language=${currentLanguage}&policy_path=${encodeURIComponent(currentPolicyPath)}`);
    if (response.ok) {
      const data: PromptData = await response.json();
      currentPrompt = data.prompt;
      textarea.value = data.prompt;
      textarea.style.display = 'block';
      loading.style.display = 'none';
      
      // Show stats
      const tokens = Math.ceil(data.prompt.length / (currentLanguage === 'chinese' ? 2 : 4));
      stats.textContent = `📊 ${data.findings_count} findings | ~${tokens.toLocaleString()} tokens`;
      stats.style.display = 'block';
    } else {
      const errorText = await response.text();
      error.textContent = `Failed to load prompt: ${errorText}`;
      error.style.display = 'block';
      loading.style.display = 'none';
    }
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : 'Unknown error';
    error.textContent = `Error: ${errorMessage}. Make sure the WebUI is running on http://localhost:8080`;
    error.style.display = 'block';
    loading.style.display = 'none';
  }
}

async function copyAIPrompt(): Promise<void> {
  const textarea = document.getElementById('ai-prompt-textarea') as HTMLTextAreaElement | null;
  const btn = document.getElementById('ai-prompt-copy-btn') as HTMLButtonElement | null;
  
  if (!textarea || !textarea.value || !btn) return;
  
  try {
    await navigator.clipboard.writeText(textarea.value);
    btn.textContent = '✓ Copied!';
    setTimeout(() => {
      btn.textContent = '📋 Copy';
    }, 2000);
  } catch (err) {
    alert('Failed to copy to clipboard');
  }
}

function generateAIPrompt(): void {
  // If in iframe (WebUI), send message to parent
  if (window.parent && window.parent !== window) {
    window.parent.postMessage({ type: 'OPEN_AI_PROMPT_MODAL' }, '*');
  } else {
    // If standalone (direct HTML file), open modal directly
    openAIPromptModal();
  }
}

// Make functions globally available for onclick handlers
(window as any).openAIPromptModal = openAIPromptModal;
(window as any).closeAIPromptModal = closeAIPromptModal;
(window as any).setAIPromptLanguage = setAIPromptLanguage;
(window as any).updateAIPromptPolicyPath = updateAIPromptPolicyPath;
(window as any).copyAIPrompt = copyAIPrompt;
(window as any).generateAIPrompt = generateAIPrompt;
