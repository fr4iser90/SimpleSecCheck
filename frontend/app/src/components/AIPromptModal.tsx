import { useState, useEffect } from 'react'
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
  language: string
  policy_path: string
}

// Map UI language (en/zh/de) to backend prompt language (english/chinese/german)
const mapUILanguageToPromptLanguage = (uiLang: Language): string => {
  const mapping: Record<Language, string> = {
    en: 'english',
    zh: 'chinese',
    de: 'german',
  }
  return mapping[uiLang] || 'english'
}

export default function AIPromptModal({ isOpen, onClose, scanId }: AIPromptModalProps) {
  const { t, language: uiLanguage, setLanguage: setUILanguage, languages } = useTranslation()
  
  // Prompt language (for backend API)
  const [promptLanguage, setPromptLanguage] = useState<Language>(uiLanguage)
  const [policyPath, setPolicyPath] = useState('.scanning/finding-policy.json')
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [promptData, setPromptData] = useState<PromptData | null>(null)
  const [copied, setCopied] = useState(false)

  // Load prompt when modal opens or settings change
  useEffect(() => {
    if (isOpen) {
      loadPrompt()
    }
  }, [isOpen, promptLanguage, policyPath, scanId])

  const loadPrompt = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const backendLanguage = mapUILanguageToPromptLanguage(promptLanguage)
      const policyParam = `policy_path=${encodeURIComponent(policyPath || '.scanning/finding-policy.json')}`
      const endpoint = scanId
        ? `/api/results/${scanId}/ai-prompt?language=${backendLanguage}&${policyParam}`
        : `/api/scan/ai-prompt?language=${backendLanguage}&${policyParam}`

      const response = await fetch(resolveApiUrl(endpoint))
      
      if (response.ok) {
        const data: PromptData = await response.json()
        setPrompt(data.prompt)
        setPromptData(data)
      } else {
        const errorText = await response.text()
        setError(`${t('aiPrompt.failedToLoad')}: ${errorText}`)
        setPrompt('')
      }
    } catch (err) {
      setError(`${t('common.error')}: ${err instanceof Error ? err.message : 'Unknown error'}`)
      setPrompt('')
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
    setUILanguage(newLanguage) // Also update UI language
  }

  const estimateTokens = (text: string): number => {
    // Rough estimation: ~4 characters per token for English/German, ~2 for Chinese
    if (promptLanguage === 'zh') {
      return Math.ceil(text.length / 2)
    }
    return Math.ceil(text.length / 4)
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
        {/* Header */}
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

        {/* Content */}
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Prompt Preview */}
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

          {/* Settings */}
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
              {/* Language Selection */}
              <div className="form-group" style={{ margin: 0 }}>
                <label style={{ marginBottom: '0.5rem', display: 'block' }}>{t('aiPrompt.language')}:</label>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  {(Object.keys(languages) as Language[]).map((lang) => (
                    <button
                      key={lang}
                      onClick={() => handleLanguageChange(lang)}
                      style={{
                        background: promptLanguage === lang ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : 'var(--glass-bg-main)',
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

              {/* Policy Path */}
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
            </div>
          </div>

          {/* Stats */}
          {promptData && !loading && !error && (
            <div
              style={{
                display: 'flex',
                gap: '1rem',
                padding: '0.75rem',
                background: 'var(--glass-bg-main)',
                border: '1px solid var(--glass-border-main)',
                borderRadius: '8px',
                fontSize: '0.9rem',
                opacity: 0.8,
              }}
            >
              {t('aiPrompt.stats', {
                count: promptData.findings_count.toString(),
                tokens: estimateTokens(prompt).toLocaleString(),
              })}
            </div>
          )}

          {/* Actions */}
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
