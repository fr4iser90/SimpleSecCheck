import { useState, useEffect, useMemo } from 'react'
import { useTranslation, Language } from '../i18n'
import { apiFetch } from '../utils/apiClient'
import type { ScanTargetItem } from '../hooks/useTargets'
import {
  buildApproachPreamble,
  combineFixPrompt,
  formatTopSeverityLabel,
  type FixApproach,
} from '../utils/fixTargetPrompt'
import FixWorkflowPanel from './FixWorkflowPanel'

interface FixTargetModalProps {
  isOpen: boolean
  onClose: () => void
  target: ScanTargetItem | null
}

interface PromptPayload {
  prompt: string
  findings_count: number
  language: string
  policy_path: string
}

const mapUILanguageToPromptLanguage = (uiLang: Language): string => {
  const mapping: Record<Language, string> = {
    en: 'english',
    zh: 'chinese',
    de: 'german',
  }
  return mapping[uiLang] || 'english'
}

export default function FixTargetModal({ isOpen, onClose, target }: FixTargetModalProps) {
  const { t, language: uiLanguage } = useTranslation()
  const [approach, setApproach] = useState<FixApproach>('quick')
  const [remotePrompt, setRemotePrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [policyPath, setPolicyPath] = useState('.scanning/finding-policy.json')

  const scanId = target?.last_scan?.scan_id ?? null
  const reportPath =
    target?.last_scan && (target.last_scan.status === 'completed' || target.last_scan.status === 'failed')
      ? `/api/results/${target.last_scan.scan_id}/report`
      : null

  const fullPrompt = useMemo(() => {
    if (!target || !remotePrompt.trim()) return ''
    const preamble = buildApproachPreamble(approach, target)
    return combineFixPrompt(preamble, remotePrompt)
  }, [approach, target, remotePrompt])

  const [draftPrompt, setDraftPrompt] = useState('')
  useEffect(() => {
    setDraftPrompt(fullPrompt)
  }, [fullPrompt])

  useEffect(() => {
    if (!isOpen || !target || !scanId) {
      setRemotePrompt('')
      setError(null)
      return
    }

    let cancelled = false
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const backendLanguage = mapUILanguageToPromptLanguage(uiLanguage)
        const policyParam = `policy_path=${encodeURIComponent(policyPath || '.scanning/finding-policy.json')}`
        const res = await apiFetch(
          `/api/results/${scanId}/ai-prompt?language=${encodeURIComponent(backendLanguage)}&${policyParam}`
        )
        if (cancelled) return
        if (res.ok) {
          const data = (await res.json()) as PromptPayload
          setRemotePrompt(data.prompt)
        } else {
          const text = await res.text().catch(() => '')
          setError(text || t('fixTarget.loadError'))
          setRemotePrompt('')
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : t('common.error'))
          setRemotePrompt('')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void load()
    return () => {
      cancelled = true
    }
  }, [isOpen, target, scanId, uiLanguage, policyPath, t])

  useEffect(() => {
    if (isOpen) {
      setApproach('quick')
      setCopied(false)
    }
  }, [isOpen, target?.id])

  const handleCopy = async () => {
    if (!draftPrompt.trim()) return
    try {
      await navigator.clipboard.writeText(draftPrompt)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      alert(t('common.error'))
    }
  }

  if (!isOpen || !target) return null

  const label = target.display_name || target.source

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
        if (e.target === e.currentTarget) onClose()
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
          maxWidth: '920px',
          width: '100%',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          position: 'relative',
        }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="fix-target-title"
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '1rem',
            borderBottom: '1px solid var(--glass-border-main)',
            paddingBottom: '1rem',
          }}
        >
          <h2 id="fix-target-title" style={{ margin: 0 }}>
            🔧 {t('fixTarget.title')}
          </h2>
          <button
            type="button"
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

        {!scanId ? (
          <p style={{ color: 'var(--text-secondary)' }}>{t('fixTarget.noScan')}</p>
        ) : (
          <>
            <div style={{ marginBottom: '1rem', fontSize: '0.95rem' }}>
              <div>
                <strong>{t('fixTarget.severity')}:</strong>{' '}
                <span style={{ color: 'var(--color-critical, #dc3545)' }}>{formatTopSeverityLabel(target)}</span>
              </div>
              <div style={{ marginTop: '0.35rem' }}>
                <strong>{t('fixTarget.targetLabel')}:</strong> {label.length > 80 ? label.slice(0, 80) + '…' : label}
              </div>
            </div>

            <fieldset style={{ border: '1px solid var(--glass-border-main)', borderRadius: '8px', padding: '1rem', marginBottom: '1rem' }}>
              <legend style={{ padding: '0 0.5rem', fontWeight: 600 }}>{t('fixTarget.approach')}</legend>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {(['quick', 'pr_ready', 'explain'] as const).map((key) => (
                  <label
                    key={key}
                    style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}
                  >
                    <input
                      type="radio"
                      name="fix-approach"
                      checked={approach === key}
                      onChange={() => setApproach(key)}
                    />
                    {t(`fixTarget.${key}`)}
                  </label>
                ))}
              </div>
            </fieldset>

            <div className="form-group" style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.35rem', fontSize: '0.85rem' }}>{t('fixTarget.policyPath')}</label>
              <input
                type="text"
                value={policyPath}
                onChange={(e) => setPolicyPath(e.target.value)}
                style={{
                  width: '100%',
                  maxWidth: '100%',
                  padding: '0.5rem 0.75rem',
                  borderRadius: '6px',
                  border: '1px solid var(--glass-border-main)',
                  background: 'var(--glass-bg-main)',
                  color: 'var(--text-main)',
                }}
              />
            </div>

            <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', marginBottom: '1rem' }}>
              <label style={{ marginBottom: '0.5rem', fontWeight: 600 }}>{t('fixTarget.generatedPrompt')}</label>
              {loading ? (
                <div
                  style={{
                    padding: '2rem',
                    textAlign: 'center',
                    background: 'var(--glass-bg-main)',
                    borderRadius: '8px',
                    border: '1px solid var(--glass-border-main)',
                  }}
                >
                  {t('fixTarget.loading')}
                </div>
              ) : error ? (
                <div
                  style={{
                    padding: '1rem',
                    background: 'rgba(220, 53, 69, 0.15)',
                    border: '1px solid var(--color-critical, #dc3545)',
                    borderRadius: '8px',
                    color: 'var(--color-critical, #dc3545)',
                  }}
                >
                  {error}
                </div>
              ) : (
                <textarea
                  value={draftPrompt}
                  onChange={(e) => setDraftPrompt(e.target.value)}
                  style={{
                    flex: 1,
                    minHeight: '320px',
                    background: 'var(--code-bg)',
                    border: '1px solid var(--glass-border-main)',
                    borderRadius: '8px',
                    padding: '1rem',
                    color: 'var(--code-text)',
                    fontFamily: "'Courier New', monospace",
                    fontSize: '0.85rem',
                    resize: 'vertical',
                    whiteSpace: 'pre-wrap',
                    wordWrap: 'break-word',
                  }}
                />
              )}
            </div>

            <FixWorkflowPanel
              target={target}
              draftPrompt={draftPrompt}
              scanId={scanId}
              disabled={loading || !!error}
            />

            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>{t('fixTarget.hint')}</p>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', justifyContent: 'flex-end' }}>
              <button type="button" onClick={onClose} style={{ padding: '0.65rem 1.25rem' }}>
                {t('common.cancel')}
              </button>
              {reportPath && (
                <a
                  href={reportPath}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={onClose}
                  style={{
                    padding: '0.65rem 1.25rem',
                    borderRadius: '6px',
                    border: '1px solid var(--glass-border-main)',
                    color: 'var(--text-main)',
                    textDecoration: 'none',
                    display: 'inline-flex',
                    alignItems: 'center',
                  }}
                >
                  {t('fixTarget.openReport')}
                </a>
              )}
              <button
                type="button"
                className="primary"
                onClick={handleCopy}
                disabled={!draftPrompt.trim() || loading}
                style={{ padding: '0.65rem 1.25rem' }}
              >
                {copied ? `✓ ${t('fixTarget.copied')}` : `📋 ${t('fixTarget.copy')}`}
              </button>
            </div>
          </>
        )}

        {!scanId && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1rem' }}>
            <button type="button" onClick={onClose} style={{ padding: '0.65rem 1.25rem' }}>
              {t('common.close')}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
