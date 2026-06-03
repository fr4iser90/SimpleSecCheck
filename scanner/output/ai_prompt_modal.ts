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
const INLINE_FP_STEP_EN =
  '3. For a single-line false positive: add an inline comment on that line (`# nosec B608 — reason`, `# nosemgrep: rule-id`, `// eslint-disable-next-line rule-id`, or `# ssc:accept rule-id`). For broad patterns (many files): add a finding policy JSON entry\n';
const INLINE_FP_STEP_DE =
  '3. Für ein zeilenweises False Positive: Inline-Kommentar an der Zeile (`# nosec B608 — Begründung`, `# nosemgrep: rule-id`, `// eslint-disable-next-line rule-id`, oder `# ssc:accept rule-id`). Für breite Muster (viele Dateien): finding-policy JSON-Eintrag\n';
const INLINE_FP_STEP_ZH =
  '3. 单行误报：在该行添加内联注释（`# nosec B608 — 原因`、`# nosemgrep: rule-id`、`// eslint-disable-next-line rule-id` 或 `# ssc:accept rule-id`）。广泛模式（多文件）：添加 finding policy JSON 条目\n';
let currentPolicyPath: string = DEFAULT_POLICY_PATH;
let currentIncludePRWorkflow: boolean = true;
let currentMaxFindings: number = 100;
let currentMinSeverity: string = 'HIGH';
let currentToolFilter: string = '';
let currentSortBy: string = 'severity';

/** Upper bound for prompt size (matches API validation). */
const MAX_PROMPT_FINDINGS = 10000;

const SEV_ORDER: Record<string, number> = {
  CRITICAL: 0,
  HIGH: 1,
  MEDIUM: 2,
  LOW: 3,
  INFO: 4,
};

const MIN_SEVERITY_THRESHOLD: Record<string, number> = {
  CRITICAL: 0,
  HIGH: 1,
  MEDIUM: 2,
  LOW: 3,
  INFO: 4,
  ALL: 99,
};

type ReportFinding = {
  tool?: string;
  severity?: string;
  path?: string;
  line?: string | number;
  message?: string;
  rule_id?: string;
};

type PromptSelectionMeta = {
  total: number;
  matched: number;
  included: number;
  min_severity: string;
  tool: string | null;
  sort_by: string;
  included_by_severity: Record<string, number>;
};

function normalizeSeverity(sev: unknown): string {
  const raw = String(sev || '').trim().toUpperCase();
  if (!raw) return 'INFO';
  if (raw.indexOf('CRIT') !== -1) return 'CRITICAL';
  if (raw === 'HIGH' || raw === 'ERROR') return 'HIGH';
  if (raw === 'MEDIUM' || raw === 'MED' || raw === 'WARN' || raw === 'MODERATE') return 'MEDIUM';
  if (raw === 'LOW') return 'LOW';
  if (raw === 'INFO' || raw === 'INFORMATIONAL' || raw === 'NOTE') return 'INFO';
  return raw;
}

function severityRank(sev: unknown): number {
  return SEV_ORDER[normalizeSeverity(sev)] ?? 5;
}

function passesMinSeverity(sev: unknown, minSeverity: string): boolean {
  const key = (minSeverity || 'ALL').trim().toUpperCase();
  if (key === 'ALL') return true;
  const threshold = MIN_SEVERITY_THRESHOLD[key] ?? 1;
  return severityRank(sev) <= threshold;
}

function countBySeverity(findings: ReportFinding[]): Record<string, number> {
  const counts: Record<string, number> = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0, INFO: 0 };
  for (const f of findings) {
    const s = normalizeSeverity(f.severity);
    counts[s] = (counts[s] || 0) + 1;
  }
  return counts;
}

function sortFindingsList(findings: ReportFinding[], sortBy: string): ReportFinding[] {
  const list = findings.slice();
  const pathKey = (f: ReportFinding) => String(f.path || '').toLowerCase();
  const toolKey = (f: ReportFinding) => String(f.tool || '').toLowerCase();
  const key = (sortBy || 'severity').toLowerCase();
  if (key === 'tool') {
    return list.sort(
      (a, b) =>
        toolKey(a).localeCompare(toolKey(b)) ||
        severityRank(a.severity) - severityRank(b.severity) ||
        pathKey(a).localeCompare(pathKey(b))
    );
  }
  if (key === 'path') {
    return list.sort(
      (a, b) =>
        pathKey(a).localeCompare(pathKey(b)) ||
        severityRank(a.severity) - severityRank(b.severity) ||
        toolKey(a).localeCompare(toolKey(b))
    );
  }
  return list.sort(
    (a, b) =>
      severityRank(a.severity) - severityRank(b.severity) ||
      toolKey(a).localeCompare(toolKey(b)) ||
      pathKey(a).localeCompare(pathKey(b))
  );
}

