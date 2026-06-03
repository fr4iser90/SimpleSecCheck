import { useState, useEffect, useMemo } from 'react'
import { useTranslation, Language } from '../i18n'
import { resolveApiUrl } from '../utils/resolveApiUrl'

interface AIPromptModalProps {
  isOpen: boolean
  onClose: () => void
  scanId?: string | null
}

interface PromptData {
  prompt: string
  findings_count: number
  total_findings?: number
  matched_findings?: number
  included_by_severity?: Record<string, number>
  language: string
  policy_path: string
  max_findings?: number
  min_severity?: string
  tool?: string | null
  sort_by?: string
}

const mapUILanguageToPromptLanguage = (uiLang: Language): string => {
  const mapping: Record<Language, string> = {
    en: 'english',
    zh: 'chinese',
    de: 'german',
  }
  return mapping[uiLang] || 'english'
}

const MAX_PROMPT_FINDINGS = 10000

function clampMaxFindings(raw: number): number {
  if (Number.isNaN(raw) || raw < 1) return 100
  return Math.min(raw, MAX_PROMPT_FINDINGS)
}

const selectStyle: React.CSSProperties = {
  width: '100%',
  padding: '0.5rem 0.75rem',
  background: 'var(--glass-bg-main)',
  border: '1px solid var(--glass-border-main)',
  borderRadius: '8px',
  color: 'var(--text-main)',
  boxSizing: 'border-box',
}

