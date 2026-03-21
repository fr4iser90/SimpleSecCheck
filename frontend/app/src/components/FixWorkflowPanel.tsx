import { useState, useEffect, useMemo, type CSSProperties } from 'react'
import { useTranslation } from '../i18n'
import type { ScanTargetItem } from '../hooks/useTargets'
import {
  parseGitRemoteUrl,
  downloadTextFile,
  githubNewIssueUrl,
  githubComparePrUrl,
  gitlabNewIssueUrl,
  gitlabNewMrUrl,
  type ParsedRepo,
} from '../utils/gitWorkflow'
import {
  suggestedHeadBranch,
  defaultBaseBranch,
  buildPRTitle,
  buildIssueTitle,
  buildPRBodyMarkdown,
  buildIssueBodyMarkdown,
  buildPatchInstructionsMarkdown,
  buildHybridReadmeMarkdown,
  buildExampleGithubActionsYaml,
} from '../utils/fixWorkflowTemplates'

interface FixWorkflowPanelProps {
  target: ScanTargetItem
  draftPrompt: string
  scanId: string
  /** Hide exports when prompt not ready */
  disabled: boolean
}

export default function FixWorkflowPanel({ target, draftPrompt, scanId, disabled }: FixWorkflowPanelProps) {
  const { t } = useTranslation()
  const [baseBranch, setBaseBranch] = useState(() => defaultBaseBranch(target))
  const [headBranch, setHeadBranch] = useState(() => suggestedHeadBranch(target))
  const [copied, setCopied] = useState<string | null>(null)
  const [showStage3, setShowStage3] = useState(false)

  useEffect(() => {
    setBaseBranch(defaultBaseBranch(target))
    setHeadBranch(suggestedHeadBranch(target))
  }, [target.id])

  const parsed = useMemo(() => parseGitRemoteUrl(target.source), [target.source])

  const prTitle = useMemo(() => buildPRTitle(target), [target])
  const prBody = useMemo(
    () => (draftPrompt.trim() ? buildPRBodyMarkdown(draftPrompt, target, scanId) : ''),
    [draftPrompt, target, scanId]
  )
  const issueTitle = useMemo(() => buildIssueTitle(target), [target])
  const issueBody = useMemo(
    () => (draftPrompt.trim() ? buildIssueBodyMarkdown(draftPrompt, target, scanId) : ''),
    [draftPrompt, target, scanId]
  )

  const safeName = (target.display_name || target.source).replace(/[^a-zA-Z0-9._-]+/g, '-').slice(0, 48)

  const copyText = async (key: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(key)
      window.setTimeout(() => setCopied(null), 2000)
    } catch {
      alert(t('common.error'))
    }
  }

  const handleDownloadFixMd = () => {
    if (!draftPrompt.trim()) return
    downloadTextFile(`simpleseccheck-fix-${safeName}.md`, draftPrompt)
  }

  const handleDownloadPrTemplate = () => {
    if (!prBody) return
    const md = `# ${prTitle}\n\n${prBody}`
    downloadTextFile(`simpleseccheck-pr-${safeName}.md`, md)
  }

  const handleDownloadIssueTemplate = () => {
    if (!issueBody) return
    const md = `# ${issueTitle}\n\n${issueBody}`
    downloadTextFile(`simpleseccheck-issue-${safeName}.md`, md)
  }

  const handleDownloadPatchWorkflow = () => {
    const md = buildPatchInstructionsMarkdown(headBranch, baseBranch, target)
    downloadTextFile(`simpleseccheck-patch-workflow-${safeName}.md`, md)
  }

  const handleDownloadHybrid = () => {
    downloadTextFile(`simpleseccheck-hybrid-workflow.md`, buildHybridReadmeMarkdown())
  }

  const handleDownloadGha = () => {
    downloadTextFile(`simpleseccheck-example-github-actions.yml`, buildExampleGithubActionsYaml(), 'text/yaml;charset=utf-8')
  }

  const issueUrl = (p: ParsedRepo): string | null => {
    if (!issueTitle || !issueBody) return null
    if (p.provider === 'github') return githubNewIssueUrl(p.owner, p.repo, issueTitle, issueBody)
    return gitlabNewIssueUrl(p.host, p.owner, p.repo, issueTitle, issueBody)
  }

  const compareUrl = (p: ParsedRepo): string | null => {
    if (p.provider !== 'github') return null
    return githubComparePrUrl(p.owner, p.repo, baseBranch, headBranch)
  }

  const btnStyle: CSSProperties = {
    fontSize: '0.8rem',
    padding: '0.4rem 0.65rem',
    borderRadius: '6px',
    border: '1px solid var(--glass-border-main)',
    background: 'var(--glass-bg-main)',
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.55 : 1,
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1rem' }}>
      <fieldset
        style={{
          border: '1px solid var(--glass-border-main)',
          borderRadius: '8px',
          padding: '1rem',
          margin: 0,
        }}
      >
        <legend style={{ padding: '0 0.5rem', fontWeight: 600 }}>{t('fixTarget.stage2Title')}</legend>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: 0 }}>{t('fixTarget.stage2Blurb')}</p>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '0.75rem' }}>
          <label style={{ fontSize: '0.85rem' }}>
            {t('fixTarget.baseBranch')}
            <input
              value={baseBranch}
              onChange={(e) => setBaseBranch(e.target.value)}
              disabled={disabled}
              style={{
                width: '100%',
                marginTop: '0.25rem',
                padding: '0.4rem 0.5rem',
                borderRadius: '6px',
                border: '1px solid var(--glass-border-main)',
                background: 'var(--glass-bg-main)',
                color: 'var(--text-main)',
              }}
            />
          </label>
          <label style={{ fontSize: '0.85rem' }}>
            {t('fixTarget.headBranch')}
            <input
              value={headBranch}
              onChange={(e) => setHeadBranch(e.target.value)}
              disabled={disabled}
              style={{
                width: '100%',
                marginTop: '0.25rem',
                padding: '0.4rem 0.5rem',
                borderRadius: '6px',
                border: '1px solid var(--glass-border-main)',
                background: 'var(--glass-bg-main)',
                color: 'var(--text-main)',
              }}
            />
          </label>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.75rem' }}>
          <button type="button" style={btnStyle} disabled={disabled || !draftPrompt.trim()} onClick={handleDownloadFixMd}>
            {t('fixTarget.downloadFixMd')}
          </button>
          <button type="button" style={btnStyle} disabled={disabled || !prBody} onClick={handleDownloadPrTemplate}>
            {t('fixTarget.downloadPrMd')}
          </button>
          <button type="button" style={btnStyle} disabled={disabled || !issueBody} onClick={handleDownloadIssueTemplate}>
            {t('fixTarget.downloadIssueMd')}
          </button>
          <button type="button" style={btnStyle} disabled={disabled} onClick={handleDownloadPatchWorkflow}>
            {t('fixTarget.downloadPatchWorkflow')}
          </button>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.5rem', alignItems: 'center' }}>
          <button
            type="button"
            style={btnStyle}
            disabled={disabled}
            onClick={() => copyText('title', prTitle)}
          >
            {copied === 'title' ? `✓ ${t('fixTarget.copiedField')}` : t('fixTarget.copyPrTitle')}
          </button>
          <button
            type="button"
            style={btnStyle}
            disabled={disabled || !prBody}
            onClick={() => copyText('body', prBody)}
          >
            {copied === 'body' ? `✓ ${t('fixTarget.copiedField')}` : t('fixTarget.copyPrBody')}
          </button>
        </div>

        {parsed ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              {t('fixTarget.detectedRemote', { provider: parsed.provider, owner: parsed.owner, repo: parsed.repo })}
            </span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              {issueUrl(parsed) && (
                <a
                  href={issueUrl(parsed)!}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ ...btnStyle, display: 'inline-flex', alignItems: 'center', textDecoration: 'none', color: 'var(--accent, #0d6efd)' }}
                >
                  {t('fixTarget.openNewIssue')}
                </a>
              )}
              {parsed.provider === 'github' && compareUrl(parsed) && (
                <a
                  href={compareUrl(parsed)!}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ ...btnStyle, display: 'inline-flex', alignItems: 'center', textDecoration: 'none', color: 'var(--accent, #0d6efd)' }}
                >
                  {t('fixTarget.openComparePr')}
                </a>
              )}
              {parsed.provider === 'gitlab' && (
                <a
                  href={gitlabNewMrUrl(parsed.host, parsed.owner, parsed.repo)}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ ...btnStyle, display: 'inline-flex', alignItems: 'center', textDecoration: 'none', color: 'var(--accent, #0d6efd)' }}
                >
                  {t('fixTarget.openNewMr')}
                </a>
              )}
            </div>
          </div>
        ) : (
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0 }}>{t('fixTarget.noParsedRemote')}</p>
        )}
      </fieldset>

      <fieldset
        style={{
          border: '1px solid var(--glass-border-main)',
          borderRadius: '8px',
          padding: '0.75rem 1rem',
          margin: 0,
        }}
      >
        <legend style={{ padding: '0 0.5rem', fontWeight: 600 }}>
          <button
            type="button"
            onClick={() => setShowStage3((s) => !s)}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--text-main)',
              font: 'inherit',
              fontWeight: 600,
              padding: 0,
            }}
          >
            {showStage3 ? '▼' : '▶'} {t('fixTarget.stage3Title')}
          </button>
        </legend>
        {showStage3 && (
          <div style={{ marginTop: '0.75rem' }}>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: 0 }}>{t('fixTarget.stage3Blurb')}</p>
            <pre
              style={{
                fontSize: '0.75rem',
                padding: '0.75rem',
                borderRadius: '6px',
                background: 'var(--code-bg)',
                overflow: 'auto',
                maxHeight: '140px',
                border: '1px solid var(--glass-border-main)',
              }}
            >
              {buildPatchInstructionsMarkdown(headBranch, baseBranch, target)}
            </pre>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <button
                type="button"
                style={btnStyle}
                disabled={disabled}
                onClick={() =>
                  copyText('patch', buildPatchInstructionsMarkdown(headBranch, baseBranch, target))
                }
              >
                {copied === 'patch' ? `✓ ${t('fixTarget.copiedField')}` : t('fixTarget.copyPatchCommands')}
              </button>
              <button type="button" style={btnStyle} disabled={disabled} onClick={handleDownloadHybrid}>
                {t('fixTarget.downloadHybridMd')}
              </button>
              <button type="button" style={btnStyle} onClick={handleDownloadGha}>
                {t('fixTarget.downloadGhaExample')}
              </button>
            </div>
            <details style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              <summary style={{ cursor: 'pointer', marginBottom: '0.35rem' }}>{t('fixTarget.ghaPreview')}</summary>
              <pre
                style={{
                  fontSize: '0.72rem',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  background: 'var(--code-bg)',
                  overflow: 'auto',
                  maxHeight: '160px',
                }}
              >
                {buildExampleGithubActionsYaml()}
              </pre>
            </details>
          </div>
        )}
      </fieldset>
    </div>
  )
}