function selectFindingsForPrompt(
  findings: ReportFinding[],
  options: {
    maxFindings: number;
    minSeverity: string;
    tool?: string;
    sortBy?: string;
  }
): { selected: ReportFinding[]; meta: PromptSelectionMeta } {
  const total = findings.length;
  const toolKey = (options.tool || '').trim();
  const filtered: ReportFinding[] = [];
  for (const f of findings) {
    if (toolKey && String(f.tool || '').trim() !== toolKey) continue;
    if (!passesMinSeverity(f.severity, options.minSeverity)) continue;
    filtered.push(f);
  }
  const sorted = sortFindingsList(filtered, options.sortBy || 'severity');
  const cap = Math.max(1, options.maxFindings);
  const selected = sorted.slice(0, cap);
  return {
    selected,
    meta: {
      total,
      matched: filtered.length,
      included: selected.length,
      min_severity: String(options.minSeverity || 'HIGH').toUpperCase(),
      tool: toolKey || null,
      sort_by: options.sortBy || 'severity',
      included_by_severity: countBySeverity(selected),
    },
  };
}

function formatSeverityBreakdown(counts: Record<string, number>): string {
  const parts: string[] = [];
  for (const sev of ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']) {
    const n = counts[sev] || 0;
    if (n > 0) parts.push(`${n} ${sev}`);
  }
  return parts.join(' · ');
}

function loadReportFindingsFromPage(): ReportFinding[] {
  const ids = ['report-findings-data', 'findings-data'];
  for (let i = 0; i < ids.length; i++) {
    const el = document.getElementById(ids[i]) as HTMLScriptElement | null;
    if (!el) continue;
    let jsonText = el.textContent || el.innerText || '';
    if (jsonText.indexOf('&quot;') !== -1 || jsonText.indexOf('&amp;') !== -1) {
      const parser = new DOMParser();
      const doc = parser.parseFromString('<div>' + jsonText + '</div>', 'text/html');
      const decoded = doc.body.firstElementChild as HTMLElement | null;
      jsonText = decoded ? decoded.textContent || decoded.innerText || '' : jsonText;
    }
    if (!jsonText.trim()) continue;
    try {
      const data = JSON.parse(jsonText);
      if (Array.isArray(data)) return data;
    } catch (_) {
      /* try next */
    }
  }
  return [];
}

function populateToolFilterOptions(findings: ReportFinding[]): void {
  const select = document.getElementById('ai-prompt-filter-tool') as HTMLSelectElement | null;
  if (!select) return;
  const tools = Array.from(
    new Set(findings.map((f) => String(f.tool || '').trim()).filter(Boolean))
  ).sort();
  const prev = select.value;
  select.innerHTML = '';
  const allOpt = document.createElement('option');
  allOpt.value = '';
  setTextContent(allOpt, 'All tools');
  select.appendChild(allOpt);
  for (let i = 0; i < tools.length; i++) {
    const opt = document.createElement('option');
    opt.value = tools[i];
    setTextContent(opt, tools[i]);
    select.appendChild(opt);
  }
  if (prev && tools.indexOf(prev) !== -1) {
    select.value = prev;
  } else {
    select.value = currentToolFilter;
  }
}

function readPromptFilterSettings(): void {
  const minEl = document.getElementById('ai-prompt-min-severity') as HTMLSelectElement | null;
  const toolEl = document.getElementById('ai-prompt-filter-tool') as HTMLSelectElement | null;
  const sortEl = document.getElementById('ai-prompt-sort-by') as HTMLSelectElement | null;
  const maxEl = document.getElementById('ai-prompt-max-findings') as HTMLInputElement | null;
  if (minEl) currentMinSeverity = minEl.value || 'HIGH';
  if (toolEl) currentToolFilter = toolEl.value || '';
  if (sortEl) currentSortBy = sortEl.value || 'severity';
  if (maxEl) {
    currentMaxFindings = clampMaxFindings(parseInt(maxEl.value, 10));
    maxEl.value = String(currentMaxFindings);
  }
}

