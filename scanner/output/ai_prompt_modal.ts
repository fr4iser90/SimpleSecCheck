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
const DEFAULT_POLICY_PATH = '.scanning/finding-policy.json';
let currentPolicyPath: string = DEFAULT_POLICY_PATH;
let currentIncludePRWorkflow: boolean = true;
let currentOnlyCriticalHigh: boolean = false;
let currentMaxFindings: number = 100;

// Helper function to safely set text content (prevents XSS)
function setTextContent(element: HTMLElement, text: string): void {
  element.textContent = text;
}

// Helper function to safely set attribute values
function setAttribute(element: HTMLElement, name: string, value: string): void {
  element.setAttribute(name, value);
}

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
      background: var(--modal-overlay);
      backdrop-filter: blur(8px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 999999;
      padding: 2rem;
      overflow-y: auto;
    `;
    
    const contentContainer = document.createElement('div');
    contentContainer.style.cssText = `
      max-width: 900px;
      width: 100%;
      max-height: 90vh;
      background: var(--modal-content-bg);
      border-radius: 16px;
      border: 1px solid var(--modal-content-border);
      box-shadow: var(--shadow-main);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      position: relative;
      z-index: 1000000;
      margin: auto;
      color: var(--text-primary);
    `;
    
    // Create header
    const header = document.createElement('div');
    header.style.cssText = `
      padding: 1.5rem;
      border-bottom: 1px solid var(--modal-content-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      color: var(--text-primary);
    `;
    
    const title = document.createElement('h2');
    title.style.margin = '0';
    setTextContent(title, '🤖 AI Prompt für Findings');
    
    const closeBtn = document.createElement('button');
    closeBtn.style.cssText = `
      background: transparent;
      border: none;
      font-size: 1.5rem;
      cursor: pointer;
      color: var(--text-primary);
      padding: 0.25rem 0.5rem;
      line-height: 1;
    `;
    setTextContent(closeBtn, '✕');
    closeBtn.addEventListener('click', closeAIPromptModal);
    
    header.appendChild(title);
    header.appendChild(closeBtn);
    
    // Main content: scrollable so long prompt doesn't overflow
    const mainContent = document.createElement('div');
    mainContent.style.cssText = `
      flex: 1;
      min-height: 0;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
      padding: 1.5rem;
    `;
    
    const previewSection = document.createElement('div');
    previewSection.style.cssText = 'flex: 1; display: flex; flex-direction: column; min-height: 0; overflow: hidden;';
    
    const previewLabel = document.createElement('label');
    previewLabel.style.cssText = 'margin-bottom: 0.5rem; font-weight: 600; color: var(--text-primary);';
    setTextContent(previewLabel, '📋 Prompt Preview');
    
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'ai-prompt-loading';
    loadingDiv.style.cssText = `
      flex: 1;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 2rem;
      background: var(--glass-bg-main);
      border-radius: 8px;
      border: 1px solid var(--glass-border-main);
      color: var(--text-primary);
    `;
    const loadingText = document.createElement('div');
    loadingText.style.opacity = '0.7';
    setTextContent(loadingText, '⏳ Loading prompt...');
    loadingDiv.appendChild(loadingText);
    
    const errorDiv = document.createElement('div');
    errorDiv.id = 'ai-prompt-error';
    errorDiv.style.cssText = `
      display: none;
      padding: 1rem;
      background: var(--color-critical-bg);
      border: 1px solid var(--color-critical);
      border-radius: 8px;
      color: var(--color-critical);
    `;
    
    const textarea = document.createElement('textarea');
    textarea.id = 'ai-prompt-textarea';
    textarea.style.cssText = `
      flex: 1;
      min-height: 400px;
      background: var(--glass-bg-main);
      border: 1px solid var(--glass-border-main);
      border-radius: 8px;
      padding: 1rem;
      color: var(--text-main);
      font-family: 'Courier New', monospace;
      font-size: 0.9rem;
      resize: vertical;
      white-space: pre-wrap;
      word-wrap: break-word;
      display: none;
    `;
    setAttribute(textarea, 'placeholder', 'Prompt will appear here...');
    
    previewSection.appendChild(previewLabel);
    previewSection.appendChild(loadingDiv);
    previewSection.appendChild(errorDiv);
    previewSection.appendChild(textarea);
    
    const settingsSection = document.createElement('div');
    settingsSection.style.cssText = `
      background: var(--glass-bg-main);
      border: 1px solid var(--glass-border-main);
      border-radius: 8px;
      padding: 1rem;
      color: var(--text-primary);
    `;
    
    const settingsTitle = document.createElement('div');
    settingsTitle.style.cssText = 'margin-bottom: 1rem; font-weight: 600; color: var(--text-primary);';
    setTextContent(settingsTitle, '⚙️ Einstellungen');
    
    const settingsContent = document.createElement('div');
    settingsContent.style.cssText = 'display: flex; flex-direction: column; gap: 1rem;';
    
    // Language section
    const languageSection = document.createElement('div');
    const languageLabel = document.createElement('label');
    languageLabel.style.cssText = 'margin-bottom: 0.5rem; display: block; color: var(--text-secondary);';
    setTextContent(languageLabel, 'Sprache / Language');
    
    const languageButtons = document.createElement('div');
    languageButtons.style.cssText = 'display: flex; gap: 0.5rem; flex-wrap: wrap;';
    
    const languages: { id: string; label: string; lang: Language }[] = [
      { id: 'lang-english', label: 'English', lang: 'english' },
      { id: 'lang-chinese', label: '中文', lang: 'chinese' },
      { id: 'lang-german', label: 'Deutsch', lang: 'german' }
    ];
    
    languages.forEach(({ id, label, lang }) => {
      const btn = document.createElement('button');
      btn.id = id;
      btn.style.cssText = `
        padding: 0.5rem 1rem;
        border-radius: 8px;
        cursor: pointer;
        border: 1px solid var(--glass-border-main);
        background: var(--glass-bg-main);
        color: var(--text-primary);
      `;
      setTextContent(btn, label);
      btn.addEventListener('click', () => setAIPromptLanguage(lang));
      languageButtons.appendChild(btn);
    });
    
    languageSection.appendChild(languageLabel);
    languageSection.appendChild(languageButtons);
    
    // Policy path section
    const policySection = document.createElement('div');
    const policyLabel = document.createElement('label');
    policyLabel.style.cssText = 'margin-bottom: 0.5rem; display: block; color: var(--text-secondary);';
    setTextContent(policyLabel, 'Policy path');
    
    const policyInput = document.createElement('input');
    policyInput.id = 'ai-prompt-policy-path';
    policyInput.type = 'text';
    policyInput.style.cssText = `
      width: 100%;
      padding: 0.75rem;
      background: var(--glass-bg-main);
      border: 1px solid var(--glass-border-main);
      border-radius: 8px;
      color: var(--text-primary);
      box-sizing: border-box;
    `;
    setAttribute(policyInput, 'placeholder', DEFAULT_POLICY_PATH);
    policyInput.value = currentPolicyPath;
    policyInput.addEventListener('input', () => {
      currentPolicyPath = policyInput.value.trim() || DEFAULT_POLICY_PATH;
      loadAIPrompt();
    });
    policyInput.addEventListener('change', () => {
      currentPolicyPath = policyInput.value.trim() || DEFAULT_POLICY_PATH;
      loadAIPrompt();
    });
    
    const policyHint = document.createElement('div');
    policyHint.style.cssText = 'margin-top: 0.35rem; font-size: 0.8rem; color: var(--text-secondary); opacity: 0.9;';
    setTextContent(policyHint, `Default: ${DEFAULT_POLICY_PATH} · Override: FINDING_POLICY_FILE`);
    
    policySection.appendChild(policyLabel);
    policySection.appendChild(policyInput);
    policySection.appendChild(policyHint);
    
    // Include Pull Request workflow
    const prSection = document.createElement('div');
    prSection.style.cssText = 'display: flex; align-items: center; gap: 0.5rem;';
    const prCheck = document.createElement('input');
    prCheck.id = 'ai-prompt-include-pr';
    prCheck.type = 'checkbox';
    prCheck.checked = currentIncludePRWorkflow;
    prCheck.addEventListener('change', () => {
      currentIncludePRWorkflow = (prCheck as HTMLInputElement).checked;
      loadAIPrompt();
    });
    const prLabel = document.createElement('label');
    prLabel.htmlFor = 'ai-prompt-include-pr';
    setTextContent(prLabel, 'Include Pull Request workflow');
    prSection.appendChild(prCheck);
    prSection.appendChild(prLabel);
    
    // Only Critical / High findings
    const severitySection = document.createElement('div');
    severitySection.style.cssText = 'display: flex; align-items: center; gap: 0.5rem;';
    const severityCheck = document.createElement('input');
    severityCheck.id = 'ai-prompt-only-critical-high';
    severityCheck.type = 'checkbox';
    severityCheck.checked = currentOnlyCriticalHigh;
    severityCheck.addEventListener('change', () => {
      currentOnlyCriticalHigh = (severityCheck as HTMLInputElement).checked;
      loadAIPrompt();
    });
    const severityLabel = document.createElement('label');
    severityLabel.htmlFor = 'ai-prompt-only-critical-high';
    setTextContent(severityLabel, 'Only Critical / High findings');
    severitySection.appendChild(severityCheck);
    severitySection.appendChild(severityLabel);
    
    // Max findings in prompt
    const maxSection = document.createElement('div');
    const maxLabel = document.createElement('label');
    maxLabel.style.cssText = 'margin-bottom: 0.35rem; display: block; color: var(--text-secondary);';
    maxLabel.htmlFor = 'ai-prompt-max-findings';
    setTextContent(maxLabel, 'Max findings in prompt');
    const maxInput = document.createElement('input');
    maxInput.id = 'ai-prompt-max-findings';
    maxInput.type = 'number';
    maxInput.min = '1';
    maxInput.value = String(currentMaxFindings);
    maxInput.style.cssText = `
      width: 6rem;
      padding: 0.5rem 0.75rem;
      background: var(--glass-bg-main);
      border: 1px solid var(--glass-border-main);
      border-radius: 8px;
      color: var(--text-primary);
      box-sizing: border-box;
    `;
    maxInput.addEventListener('change', () => {
      const n = parseInt(maxInput.value, 10);
      if (!isNaN(n) && n >= 1) {
        currentMaxFindings = n;
        loadAIPrompt();
      }
    });
    maxSection.appendChild(maxLabel);
    maxSection.appendChild(maxInput);
    
    settingsContent.appendChild(languageSection);
    settingsContent.appendChild(policySection);
    settingsContent.appendChild(prSection);
    settingsContent.appendChild(severitySection);
    settingsContent.appendChild(maxSection);
    
    settingsSection.appendChild(settingsTitle);
    settingsSection.appendChild(settingsContent);
    
    // Stats div
    const statsDiv = document.createElement('div');
    statsDiv.id = 'ai-prompt-stats';
    statsDiv.style.cssText = `
      display: none;
      padding: 0.75rem;
      background: var(--glass-bg-main);
      border: 1px solid var(--glass-border-main);
      border-radius: 8px;
      font-size: 0.9rem;
      color: var(--text-secondary);
    `;
    
    // Footer buttons
    const footer = document.createElement('div');
    footer.style.cssText = 'display: flex; gap: 1rem; justify-content: flex-end;';
    
    const cancelBtn = document.createElement('button');
    cancelBtn.style.cssText = `
      background: var(--glass-bg-main);
      border: 1px solid var(--glass-border-main);
      padding: 0.75rem 1.5rem;
      border-radius: 8px;
      color: var(--text-primary);
      cursor: pointer;
    `;
    setTextContent(cancelBtn, '❌ Cancel');
    cancelBtn.addEventListener('click', closeAIPromptModal);
    
    const copyBtn = document.createElement('button');
    copyBtn.id = 'ai-prompt-copy-btn';
    copyBtn.style.cssText = `
      padding: 0.75rem 1.5rem;
      border-radius: 8px;
      background: var(--btn-primary-gradient);
      border: none;
      color: var(--text-main);
      cursor: pointer;
      font-weight: 600;
    `;
    setTextContent(copyBtn, '📋 Copy Prompt');
    copyBtn.addEventListener('click', copyAIPrompt);
    
    const newTabBtn = document.createElement('button');
    newTabBtn.id = 'ai-prompt-new-tab-btn';
    newTabBtn.style.cssText = `
      padding: 0.75rem 1.5rem;
      border-radius: 8px;
      background: var(--glass-bg-main);
      border: 1px solid var(--glass-border-main);
      color: var(--text-primary);
      cursor: pointer;
      font-weight: 600;
    `;
    setTextContent(newTabBtn, '📄 In neuem Tab');
    newTabBtn.addEventListener('click', openAIPromptInNewTab);
    
    footer.appendChild(cancelBtn);
    footer.appendChild(copyBtn);
    footer.appendChild(newTabBtn);
    
    // Assemble main content
    mainContent.appendChild(previewSection);
    mainContent.appendChild(settingsSection);
    mainContent.appendChild(statsDiv);
    mainContent.appendChild(footer);
    
    // Assemble content container
    contentContainer.appendChild(header);
    contentContainer.appendChild(mainContent);
    
    // Add to modal
    aiPromptModal.appendChild(contentContainer);
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
    // Pre-fill from scan metadata (script id="scan-ai-prompt-defaults")
    try {
      const defaultsEl = document.getElementById('scan-ai-prompt-defaults') as HTMLScriptElement | null;
      if (defaultsEl && defaultsEl.textContent) {
        const defaults = JSON.parse(defaultsEl.textContent) as { policy_path?: string };
        if (defaults.policy_path && defaults.policy_path.trim()) {
          currentPolicyPath = defaults.policy_path.trim();
        }
      }
    } catch (_) { /* ignore */ }
    const input = document.getElementById('ai-prompt-policy-path') as HTMLInputElement | null;
    if (input) {
      input.value = currentPolicyPath;
    }
    const maxInput = document.getElementById('ai-prompt-max-findings') as HTMLInputElement | null;
    if (maxInput) {
      maxInput.value = String(currentMaxFindings);
    }
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
        btn.style.background = 'var(--btn-primary-gradient)';
        btn.style.borderColor = 'var(--btn-primary)';
        btn.style.fontWeight = '600';
      } else {
        btn.style.background = 'var(--glass-bg-main)';
        btn.style.borderColor = 'var(--glass-border-main)';
        btn.style.fontWeight = '400';
      }
    }
  });
  loadAIPrompt();
}

function updateAIPromptPolicyPath(path: string): void {
  currentPolicyPath = path.trim() || DEFAULT_POLICY_PATH;
  const input = document.getElementById('ai-prompt-policy-path') as HTMLInputElement | null;
  if (input) {
    input.value = currentPolicyPath;
  }
  loadAIPrompt();
}

function openAIPromptInNewTab(): void {
  const textarea = document.getElementById('ai-prompt-textarea') as HTMLTextAreaElement | null;
  if (!textarea || !textarea.value) return;
  const w = window.open('', '_blank');
  if (w) {
    w.document.write(
      '<!DOCTYPE html><html><head><meta charset="utf-8"><title>AI Prompt</title></head><body>' +
      '<pre style="white-space: pre-wrap; word-wrap: break-word; font-family: monospace; padding: 1rem; font-size: 14px;">' +
      textarea.value.replace(/</g, '&lt;').replace(/>/g, '&gt;') +
      '</pre></body></html>'
    );
    w.document.close();
  }
}

// Generate prompt locally from findings (same logic as backend)
function generatePromptLocally(
  findings: any[],
  language: Language,
  policyPath: string,
  maxFindingsPerPrompt: number,
  onlyCriticalHigh: boolean,
  includePRWorkflow: boolean
): string {
  let list = findings;
  if (onlyCriticalHigh) {
    list = list.filter((f: any) => {
      const sev = String(f.severity || '').toUpperCase();
      return sev === 'CRITICAL' || sev === 'HIGH' || sev.indexOf('CRIT') !== -1 || sev === 'ERROR';
    });
  }
  list = list.slice(0, maxFindingsPerPrompt);
  if (list.length === 0 && findings.length > 0) {
    list = findings.slice(0, maxFindingsPerPrompt);
  }
  
  const byTool: { [key: string]: any[] } = {};
  for (const f of list) {
    const tool = f.tool || 'Unknown';
    if (!byTool[tool]) {
      byTool[tool] = [];
    }
    byTool[tool].push(f);
  }
  
  const prWorkflowEn = "\n\n## Pull Request workflow\nIf you need to apply fixes in a repository: clone the repo if needed, apply fixes per finding or per file, commit with clear messages, and open a Pull Request. Re-run the scan with FINDING_POLICY_FILE set to verify.\n";
  const prWorkflowZh = "\n\n## 提交流程\n如需在仓库中应用修复：如需要请先克隆仓库，按发现或按文件修复，用清晰消息提交，并提交 Pull Request。使用 FINDING_POLICY_FILE 重新运行扫描以验证。\n";
  const prWorkflowDe = "\n\n## Pull-Request-Workflow\nWenn Sie Fixes im Repository anwenden müssen: Repo ggf. klonen, Fixes pro Finding oder pro Datei anwenden, mit klaren Commit-Messages committen und einen Pull Request öffnen. Scan mit gesetztem FINDING_POLICY_FILE erneut ausführen.\n";

  const policySchemaEn =
    "\n\n## Finding policy JSON schema (MUST follow exactly)\n" +
    "Output must be **valid JSON** (not YAML). Root must be a JSON object. Each top-level value must be a JSON object.\n" +
    "Only use these keys when relevant to the tool(s) in the findings. Do not invent new fields.\n\n" +
    "### Root shape\n" +
    `- File: \`${policyPath}\`\n` +
    "- Root: `{ <tool_policy_key>: <object>, ... }`\n\n" +
    "### Supported tool blocks and fields\n" +
    "- `semgrep`:\n" +
    "  - `accepted_findings[]`: `{ rule_id, path_regex, message_regex, reason }` (strings; regex fields optional)\n" +
    "  - `severity_overrides[]`: `{ rule_id, path_regex, message_regex, new_severity, reason }` (`new_severity`: CRITICAL|HIGH|MEDIUM|LOW|INFO)\n" +
    "  - `dedupe`: `{ enabled: boolean, line_window: number }`\n" +
    "- `bandit`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`\n" +
    "- `codeql`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`\n" +
    "- `gitleaks`: `accepted_findings[]` `{ rule_id, file_regex, description_regex, reason }`\n" +
    "- `detect_secrets`: `accepted_findings[]` `{ rule_id, path_regex, reason }`\n" +
    "- `npm_audit`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`\n" +
    "- `trivy`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`\n\n" +
    "### Minimal example skeleton\n" +
    "{\n" +
    '  "semgrep": {\n' +
    '    "accepted_findings": [\n' +
    "      {\n" +
    '        "rule_id": "EXAMPLE_RULE_ID",\n' +
    '        "path_regex": "EXAMPLE_PATH_REGEX",\n' +
    '        "message_regex": "EXAMPLE_MESSAGE_REGEX",\n' +
    '        "reason": "EXAMPLE_REASON"\n' +
    "      }\n" +
    "    ]\n" +
    "  }\n" +
    "}\n";

  const policySchemaDe =
    "\n\n## Finding-Policy JSON-Schema (MUSS exakt eingehalten werden)\n" +
    "Output muss **valide JSON** sein (kein YAML). Root muss ein JSON-Objekt sein. Jeder Top-Level-Value muss ein JSON-Objekt sein.\n" +
    "Nur diese Keys verwenden, wenn sie zum Tool passen. Keine neuen Felder erfinden.\n\n" +
    "### Root-Form\n" +
    `- Datei: \`${policyPath}\`\n` +
    "- Root: `{ <tool_policy_key>: <object>, ... }`\n\n" +
    "### Tool-Blöcke und Felder\n" +
    "- `semgrep`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`, `severity_overrides[]` `{ rule_id, path_regex, message_regex, new_severity, reason }`, `dedupe` `{ enabled, line_window }`\n" +
    "- `bandit`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`\n" +
    "- `codeql`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`\n" +
    "- `gitleaks`: `accepted_findings[]` `{ rule_id, file_regex, description_regex, reason }`\n" +
    "- `detect_secrets`: `accepted_findings[]` `{ rule_id, path_regex, reason }`\n" +
    "- `npm_audit`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`\n" +
    "- `trivy`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`\n";

  const policySchemaZh =
    "\n\n## Finding policy JSON 结构（必须严格遵守）\n" +
    "输出必须是**合法 JSON**（不是 YAML）。根必须是 JSON 对象。每个顶层 value 必须是 JSON 对象。\n" +
    "只使用与工具匹配的字段，不要编造新字段。\n\n" +
    "### 根结构\n" +
    `- 文件: \`${policyPath}\`\n` +
    "- 根: `{ <tool_policy_key>: <object>, ... }`\n\n" +
    "### 工具块与字段\n" +
    "- `semgrep`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`, `severity_overrides[]` `{ rule_id, path_regex, message_regex, new_severity, reason }`, `dedupe` `{ enabled, line_window }`\n" +
    "- `bandit`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`\n" +
    "- `codeql`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`\n" +
    "- `gitleaks`: `accepted_findings[]` `{ rule_id, file_regex, description_regex, reason }`\n" +
    "- `detect_secrets`: `accepted_findings[]` `{ rule_id, path_regex, reason }`\n" +
    "- `npm_audit`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`\n" +
    "- `trivy`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`\n";
  
  if (language === 'chinese') {
    const parts: string[] = [
      "# 安全扫描结果分析请求\n\n",
      "我对代码库进行了安全扫描，发现以下问题。请分析每个发现并：\n",
      "1. 识别误报（非实际安全问题的发现）\n",
      "2. 对于误报，如可能，建议代码更改以避免触发规则\n",
      "3. 如果无法/不适合更改代码，生成finding policy JSON条目\n",
      `4. 提供包含所有误报的完整${policyPath.split('/').pop() || 'finding-policy.json'}结构\n\n`,
      "## 发现摘要\n",
      `总发现数: ${list.length}\n`,
      `工具: ${Object.keys(byTool).join(', ')}\n\n`
    ];
    
    for (const [tool, toolFindings] of Object.entries(byTool)) {
      parts.push(`## ${tool} 发现 (${toolFindings.length} 个)\n\n`);
      for (let i = 0; i < toolFindings.length; i++) {
        const finding = toolFindings[i];
        parts.push(`### 发现 ${i + 1}\n`);
        parts.push(`- **严重性**: ${finding.severity || 'UNKNOWN'}\n`);
        parts.push(`- **文件**: \`${finding.path || ''}\`\n`);
        if (finding.line) {
          parts.push(`- **行号**: ${finding.line}\n`);
        }
        if (finding.rule_id) {
          parts.push(`- **规则ID**: \`${finding.rule_id}\`\n`);
        }
        parts.push(`- **消息**: ${finding.message || ''}\n\n`);
      }
    }
    parts.push(policySchemaZh);
    parts.push("\n## 期望输出\n");
    parts.push("1. 误报列表及说明\n");
    parts.push("2. 代码更改建议（如适用）\n");
    parts.push(`3. 包含所有误报的完整\`${policyPath.split('/').pop() || 'finding-policy.json'}\`结构\n`);
    parts.push(`   - 放置在\`${policyPath}\`\n`);
    parts.push("   - 使用适当的正则表达式进行路径/消息匹配\n");
    parts.push("   - 为每个接受的发现包含清晰的原因\n");
    if (includePRWorkflow) {
      parts.push(prWorkflowZh);
    }
    return parts.join('');
  } else if (language === 'german') {
    const parts: string[] = [
      "# Sicherheitsscan-Ergebnisse Analyseanfrage\n\n",
      "Ich habe einen Sicherheitsscan meines Codebases durchgeführt und die folgenden Probleme gefunden. ",
      "Bitte analysieren Sie jeden Fund und:\n",
      "1. Identifizieren Sie False Positives (Funde, die keine tatsächlichen Sicherheitsprobleme sind)\n",
      "2. Für False Positives schlagen Sie Code-Änderungen vor, falls möglich, um die Regel nicht auszulösen\n",
      "3. Wenn Code-Änderungen nicht möglich/angemessen sind, generieren Sie einen finding policy JSON-Eintrag\n",
      `4. Stellen Sie die vollständige ${policyPath.split('/').pop() || 'finding-policy.json'}-Struktur mit allen False Positives bereit\n\n`,
      "## Funde-Zusammenfassung\n",
      `Gesamtanzahl Funde: ${list.length}\n`,
      `Tools: ${Object.keys(byTool).join(', ')}\n\n`
    ];
    
    for (const [tool, toolFindings] of Object.entries(byTool)) {
      parts.push(`## ${tool} Funde (${toolFindings.length} insgesamt)\n\n`);
      for (let i = 0; i < toolFindings.length; i++) {
        const finding = toolFindings[i];
        parts.push(`### Fund ${i + 1}\n`);
        parts.push(`- **Schweregrad**: ${finding.severity || 'UNKNOWN'}\n`);
        parts.push(`- **Datei**: \`${finding.path || ''}\`\n`);
        if (finding.line) {
          parts.push(`- **Zeile**: ${finding.line}\n`);
        }
        if (finding.rule_id) {
          parts.push(`- **Regel-ID**: \`${finding.rule_id}\`\n`);
        }
        parts.push(`- **Nachricht**: ${finding.message || ''}\n\n`);
      }
    }
    parts.push(policySchemaDe);
    parts.push("\n## Erwartete Ausgabe\n");
    parts.push("1. Liste der False Positives mit Erklärung\n");
    parts.push("2. Code-Änderungsvorschläge (falls zutreffend)\n");
    parts.push(`3. Vollständige \`${policyPath.split('/').pop() || 'finding-policy.json'}\`-Struktur mit allen False Positives\n`);
    parts.push(`   - Platzieren in \`${policyPath}\`\n`);
    parts.push("   - Verwenden Sie geeignete Regex-Muster für Pfad/Nachricht-Matching\n");
    parts.push("   - Enthalten Sie klare Gründe für jeden akzeptierten Fund\n");
    if (includePRWorkflow) {
      parts.push(prWorkflowDe);
    }
    return parts.join('');
  } else {
    // English (default)
    const parts: string[] = [
      "# Security Scan Findings Analysis Request\n\n",
      "I have performed a security scan on my codebase and found the following issues. ",
      "Please analyze each finding and:\n",
      "1. Identify false positives (findings that are not actual security issues)\n",
      "2. For false positives, suggest code changes if possible to avoid triggering the rule\n",
      "3. If code changes are not possible/appropriate, generate a finding policy JSON entry\n",
      `4. Provide the complete ${policyPath.split('/').pop() || 'finding-policy.json'} structure with all false positives\n\n`,
      "## Findings Summary\n",
      `Total findings: ${list.length}\n`,
      `Tools: ${Object.keys(byTool).join(', ')}\n\n`
    ];
    
    for (const [tool, toolFindings] of Object.entries(byTool)) {
      parts.push(`## ${tool} Findings (${toolFindings.length} total)\n\n`);
      for (let i = 0; i < toolFindings.length; i++) {
        const finding = toolFindings[i];
        parts.push(`### Finding ${i + 1}\n`);
        parts.push(`- **Severity**: ${finding.severity || 'UNKNOWN'}\n`);
        parts.push(`- **File**: \`${finding.path || ''}\`\n`);
        if (finding.line) {
          parts.push(`- **Line**: ${finding.line}\n`);
        }
        if (finding.rule_id) {
          parts.push(`- **Rule ID**: \`${finding.rule_id}\`\n`);
        }
        parts.push(`- **Message**: ${finding.message || ''}\n\n`);
      }
    }
    parts.push(policySchemaEn);
    parts.push("\n## Expected Output\n");
    parts.push("1. List of false positives with explanations\n");
    parts.push("2. Code change suggestions (if applicable)\n");
    parts.push(`3. Complete \`${policyPath.split('/').pop() || 'finding-policy.json'}\` structure with all false positives\n`);
    parts.push(`   - Place in \`${policyPath}\`\n`);
    parts.push("   - Use proper regex patterns for path/message matching\n");
    parts.push("   - Include clear reasons for each accepted finding\n");
    if (includePRWorkflow) {
      parts.push(prWorkflowEn);
    }
    return parts.join('');
  }
}

// Generate split prompt for large projects
function generateSplitPrompt(findings: any[], language: Language, policyPath: string, maxFindings: number, includePRWorkflow: boolean = true): string {
  // Group by tool first
  const byTool: { [key: string]: any[] } = {};
  for (const f of findings) {
    const tool = f.tool || 'Unknown';
    if (!byTool[tool]) {
      byTool[tool] = [];
    }
    byTool[tool].push(f);
  }
  
  // Split into chunks
  const chunks: any[][] = [];
  let currentChunk: any[] = [];
  let currentCount = 0;
  
  for (const [tool, toolFindings] of Object.entries(byTool)) {
    // If adding this tool would exceed limit, start new chunk
    if (currentCount + toolFindings.length > maxFindings && currentChunk.length > 0) {
      chunks.push(currentChunk);
      currentChunk = [];
      currentCount = 0;
    }
    
    // Add all findings from this tool (keep tool findings together)
    currentChunk.push(...toolFindings);
    currentCount += toolFindings.length;
  }
  
  // Add remaining chunk
  if (currentChunk.length > 0) {
    chunks.push(currentChunk);
  }
  
  // Generate prompts for each chunk
  const prompts: string[] = [];
  for (let i = 0; i < chunks.length; i++) {
    const chunk = chunks[i];
    const chunkNum = i + 1;
    const totalChunks = chunks.length;
    
    // Group chunk by tool
    const chunkByTool: { [key: string]: any[] } = {};
    for (const f of chunk) {
      const tool = f.tool || 'Unknown';
      if (!chunkByTool[tool]) {
        chunkByTool[tool] = [];
      }
      chunkByTool[tool].push(f);
    }

    const policySchemaEn =
      "\n\n## Finding policy JSON schema (MUST follow exactly)\n" +
      "Output must be **valid JSON** (not YAML). Root must be a JSON object. Each top-level value must be a JSON object.\n" +
      "Only use these keys when relevant to the tool(s) in the findings. Do not invent new fields.\n\n" +
      "### Root shape\n" +
      `- File: \`${policyPath}\`\n` +
      "- Root: `{ <tool_policy_key>: <object>, ... }`\n\n" +
      "### Supported tool blocks and fields\n" +
      "- `semgrep`:\n" +
      "  - `accepted_findings[]`: `{ rule_id, path_regex, message_regex, reason }` (strings; regex fields optional)\n" +
      "  - `severity_overrides[]`: `{ rule_id, path_regex, message_regex, new_severity, reason }` (`new_severity`: CRITICAL|HIGH|MEDIUM|LOW|INFO)\n" +
      "  - `dedupe`: `{ enabled: boolean, line_window: number }`\n" +
      "- `bandit`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`\n" +
      "- `codeql`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`\n" +
      "- `gitleaks`: `accepted_findings[]` `{ rule_id, file_regex, description_regex, reason }`\n" +
      "- `detect_secrets`: `accepted_findings[]` `{ rule_id, path_regex, reason }`\n" +
      "- `npm_audit`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`\n" +
      "- `trivy`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`\n\n" +
      "### Minimal example skeleton\n" +
      "{\n" +
      '  "semgrep": {\n' +
      '    "accepted_findings": [\n' +
      "      {\n" +
      '        "rule_id": "EXAMPLE_RULE_ID",\n' +
      '        "path_regex": "EXAMPLE_PATH_REGEX",\n' +
      '        "message_regex": "EXAMPLE_MESSAGE_REGEX",\n' +
      '        "reason": "EXAMPLE_REASON"\n' +
      "      }\n" +
      "    ]\n" +
      "  }\n" +
      "}\n";

    const policySchemaDe =
      "\n\n## Finding-Policy JSON-Schema (MUSS exakt eingehalten werden)\n" +
      "Output muss **valide JSON** sein (kein YAML). Root muss ein JSON-Objekt sein. Jeder Top-Level-Value muss ein JSON-Objekt sein.\n" +
      "Nur diese Keys verwenden, wenn sie zum Tool passen. Keine neuen Felder erfinden.\n\n" +
      "### Root-Form\n" +
      `- Datei: \`${policyPath}\`\n` +
      "- Root: `{ <tool_policy_key>: <object>, ... }`\n\n" +
      "### Tool-Blöcke und Felder\n" +
      "- `semgrep`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`, `severity_overrides[]` `{ rule_id, path_regex, message_regex, new_severity, reason }`, `dedupe` `{ enabled, line_window }`\n" +
      "- `bandit`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`\n" +
      "- `codeql`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`\n" +
      "- `gitleaks`: `accepted_findings[]` `{ rule_id, file_regex, description_regex, reason }`\n" +
      "- `detect_secrets`: `accepted_findings[]` `{ rule_id, path_regex, reason }`\n" +
      "- `npm_audit`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`\n" +
      "- `trivy`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`\n";

    const policySchemaZh =
      "\n\n## Finding policy JSON 结构（必须严格遵守）\n" +
      "输出必须是**合法 JSON**（不是 YAML）。根必须是 JSON 对象。每个顶层 value 必须是 JSON 对象。\n" +
      "只使用与工具匹配的字段，不要编造新字段。\n\n" +
      "### 根结构\n" +
      `- 文件: \`${policyPath}\`\n` +
      "- 根: `{ <tool_policy_key>: <object>, ... }`\n\n" +
      "### 工具块与字段\n" +
      "- `semgrep`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`, `severity_overrides[]` `{ rule_id, path_regex, message_regex, new_severity, reason }`, `dedupe` `{ enabled, line_window }`\n" +
      "- `bandit`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`\n" +
      "- `codeql`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`\n" +
      "- `gitleaks`: `accepted_findings[]` `{ rule_id, file_regex, description_regex, reason }`\n" +
      "- `detect_secrets`: `accepted_findings[]` `{ rule_id, path_regex, reason }`\n" +
      "- `npm_audit`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`\n" +
      "- `trivy`: `accepted_findings[]` `{ rule_id, path_regex, message_regex, reason }`\n";
    
    if (language === 'chinese') {
      const parts: string[] = [
        "# 安全扫描结果分析请求\n\n",
        `## 第 ${chunkNum} 部分，共 ${totalChunks} 部分\n\n`,
        "我对代码库进行了安全扫描，发现以下问题。请分析每个发现并：\n",
        "1. 识别误报（非实际安全问题的发现）\n",
        "2. 对于误报，如可能，建议代码更改以避免触发规则\n",
        "3. 如果无法/不适合更改代码，生成finding policy JSON条目\n",
        `4. 提供包含所有误报的完整${policyPath.split('/').pop() || 'finding-policy.json'}结构\n\n`,
        "## 发现摘要\n",
        `本部分总发现数: ${chunk.length}\n`,
        `工具: ${Object.keys(chunkByTool).join(', ')}\n\n`
      ];
      
      for (const [tool, toolFindings] of Object.entries(chunkByTool)) {
        parts.push(`## ${tool} 发现 (${toolFindings.length} 个)\n\n`);
        for (let j = 0; j < toolFindings.length; j++) {
          const finding = toolFindings[j];
          parts.push(`### 发现 ${j + 1}\n`);
          parts.push(`- **严重性**: ${finding.severity || 'UNKNOWN'}\n`);
          parts.push(`- **文件**: \`${finding.path || ''}\`\n`);
          if (finding.line) {
            parts.push(`- **行号**: ${finding.line}\n`);
          }
          if (finding.rule_id) {
            parts.push(`- **规则ID**: \`${finding.rule_id}\`\n`);
          }
          parts.push(`- **消息**: ${finding.message || ''}\n\n`);
        }
      }
      
      parts.push(policySchemaZh);
      parts.push("\n## 期望输出\n");
      parts.push("1. 误报列表及说明\n");
      parts.push("2. 代码更改建议（如适用）\n");
      parts.push(`3. 包含所有误报的完整\`${policyPath.split('/').pop() || 'finding-policy.json'}\`结构\n`);
      parts.push(`   - 放置在\`${policyPath}\`\n`);
      parts.push("   - 使用适当的正则表达式进行路径/消息匹配\n");
      parts.push("   - 为每个接受的发现包含清晰的原因\n");
      
      prompts.push(parts.join(''));
    } else if (language === 'german') {
      const parts: string[] = [
        "# Sicherheitsscan-Ergebnisse Analyseanfrage\n\n",
        `## Teil ${chunkNum} von ${totalChunks}\n\n`,
        "Ich habe einen Sicherheitsscan meines Codebases durchgeführt und die folgenden Probleme gefunden. ",
        "Bitte analysieren Sie jeden Fund und:\n",
        "1. Identifizieren Sie False Positives (Funde, die keine tatsächlichen Sicherheitsprobleme sind)\n",
        "2. Für False Positives schlagen Sie Code-Änderungen vor, falls möglich, um die Regel nicht auszulösen\n",
        "3. Wenn Code-Änderungen nicht möglich/angemessen sind, generieren Sie einen finding policy JSON-Eintrag\n",
        `4. Stellen Sie die vollständige ${policyPath.split('/').pop() || 'finding-policy.json'}-Struktur mit allen False Positives bereit\n\n`,
        "## Funde-Zusammenfassung\n",
        `Gesamtanzahl Funde in diesem Teil: ${chunk.length}\n`,
        `Tools: ${Object.keys(chunkByTool).join(', ')}\n\n`
      ];
      
      for (const [tool, toolFindings] of Object.entries(chunkByTool)) {
        parts.push(`## ${tool} Funde (${toolFindings.length} insgesamt)\n\n`);
        for (let j = 0; j < toolFindings.length; j++) {
          const finding = toolFindings[j];
          parts.push(`### Fund ${j + 1}\n`);
          parts.push(`- **Schweregrad**: ${finding.severity || 'UNKNOWN'}\n`);
          parts.push(`- **Datei**: \`${finding.path || ''}\`\n`);
          if (finding.line) {
            parts.push(`- **Zeile**: ${finding.line}\n`);
          }
          if (finding.rule_id) {
            parts.push(`- **Regel-ID**: \`${finding.rule_id}\`\n`);
          }
          parts.push(`- **Nachricht**: ${finding.message || ''}\n\n`);
        }
      }
      
      parts.push(policySchemaDe);
      parts.push("\n## Erwartete Ausgabe\n");
      parts.push("1. Liste der False Positives mit Erklärung\n");
      parts.push("2. Code-Änderungsvorschläge (falls zutreffend)\n");
      parts.push(`3. Vollständige \`${policyPath.split('/').pop() || 'finding-policy.json'}\`-Struktur mit allen False Positives\n`);
      parts.push(`   - Platzieren in \`${policyPath}\`\n`);
      parts.push("   - Verwenden Sie geeignete Regex-Muster für Pfad/Nachricht-Matching\n");
      parts.push("   - Enthalten Sie klare Gründe für jeden akzeptierten Fund\n");
      
      prompts.push(parts.join(''));
    } else {
      // English
      const parts: string[] = [
        "# Security Scan Findings Analysis Request\n\n",
        `## Part ${chunkNum} of ${totalChunks}\n\n`,
        "I have performed a security scan on my codebase and found the following issues. ",
        "Please analyze each finding and:\n",
        "1. Identify false positives (findings that are not actual security issues)\n",
        "2. For false positives, suggest code changes if possible to avoid triggering the rule\n",
        "3. If code changes are not possible/appropriate, generate a finding policy JSON entry\n",
        `4. Provide the complete ${policyPath.split('/').pop() || 'finding-policy.json'} structure with all false positives\n\n`,
        "## Findings Summary\n",
        `Total findings in this part: ${chunk.length}\n`,
        `Tools: ${Object.keys(chunkByTool).join(', ')}\n\n`
      ];
      
      for (const [tool, toolFindings] of Object.entries(chunkByTool)) {
        parts.push(`## ${tool} Findings (${toolFindings.length} total)\n\n`);
        for (let j = 0; j < toolFindings.length; j++) {
          const finding = toolFindings[j];
          parts.push(`### Finding ${j + 1}\n`);
          parts.push(`- **Severity**: ${finding.severity || 'UNKNOWN'}\n`);
          parts.push(`- **File**: \`${finding.path || ''}\`\n`);
          if (finding.line) {
            parts.push(`- **Line**: ${finding.line}\n`);
          }
          if (finding.rule_id) {
            parts.push(`- **Rule ID**: \`${finding.rule_id}\`\n`);
          }
          parts.push(`- **Message**: ${finding.message || ''}\n\n`);
        }
      }
      
      parts.push(policySchemaEn);
      parts.push("\n## Expected Output\n");
      parts.push("1. List of false positives with explanations\n");
      parts.push("2. Code change suggestions (if applicable)\n");
      parts.push(`3. Complete \`${policyPath.split('/').pop() || 'finding-policy.json'}\` structure with all false positives\n`);
      parts.push(`   - Place in \`${policyPath}\`\n`);
      parts.push("   - Use proper regex patterns for path/message matching\n");
      parts.push("   - Include clear reasons for each accepted finding\n");
      
      prompts.push(parts.join(''));
    }
  }
  
  // Join with clear separator
  const separator = "\n\n" + "=".repeat(80) + "\n\n";
  return separator + prompts.join(separator);
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
    const findingsScript = document.getElementById('findings-data') as HTMLScriptElement | null;
    if (!findingsScript) {
      error.textContent =
        'No embedded findings in this page (missing script#findings-data). Open the scan summary.html from a completed scan.';
      error.style.display = 'block';
      loading.style.display = 'none';
      return;
    }

    let jsonText = findingsScript.textContent || findingsScript.innerText || '';
    if (jsonText.includes('&quot;') || jsonText.includes('&amp;')) {
      const parser = new DOMParser();
      const doc = parser.parseFromString(`<div>${jsonText}</div>`, 'text/html');
      const decodedElement = doc.body.firstElementChild as HTMLElement | null;
      jsonText = decodedElement ? (decodedElement.textContent || decodedElement.innerText || '') : jsonText;
    }

    if (!jsonText.trim()) {
      error.textContent = 'Embedded findings are empty. This report has no normalized findings for the AI prompt.';
      error.style.display = 'block';
      loading.style.display = 'none';
      return;
    }

    const findings = JSON.parse(jsonText);
    if (!Array.isArray(findings)) {
      throw new Error('findings-data is not a JSON array');
    }

    const includePR =
      (document.getElementById('ai-prompt-include-pr') as HTMLInputElement | null)?.checked ??
      currentIncludePRWorkflow;
    const onlyCH =
      (document.getElementById('ai-prompt-only-critical-high') as HTMLInputElement | null)?.checked ??
      currentOnlyCriticalHigh;
    const maxF =
      parseInt(
        (document.getElementById('ai-prompt-max-findings') as HTMLInputElement | null)?.value ||
          String(currentMaxFindings),
        10
      ) || currentMaxFindings;

    const prompt = generatePromptLocally(
      findings,
      currentLanguage,
      currentPolicyPath,
      maxF,
      onlyCH,
      includePR
    );
    currentPrompt = prompt;
    textarea.value = prompt;
    textarea.style.display = 'block';
    loading.style.display = 'none';
    const n = onlyCH
      ? Math.min(
          findings.filter((f: any) =>
            /^(CRITICAL|HIGH|ERROR)$/i.test(String(f.severity || ''))
          ).length,
          maxF
        )
      : Math.min(findings.length, maxF);
    const charK = Math.round(prompt.length / 1000);
    stats.textContent = `📊 ${n} findings · ~${charK}k characters`;
    stats.style.display = 'block';
  } catch (parseErr) {
    console.error('AI prompt from embedded findings failed:', parseErr);
    error.textContent =
      parseErr instanceof Error
        ? `Could not build prompt: ${parseErr.message}`
        : 'Could not build prompt from embedded findings.';
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
      btn.textContent = '📋 Copy Prompt';
    }, 2000);
  } catch (err) {
    alert('Failed to copy to clipboard');
  }
}

function generateAIPrompt(): void {
  // If in iframe (WebUI), send message to parent
  if (window.parent && window.parent !== window) {
    // Use specific origin instead of '*' for security
    // Try to get parent origin, fallback to current origin if same-origin
    const targetOrigin = window.location.origin;
    window.parent.postMessage({ type: 'OPEN_AI_PROMPT_MODAL' }, targetOrigin);
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
(window as any).openAIPromptInNewTab = openAIPromptInNewTab;
(window as any).generateAIPrompt = generateAIPrompt;