export default function AIPromptModal({ isOpen, onClose, scanId }: AIPromptModalProps) {
  const { t, language: uiLanguage, setLanguage: setUILanguage, languages } = useTranslation()

  const [promptLanguage, setPromptLanguage] = useState<Language>(uiLanguage)
  const [policyPath, setPolicyPath] = useState('.scanning/finding-policy.json')
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [promptData, setPromptData] = useState<PromptData | null>(null)
  const [copied, setCopied] = useState(false)

  const [maxFindings, setMaxFindings] = useState(100)
  const [maxFindingsDraft, setMaxFindingsDraft] = useState('100')
  const [minSeverity, setMinSeverity] = useState('HIGH')
  const [toolFilter, setToolFilter] = useState('')
  const [toolFilterDraft, setToolFilterDraft] = useState('')
  const [sortBy, setSortBy] = useState('severity')

  const commitMaxFindings = () => {
    const n = clampMaxFindings(parseInt(maxFindingsDraft, 10))
    setMaxFindingsDraft(String(n))
    setMaxFindings(n)
  }

  const commitToolFilter = () => {
    setToolFilter(toolFilterDraft.trim())
  }

  const filterDeps = useMemo(
    () => [isOpen, promptLanguage, policyPath, scanId, maxFindings, minSeverity, toolFilter, sortBy],
    [isOpen, promptLanguage, policyPath, scanId, maxFindings, minSeverity, toolFilter, sortBy]
  )

  useEffect(() => {
    if (isOpen) {
      loadPrompt()
    }
  }, filterDeps)

  const loadPrompt = async () => {
    setLoading(true)
    setError(null)

    try {
      const backendLanguage = mapUILanguageToPromptLanguage(promptLanguage)
      const params = new URLSearchParams({
        language: backendLanguage,
        policy_path: policyPath || '.scanning/finding-policy.json',
        max_findings: String(maxFindings),
        min_severity: minSeverity,
        sort_by: sortBy,
      })
      if (toolFilter.trim()) {
        params.set('tool', toolFilter.trim())
      }
      const endpoint = scanId
        ? `/api/results/${scanId}/ai-prompt?${params.toString()}`
        : `/api/scan/ai-prompt?${params.toString()}`

      const response = await fetch(resolveApiUrl(endpoint))

      if (response.ok) {
        const data: PromptData = await response.json()
        setPrompt(data.prompt)
        setPromptData(data)
      } else if (response.status === 422) {
        setError(t('aiPrompt.validationFailed', { max: String(MAX_PROMPT_FINDINGS) }))
        setPrompt('')
        setPromptData(null)
      } else {
        const errorText = await response.text()
        setError(`${t('aiPrompt.failedToLoad')}: ${errorText}`)
        setPrompt('')
        setPromptData(null)
      }
    } catch (err) {
      setError(`${t('common.error')}: ${err instanceof Error ? err.message : 'Unknown error'}`)
      setPrompt('')
      setPromptData(null)
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = async () => {
    if (!prompt) return

    try {
      await navigator.clipboard.writeText(prompt)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
      alert(t('common.error'))
    }
  }

  const handleLanguageChange = (newLanguage: Language) => {
    setPromptLanguage(newLanguage)
    setUILanguage(newLanguage)
  }

  const estimateTokens = (text: string): number => {
    if (promptLanguage === 'zh') {
      return Math.ceil(text.length / 2)
    }
    return Math.ceil(text.length / 4)
  }

  const severityBreakdown = (counts?: Record<string, number>) => {
    if (!counts) return ''
    const order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']
    return order
      .filter((s) => (counts[s] || 0) > 0)
      .map((s) => `${counts[s]} ${s}`)
      .join(' · ')
  }

  if (!isOpen) return null

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'var(--modal-overlay-bg)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '2rem',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose()
        }
      }}
    >
      <div
        style={{
          background: 'var(--modal-content-bg)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          borderRadius: '8px',
          border: '1px solid var(--glass-border-main)',
          boxShadow: 'var(--shadow-main)',
          padding: '2rem',
          maxWidth: '900px',
          width: '100%',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          position: 'relative',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '1.5rem',
            borderBottom: '1px solid var(--glass-border-main)',
            paddingBottom: '1rem',
          }}
        >
          <h2 style={{ margin: 0 }}>🤖 {t('aiPrompt.title')}</h2>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              fontSize: '1.5rem',
              cursor: 'pointer',
              color: 'var(--text-main)',
              padding: '0.25rem 0.5rem',
              lineHeight: 1,
            }}
            title={t('common.close')}
          >
            ✕
          </button>
        </div>

        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="form-group" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <label style={{ marginBottom: '0.5rem', fontWeight: 600 }}>📋 {t('aiPrompt.promptPreview')}:</label>
            {loading ? (
              <div
                style={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '2rem',
                  background: 'var(--glass-bg-main)',
                  borderRadius: '8px',
                  border: '1px solid var(--glass-border-main)',
                }}
              >
                <div style={{ opacity: 0.7 }}>⏳ {t('aiPrompt.loadingPrompt')}</div>
              </div>
            ) : error ? (
              <div
                style={{
                  padding: '1rem',
                  background: 'rgba(220, 53, 69, 0.2)',
                  border: '1px solid #dc3545',
                  borderRadius: '8px',
                  color: '#dc3545',
                }}
              >
                {error}
              </div>
            ) : (
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                style={{
                  flex: 1,
                  minHeight: '400px',
                  background: 'var(--code-bg)',
                  border: '1px solid var(--glass-border-main)',
                  borderRadius: '8px',
                  padding: '1rem',
                  color: 'var(--code-text)',
                  fontFamily: "'Courier New', monospace",
                  fontSize: '0.9rem',
                  resize: 'vertical',
                  whiteSpace: 'pre-wrap',
                  wordWrap: 'break-word',
                }}
                placeholder={t('aiPrompt.placeholder')}
              />
            )}
          </div>

          <div
            style={{
              background: 'var(--glass-bg-main)',
              border: '1px solid var(--glass-border-main)',
              borderRadius: '8px',
              padding: '1rem',
            }}
          >
            <div style={{ marginBottom: '1rem', fontWeight: 600 }}>⚙️ {t('aiPrompt.settings')}:</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label style={{ marginBottom: '0.5rem', display: 'block' }}>{t('aiPrompt.language')}:</label>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  {(Object.keys(languages) as Language[]).map((lang) => (
                    <button
                      key={lang}
                      onClick={() => handleLanguageChange(lang)}
                      style={{
                        background:
                          promptLanguage === lang
                            ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                            : 'var(--glass-bg-main)',
                        border: `1px solid ${promptLanguage === lang ? '#667eea' : 'var(--glass-border-main)'}`,
                        padding: '0.5rem 1rem',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        fontWeight: promptLanguage === lang ? 600 : 400,
                      }}
                    >
                      {languages[lang].flag} {languages[lang].name}
                    </button>
                  ))}
                </div>
              </div>

              <div className="form-group" style={{ margin: 0 }}>
                <label style={{ marginBottom: '0.5rem', display: 'block' }}>{t('aiPrompt.policyPath')}:</label>
                <input
                  type="text"
                  value={policyPath}
                  onChange={(e) => setPolicyPath(e.target.value)}
                  placeholder=".scanning/finding-policy.json"
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    background: 'var(--glass-bg-main)',
                    border: '1px solid var(--glass-border-main)',
                    borderRadius: '8px',
                    color: 'var(--text-main)',
                  }}
                />
              </div>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                  gap: '0.75rem',
                }}
              >
                <div>
                  <label style={{ marginBottom: '0.35rem', display: 'block', fontSize: '0.9rem' }}>
                    {t('aiPrompt.minSeverity')}
                  </label>
                  <select value={minSeverity} onChange={(e) => setMinSeverity(e.target.value)} style={selectStyle}>
                    <option value="CRITICAL">{t('aiPrompt.severityCriticalOnly')}</option>
                    <option value="HIGH">{t('aiPrompt.severityCriticalHigh')}</option>
                    <option value="MEDIUM">{t('aiPrompt.severityMediumPlus')}</option>
                    <option value="LOW">{t('aiPrompt.severityLowPlus')}</option>
                    <option value="ALL">{t('aiPrompt.severityAll')}</option>
                  </select>
                </div>
                <div>
                  <label style={{ marginBottom: '0.35rem', display: 'block', fontSize: '0.9rem' }}>
                    {t('aiPrompt.filterTool')}
                  </label>
                  <input
                    type="text"
                    value={toolFilterDraft}
                    onChange={(e) => setToolFilterDraft(e.target.value)}
                    onBlur={commitToolFilter}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        commitToolFilter()
                      }
                    }}
                    placeholder={t('aiPrompt.allTools')}
                    style={selectStyle}
                    list="ai-prompt-tool-suggestions"
                  />
                  <datalist id="ai-prompt-tool-suggestions">
                    <option value="Semgrep" />
                    <option value="Bandit" />
                    <option value="Codeql" />
                    <option value="Eslint" />
                    <option value="Trivy" />
                  </datalist>
                </div>
                <div>
                  <label style={{ marginBottom: '0.35rem', display: 'block', fontSize: '0.9rem' }}>
                    {t('aiPrompt.sortBy')}
                  </label>
                  <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} style={selectStyle}>
                    <option value="severity">{t('aiPrompt.sortSeverity')}</option>
                    <option value="tool">{t('aiPrompt.sortTool')}</option>
                    <option value="path">{t('aiPrompt.sortPath')}</option>
                  </select>
                </div>
                <div>
                  <label style={{ marginBottom: '0.35rem', display: 'block', fontSize: '0.9rem' }}>
                    {t('aiPrompt.maxFindings')}
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={MAX_PROMPT_FINDINGS}
                    value={maxFindingsDraft}
                    onChange={(e) => setMaxFindingsDraft(e.target.value)}
                    onBlur={commitMaxFindings}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        commitMaxFindings()
                      }
                    }}
                    style={selectStyle}
                  />
                  <div style={{ marginTop: '0.25rem', fontSize: '0.75rem', opacity: 0.85 }}>
                    {t('aiPrompt.maxFindingsHint', { max: String(MAX_PROMPT_FINDINGS) })}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {promptData && !loading && !error && (
            <div
              style={{
                padding: '0.75rem',
                background: 'var(--glass-bg-main)',
                border: '1px solid var(--glass-border-main)',
                borderRadius: '8px',
                fontSize: '0.9rem',
                opacity: 0.9,
                lineHeight: 1.5,
              }}
            >
              {t('aiPrompt.statsDetail', {
                included: String(promptData.findings_count),
                breakdown: severityBreakdown(promptData.included_by_severity) || '—',
                matched: String(promptData.matched_findings ?? promptData.findings_count),
                total: String(promptData.total_findings ?? promptData.findings_count),
                tokens: estimateTokens(prompt).toLocaleString(),
              })}
            </div>
          )}

          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
            <button
              onClick={onClose}
              style={{
                background: 'var(--glass-bg-main)',
                border: '1px solid var(--glass-border-main)',
                padding: '0.75rem 1.5rem',
              }}
            >
              ❌ {t('common.cancel')}
            </button>
            <button
              onClick={handleCopy}
              disabled={!prompt || loading}
              className="primary"
              style={{
                padding: '0.75rem 1.5rem',
                fontWeight: 600,
              }}
            >
              {copied ? `✓ ${t('common.copied')}` : `📋 ${t('common.copy')}`}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
