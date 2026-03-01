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
      z-index: 999999;
      padding: 2rem;
      overflow-y: auto;
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
        position: relative;
        z-index: 1000000;
        margin: auto;
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
                  value="${currentPolicyPath}"
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
    // Update input field with current value
    const input = document.getElementById('ai-prompt-policy-path') as HTMLInputElement | null;
    if (input) {
      input.value = currentPolicyPath;
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
  // Update input field to reflect the change
  const input = document.getElementById('ai-prompt-policy-path') as HTMLInputElement | null;
  if (input) {
    input.value = path;
  }
  loadAIPrompt();
}

// Generate prompt locally from findings (same logic as backend)
function generatePromptLocally(findings: any[], language: Language, policyPath: string, maxFindingsPerPrompt: number = 50): string {
  // Split findings if too many
  if (findings.length > maxFindingsPerPrompt) {
    return generateSplitPrompt(findings, language, policyPath, maxFindingsPerPrompt);
  }
  
  // Group by tool
  const byTool: { [key: string]: any[] } = {};
  for (const f of findings) {
    const tool = f.tool || 'Unknown';
    if (!byTool[tool]) {
      byTool[tool] = [];
    }
    byTool[tool].push(f);
  }
  
  if (language === 'chinese') {
    const parts: string[] = [
      "# 安全扫描结果分析请求\n\n",
      "我对代码库进行了安全扫描，发现以下问题。请分析每个发现并：\n",
      "1. 识别误报（非实际安全问题的发现）\n",
      "2. 对于误报，如可能，建议代码更改以避免触发规则\n",
      "3. 如果无法/不适合更改代码，生成finding policy JSON条目\n",
      `4. 提供包含所有误报的完整${policyPath.split('/').pop() || 'finding-policy.json'}结构\n\n`,
      "## 发现摘要\n",
      `总发现数: ${findings.length}\n`,
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
        if (finding.check_id) {
          parts.push(`- **规则ID**: \`${finding.check_id}\`\n`);
        }
        parts.push(`- **消息**: ${finding.message || ''}\n\n`);
      }
    }
    
    parts.push("\n## 期望输出\n");
    parts.push("1. 误报列表及说明\n");
    parts.push("2. 代码更改建议（如适用）\n");
    parts.push(`3. 包含所有误报的完整\`${policyPath.split('/').pop() || 'finding-policy.json'}\`结构\n`);
    parts.push(`   - 放置在\`${policyPath}\`\n`);
    parts.push("   - 使用适当的正则表达式进行路径/消息匹配\n");
    parts.push("   - 为每个接受的发现包含清晰的原因\n");
    
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
      `Gesamtanzahl Funde: ${findings.length}\n`,
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
        if (finding.check_id) {
          parts.push(`- **Regel-ID**: \`${finding.check_id}\`\n`);
        }
        parts.push(`- **Nachricht**: ${finding.message || ''}\n\n`);
      }
    }
    
    parts.push("\n## Erwartete Ausgabe\n");
    parts.push("1. Liste der False Positives mit Erklärung\n");
    parts.push("2. Code-Änderungsvorschläge (falls zutreffend)\n");
    parts.push(`3. Vollständige \`${policyPath.split('/').pop() || 'finding-policy.json'}\`-Struktur mit allen False Positives\n`);
    parts.push(`   - Platzieren in \`${policyPath}\`\n`);
    parts.push("   - Verwenden Sie geeignete Regex-Muster für Pfad/Nachricht-Matching\n");
    parts.push("   - Enthalten Sie klare Gründe für jeden akzeptierten Fund\n");
    
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
      `Total findings: ${findings.length}\n`,
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
        if (finding.check_id) {
          parts.push(`- **Rule ID**: \`${finding.check_id}\`\n`);
        }
        parts.push(`- **Message**: ${finding.message || ''}\n\n`);
      }
    }
    
    parts.push("\n## Expected Output\n");
    parts.push("1. List of false positives with explanations\n");
    parts.push("2. Code change suggestions (if applicable)\n");
    parts.push(`3. Complete \`${policyPath.split('/').pop() || 'finding-policy.json'}\` structure with all false positives\n`);
    parts.push(`   - Place in \`${policyPath}\`\n`);
    parts.push("   - Use proper regex patterns for path/message matching\n");
    parts.push("   - Include clear reasons for each accepted finding\n");
    
    return parts.join('');
  }
}

// Generate split prompt for large projects
function generateSplitPrompt(findings: any[], language: Language, policyPath: string, maxFindings: number): string {
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
          if (finding.check_id) {
            parts.push(`- **规则ID**: \`${finding.check_id}\`\n`);
          }
          parts.push(`- **消息**: ${finding.message || ''}\n\n`);
        }
      }
      
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
          if (finding.check_id) {
            parts.push(`- **Regel-ID**: \`${finding.check_id}\`\n`);
          }
          parts.push(`- **Nachricht**: ${finding.message || ''}\n\n`);
        }
      }
      
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
          if (finding.check_id) {
            parts.push(`- **Rule ID**: \`${finding.check_id}\`\n`);
          }
          parts.push(`- **Message**: ${finding.message || ''}\n\n`);
        }
      }
      
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
      throw new Error('API request failed');
    }
  } catch (err) {
    // Fallback: Extract findings from embedded JSON in HTML
    try {
      const findingsScript = document.getElementById('findings-data') as HTMLScriptElement | null;
      if (findingsScript) {
        // Get text content - try textContent first, then innerText
        let jsonText = findingsScript.textContent || findingsScript.innerText || '';
        
        // Decode HTML entities if present (shouldn't be, but handle it just in case)
        // Use DOMParser instead of innerHTML to avoid XSS risks
        if (jsonText.includes('&quot;') || jsonText.includes('&amp;')) {
          const parser = new DOMParser();
          const doc = parser.parseFromString(`<div>${jsonText}</div>`, 'text/html');
          const decodedElement = doc.body.firstElementChild as HTMLElement | null;
          jsonText = decodedElement ? (decodedElement.textContent || decodedElement.innerText || '') : jsonText;
        }
        
        if (jsonText.trim()) {
          const findings = JSON.parse(jsonText);
          const prompt = generatePromptLocally(findings, currentLanguage, currentPolicyPath);
          currentPrompt = prompt;
          textarea.value = prompt;
          textarea.style.display = 'block';
          loading.style.display = 'none';
          
          const tokens = Math.ceil(prompt.length / (currentLanguage === 'chinese' ? 2 : 4));
          stats.textContent = `📊 ${findings.length} findings | ~${tokens.toLocaleString()} tokens`;
          stats.style.display = 'block';
          return;
        }
      }
    } catch (parseErr) {
      // If embedded JSON doesn't exist or is invalid, show error
      console.error('Failed to parse embedded findings:', parseErr);
      console.error('Findings script element:', document.getElementById('findings-data'));
    }
    
    const errorMessage = err instanceof Error ? err.message : 'Unknown error';
    error.textContent = `Error: ${errorMessage}. Make sure the WebUI is running on http://localhost:8080 or open the report via WebUI.`;
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
(window as any).generateAIPrompt = generateAIPrompt;