function clampMaxFindings(n: number): number {
  if (isNaN(n) || n < 1) return 100;
  return Math.min(n, MAX_PROMPT_FINDINGS);
}

let promptRefreshTimer: ReturnType<typeof setTimeout> | null = null;

function scheduleRefreshAIPrompt(delayMs: number = 120): void {
  if (promptRefreshTimer !== null) {
    clearTimeout(promptRefreshTimer);
  }
  promptRefreshTimer = setTimeout(() => {
    promptRefreshTimer = null;
    refreshAIPromptContent();
  }, delayMs);
}

function applyMaxFindingsFromInput(): void {
  const maxEl = document.getElementById('ai-prompt-max-findings') as HTMLInputElement | null;
  if (!maxEl) return;
  currentMaxFindings = clampMaxFindings(parseInt(maxEl.value, 10));
  maxEl.value = String(currentMaxFindings);
}

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
      scheduleRefreshAIPrompt(200);
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
      refreshAIPromptContent();
    });
    const prLabel = document.createElement('label');
    prLabel.htmlFor = 'ai-prompt-include-pr';
    setTextContent(prLabel, 'Include Pull Request workflow');
    prSection.appendChild(prCheck);
    prSection.appendChild(prLabel);
    
    const filterSection = document.createElement('div');
    filterSection.style.cssText =
      'display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.75rem;';
    const selectStyle = `
      width: 100%;
      padding: 0.5rem 0.75rem;
      background: var(--glass-bg-main);
      border: 1px solid var(--glass-border-main);
      border-radius: 8px;
      color: var(--text-primary);
      box-sizing: border-box;
    `;

    const minSection = document.createElement('div');
    const minLabel = document.createElement('label');
    minLabel.style.cssText = 'margin-bottom: 0.35rem; display: block; color: var(--text-secondary);';
    minLabel.htmlFor = 'ai-prompt-min-severity';
    setTextContent(minLabel, 'Min. severity');
    const minSelect = document.createElement('select');
    minSelect.id = 'ai-prompt-min-severity';
    minSelect.style.cssText = selectStyle;
    [
      { v: 'CRITICAL', l: 'Critical only' },
      { v: 'HIGH', l: 'Critical + High' },
      { v: 'MEDIUM', l: 'Medium+' },
      { v: 'LOW', l: 'Low+' },
      { v: 'ALL', l: 'All severities' },
    ].forEach(({ v, l }) => {
      const opt = document.createElement('option');
      opt.value = v;
      setTextContent(opt, l);
      minSelect.appendChild(opt);
    });
    minSelect.value = currentMinSeverity;
    minSelect.addEventListener('change', () => {
      readPromptFilterSettings();
      refreshAIPromptContent();
    });
    minSection.appendChild(minLabel);
    minSection.appendChild(minSelect);

    const toolSection = document.createElement('div');
    const toolLabel = document.createElement('label');
    toolLabel.style.cssText = 'margin-bottom: 0.35rem; display: block; color: var(--text-secondary);';
    toolLabel.htmlFor = 'ai-prompt-filter-tool';
    setTextContent(toolLabel, 'Tool');
    const toolSelect = document.createElement('select');
    toolSelect.id = 'ai-prompt-filter-tool';
    toolSelect.style.cssText = selectStyle;
    toolSelect.addEventListener('change', () => {
      readPromptFilterSettings();
      refreshAIPromptContent();
    });
    toolSection.appendChild(toolLabel);
    toolSection.appendChild(toolSelect);

    const sortSection = document.createElement('div');
    const sortLabel = document.createElement('label');
    sortLabel.style.cssText = 'margin-bottom: 0.35rem; display: block; color: var(--text-secondary);';
    sortLabel.htmlFor = 'ai-prompt-sort-by';
    setTextContent(sortLabel, 'Sort by');
    const sortSelect = document.createElement('select');
    sortSelect.id = 'ai-prompt-sort-by';
    sortSelect.style.cssText = selectStyle;
    [
      { v: 'severity', l: 'Severity (first)' },
      { v: 'tool', l: 'Tool' },
      { v: 'path', l: 'File' },
    ].forEach(({ v, l }) => {
      const opt = document.createElement('option');
      opt.value = v;
      setTextContent(opt, l);
      sortSelect.appendChild(opt);
    });
    sortSelect.value = currentSortBy;
    sortSelect.addEventListener('change', () => {
      readPromptFilterSettings();
      refreshAIPromptContent();
    });
    sortSection.appendChild(sortLabel);
    sortSection.appendChild(sortSelect);

    const maxSection = document.createElement('div');
    const maxLabel = document.createElement('label');
    maxLabel.style.cssText = 'margin-bottom: 0.35rem; display: block; color: var(--text-secondary);';
    maxLabel.htmlFor = 'ai-prompt-max-findings';
    setTextContent(maxLabel, 'Max in prompt');
    const maxInput = document.createElement('input');
    maxInput.id = 'ai-prompt-max-findings';
    maxInput.type = 'number';
    maxInput.min = '1';
    maxInput.max = String(MAX_PROMPT_FINDINGS);
    maxInput.value = String(currentMaxFindings);
    maxInput.style.cssText = selectStyle;
    maxInput.addEventListener('input', () => {
      applyMaxFindingsFromInput();
      scheduleRefreshAIPrompt(150);
    });
    const maxHint = document.createElement('div');
    maxHint.style.cssText = 'margin-top: 0.25rem; font-size: 0.75rem; color: var(--text-secondary); opacity: 0.85;';
    setTextContent(maxHint, `1–${MAX_PROMPT_FINDINGS}, prompt updates as you type`);
    maxSection.appendChild(maxLabel);
    maxSection.appendChild(maxInput);
    maxSection.appendChild(maxHint);

    filterSection.appendChild(minSection);
    filterSection.appendChild(toolSection);
    filterSection.appendChild(sortSection);
    filterSection.appendChild(maxSection);

    const useTableBtn = document.createElement('button');
    useTableBtn.type = 'button';
    useTableBtn.style.cssText = `
      padding: 0.5rem 0.75rem;
      border-radius: 8px;
      cursor: pointer;
      border: 1px solid var(--glass-border-main);
      background: var(--glass-bg-main);
      color: var(--text-primary);
      font-size: 0.85rem;
      justify-self: start;
    `;
    setTextContent(useTableBtn, '↻ Use report table filters');
    useTableBtn.addEventListener('click', () => {
      const toolEl = document.getElementById('filter-tool') as HTMLSelectElement | null;
      const sevEl = document.getElementById('filter-severity') as HTMLSelectElement | null;
      const sortEl = document.getElementById('sort-findings') as HTMLSelectElement | null;
      if (toolEl) {
        currentToolFilter = toolEl.value || '';
        const aiTool = document.getElementById('ai-prompt-filter-tool') as HTMLSelectElement | null;
        if (aiTool) aiTool.value = currentToolFilter;
      }
      if (sevEl && sevEl.value) {
        currentMinSeverity = sevEl.value;
        const aiMin = document.getElementById('ai-prompt-min-severity') as HTMLSelectElement | null;
        if (aiMin) aiMin.value = currentMinSeverity;
      }
      if (sortEl) {
        currentSortBy = sortEl.value || 'severity';
        const aiSort = document.getElementById('ai-prompt-sort-by') as HTMLSelectElement | null;
        if (aiSort) aiSort.value = currentSortBy;
      }
      refreshAIPromptContent();
    });

    settingsContent.appendChild(languageSection);
    settingsContent.appendChild(policySection);
    settingsContent.appendChild(prSection);
    settingsContent.appendChild(filterSection);
    settingsContent.appendChild(useTableBtn);
    
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
    if (maxInput) maxInput.value = String(currentMaxFindings);
    const minSelect = document.getElementById('ai-prompt-min-severity') as HTMLSelectElement | null;
    if (minSelect) minSelect.value = currentMinSeverity;
    const sortSelect = document.getElementById('ai-prompt-sort-by') as HTMLSelectElement | null;
    if (sortSelect) sortSelect.value = currentSortBy;
  }
  loadAIPrompt(true);
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
  refreshAIPromptContent();
}

