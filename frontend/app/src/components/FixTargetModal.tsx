import { useState, useEffect, useMemo } from 'react'
import { useTranslation, type Language } from '../i18n'
import { apiFetch } from '../utils/apiClient'
import type { ScanTargetItem } from '../hooks/useTargets'
import {
  buildApproachPreamble,
  combineFixPrompt,
  formatTopSeverityLabel,
  type FixApproach,
} from '../utils/fixTargetPrompt'
import FixWorkflowPanel from './FixWorkflowPanel'
import './FixTargetModal.css'

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
  }, [isOpen, target, scanId, uiLanguage, policyPath])

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
  const approachOptions: FixApproach[] = ['quick', 'pr_ready', 'explain']
  const isQuickApproach = approach === 'quick'
  const isPrReadyApproach = approach === 'pr_ready'

  return (
    <div
      className="fix-target-modal__overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        className="fix-target-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="fix-target-title"
      >
        <div className="fix-target-modal__header">
          <h2 id="fix-target-title" className="fix-target-modal__title">
            🔧 {t('fixTarget.title')}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="fix-target-modal__close"
            title={t('common.close')}
          >
            ✕
          </button>
        </div>

        {!scanId ? (
          <>
            <div className="fix-target-modal__body">
              <p className="fix-target-modal__no-scan">{t('fixTarget.noScan')}</p>
            </div>
            <div className="fix-target-modal__actions">
              <button type="button" onClick={onClose} className="fix-target-modal__action-btn">
                {t('common.close')}
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="fix-target-modal__body">
              <div className="fix-target-modal__meta">
                <div>
                  <strong>{t('fixTarget.severity')}:</strong>{' '}
                  <span className="fix-target-modal__severity">{formatTopSeverityLabel(target)}</span>
                </div>
                <div className="fix-target-modal__meta-secondary">
                  <strong>{t('fixTarget.targetLabel')}:</strong> {label.length > 80 ? label.slice(0, 80) + '…' : label}
                </div>
              </div>

              <fieldset className="fix-target-modal__fieldset">
                <legend className="fix-target-modal__legend">{t('fixTarget.approach')}</legend>
                <div className="fix-target-modal__approach-list">
                  {approachOptions.map((key) => (
                    <label
                      key={key}
                      className={`fix-target-modal__approach-option ${
                        approach === key ? 'is-selected' : ''
                      }`}
                    >
                      <input
                        type="radio"
                        name="fix-approach"
                        checked={approach === key}
                        onChange={() => setApproach(key)}
                      />
                      <span className="fix-target-modal__approach-label">{t(`fixTarget.${key}`)}</span>
                    </label>
                  ))}
                </div>
              </fieldset>

              {!isQuickApproach && (
                <div className="fix-target-modal__group">
                  <label className="fix-target-modal__label">{t('fixTarget.policyPath')}</label>
                  <input
                    type="text"
                    value={policyPath}
                    onChange={(e) => setPolicyPath(e.target.value)}
                    className="fix-target-modal__input"
                  />
                </div>
              )}

              <div className="fix-target-modal__prompt">
                <label className="fix-target-modal__prompt-label">{t('fixTarget.generatedPrompt')}</label>
                {loading ? (
                  <div className="fix-target-modal__loading">{t('fixTarget.loading')}</div>
                ) : error ? (
                  <div className="fix-target-modal__error">{error}</div>
                ) : (
                  <textarea
                    value={draftPrompt}
                    onChange={(e) => setDraftPrompt(e.target.value)}
                    className="fix-target-modal__textarea"
                  />
                )}
              </div>

              {isPrReadyApproach && (
                <FixWorkflowPanel
                  target={target}
                  draftPrompt={draftPrompt}
                  scanId={scanId}
                  disabled={loading || !!error}
                />
              )}

              <p className="fix-target-modal__hint">{t('fixTarget.hint')}</p>
            </div>

            <div className="fix-target-modal__actions">
              <button type="button" onClick={onClose} className="fix-target-modal__action-btn">
                {t('common.cancel')}
              </button>
              {reportPath && (
                <a
                  href={reportPath}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={onClose}
                  className="fix-target-modal__action-link"
                >
                  {t('fixTarget.openReport')}
                </a>
              )}
              <button
                type="button"
                className="primary fix-target-modal__action-btn"
                onClick={handleCopy}
                disabled={!draftPrompt.trim() || loading}
              >
                {copied ? `✓ ${t('fixTarget.copied')}` : `📋 ${t('fixTarget.copy')}`}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