function updateAIPromptPolicyPath(path: string): void {
  currentPolicyPath = path.trim() || DEFAULT_POLICY_PATH;
  const input = document.getElementById('ai-prompt-policy-path') as HTMLInputElement | null;
  if (input) {
    input.value = currentPolicyPath;
  }
  refreshAIPromptContent();
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
  findings: ReportFinding[],
  language: Language,
  policyPath: string,
  maxFindingsPerPrompt: number,
  minSeverity: string,
  toolFilter: string,
  sortBy: string,
  includePRWorkflow: boolean
): string {
  const { selected: list } = selectFindingsForPrompt(findings, {
    maxFindings: maxFindingsPerPrompt,
    minSeverity: minSeverity,
    tool: toolFilter,
    sortBy: sortBy,
  });

  const byTool: { [key: string]: ReportFinding[] } = {};
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
      INLINE_FP_STEP_ZH,
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
      INLINE_FP_STEP_DE,
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
      INLINE_FP_STEP_EN,
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
        INLINE_FP_STEP_ZH,
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
        INLINE_FP_STEP_DE,
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
        INLINE_FP_STEP_EN,
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

function buildPromptFromPageSettings(): {
  prompt: string;
  meta: PromptSelectionMeta;
  selectedCount: number;
  matchedCount: number;
} | null {
  readPromptFilterSettings();
  const findings = loadReportFindingsFromPage();
  if (!findings.length) {
    return null;
  }
  populateToolFilterOptions(findings);
  const includePR =
    (document.getElementById('ai-prompt-include-pr') as HTMLInputElement | null)?.checked ??
    currentIncludePRWorkflow;
  const { selected, meta } = selectFindingsForPrompt(findings, {
    maxFindings: currentMaxFindings,
    minSeverity: currentMinSeverity,
    tool: currentToolFilter,
    sortBy: currentSortBy,
  });
  const prompt = generatePromptLocally(
    findings,
    currentLanguage,
    currentPolicyPath,
    currentMaxFindings,
    currentMinSeverity,
    currentToolFilter,
    currentSortBy,
    includePR
  );
  return { prompt, meta, selectedCount: selected.length, matchedCount: meta.matched };
}

function refreshAIPromptContent(): void {
  const error = document.getElementById('ai-prompt-error') as HTMLDivElement | null;
  const textarea = document.getElementById('ai-prompt-textarea') as HTMLTextAreaElement | null;
  const stats = document.getElementById('ai-prompt-stats') as HTMLDivElement | null;
  const loading = document.getElementById('ai-prompt-loading') as HTMLDivElement | null;
  if (!error || !textarea || !stats) return;

  try {
    const built = buildPromptFromPageSettings();
    if (!built) {
      error.textContent =
        'No embedded findings in this page (missing report-findings-data). Open the scan summary.html from a completed scan.';
      error.style.display = 'block';
      return;
    }
    const { prompt, meta, selectedCount, matchedCount } = built;
    currentPrompt = prompt;
    textarea.value = prompt;
    textarea.style.display = 'block';
    if (loading) loading.style.display = 'none';
    const charK = Math.round(prompt.length / 1000);
    const breakdown = formatSeverityBreakdown(meta.included_by_severity);
    stats.textContent =
      `📊 ${meta.included} in prompt (${breakdown}) · ${meta.matched} match filter · ${meta.total} total · ~${charK}k chars`;
    stats.style.display = 'block';
    if (selectedCount === 0 && matchedCount === 0) {
      error.textContent =
        'No findings match the current filters. Lower min. severity, clear tool filter, or raise max in prompt.';
      error.style.display = 'block';
    } else {
      error.style.display = 'none';
    }
  } catch (parseErr) {
    console.error('AI prompt refresh failed:', parseErr);
    error.textContent =
      parseErr instanceof Error
        ? `Could not build prompt: ${parseErr.message}`
        : 'Could not build prompt from embedded findings.';
    error.style.display = 'block';
  }
}

async function loadAIPrompt(initialOpen: boolean = false): Promise<void> {
  const loading = document.getElementById('ai-prompt-loading') as HTMLDivElement | null;
  const error = document.getElementById('ai-prompt-error') as HTMLDivElement | null;
  const textarea = document.getElementById('ai-prompt-textarea') as HTMLTextAreaElement | null;
  const stats = document.getElementById('ai-prompt-stats') as HTMLDivElement | null;

  if (!loading || !error || !textarea || !stats) return;

  const hasExistingPrompt = textarea.style.display !== 'none' && textarea.value.length > 0;
  if (initialOpen && !hasExistingPrompt) {
    loading.style.display = 'flex';
    error.style.display = 'none';
    textarea.style.display = 'none';
    stats.style.display = 'none';
  }

  refreshAIPromptContent();
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
