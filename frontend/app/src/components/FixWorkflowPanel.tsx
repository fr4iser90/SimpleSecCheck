import { useState, useEffect, useMemo } from 'react'
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
import './FixWorkflowPanel.css'

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
    downloadTextFile(
      'simpleseccheck-example-github-actions.yml',
      buildExampleGithubActionsYaml(),
      'text/yaml;charset=utf-8'
    )
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

  return (
    <div className="fix-workflow">
      <fieldset className="fix-workflow__fieldset">
        <legend className="fix-workflow__legend">{t('fixTarget.stage2Title')}</legend>
        <p className="fix-workflow__blurb">{t('fixTarget.stage2Blurb')}</p>

        <div className="fix-workflow__inputs">
          <label className="fix-workflow__label">
            {t('fixTarget.baseBranch')}
            <input
              value={baseBranch}
              onChange={(e) => setBaseBranch(e.target.value)}
              disabled={disabled}
              className="fix-workflow__input"
            />
          </label>
          <label className="fix-workflow__label">
            {t('fixTarget.headBranch')}
            <input
              value={headBranch}
              onChange={(e) => setHeadBranch(e.target.value)}
              disabled={disabled}
              className="fix-workflow__input"
            />
          </label>
        </div>

        <div className="fix-workflow__btn-row">
          <button type="button" className="fix-workflow__btn" disabled={disabled || !draftPrompt.trim()} onClick={handleDownloadFixMd}>
            {t('fixTarget.downloadFixMd')}
          </button>
          <button type="button" className="fix-workflow__btn" disabled={disabled || !prBody} onClick={handleDownloadPrTemplate}>
            {t('fixTarget.downloadPrMd')}
          </button>
          <button type="button" className="fix-workflow__btn" disabled={disabled || !issueBody} onClick={handleDownloadIssueTemplate}>
            {t('fixTarget.downloadIssueMd')}
          </button>
          <button type="button" className="fix-workflow__btn" disabled={disabled} onClick={handleDownloadPatchWorkflow}>
            {t('fixTarget.downloadPatchWorkflow')}
          </button>
        </div>

        <div className="fix-workflow__btn-row fix-workflow__btn-row--tight">
          <button
            type="button"
            className="fix-workflow__btn"
            disabled={disabled}
            onClick={() => copyText('title', prTitle)}
          >
            {copied === 'title' ? `✓ ${t('fixTarget.copiedField')}` : t('fixTarget.copyPrTitle')}
          </button>
          <button
            type="button"
            className="fix-workflow__btn"
            disabled={disabled || !prBody}
            onClick={() => copyText('body', prBody)}
          >
            {copied === 'body' ? `✓ ${t('fixTarget.copiedField')}` : t('fixTarget.copyPrBody')}
          </button>
        </div>

        {parsed ? (
          <div className="fix-workflow__remote-block">
            <span className="fix-workflow__remote-text">
              {t('fixTarget.detectedRemote', { provider: parsed.provider, owner: parsed.owner, repo: parsed.repo })}
            </span>
            <div className="fix-workflow__btn-row">
              {issueUrl(parsed) && (
                <a
                  href={issueUrl(parsed)!}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="fix-workflow__btn fix-workflow__link-btn"
                >
                  {t('fixTarget.openNewIssue')}
                </a>
              )}
              {parsed.provider === 'github' && compareUrl(parsed) && (
                <a
                  href={compareUrl(parsed)!}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="fix-workflow__btn fix-workflow__link-btn"
                >
                  {t('fixTarget.openComparePr')}
                </a>
              )}
              {parsed.provider === 'gitlab' && (
                <a
                  href={gitlabNewMrUrl(parsed.host, parsed.owner, parsed.repo)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="fix-workflow__btn fix-workflow__link-btn"
                >
                  {t('fixTarget.openNewMr')}
                </a>
              )}
            </div>
          </div>
        ) : (
          <p className="fix-workflow__no-remote">{t('fixTarget.noParsedRemote')}</p>
        )}
      </fieldset>

      <fieldset className="fix-workflow__fieldset fix-workflow__fieldset--compact">
        <legend className="fix-workflow__legend">
          <button
            type="button"
            onClick={() => setShowStage3((s) => !s)}
            className="fix-workflow__toggle"
          >
            {showStage3 ? '▼' : '▶'} {t('fixTarget.stage3Title')}
          </button>
        </legend>
        {showStage3 && (
          <div className="fix-workflow__stage3">
            <p className="fix-workflow__blurb">{t('fixTarget.stage3Blurb')}</p>
            <pre className="fix-workflow__pre">{buildPatchInstructionsMarkdown(headBranch, baseBranch, target)}</pre>
            <div className="fix-workflow__btn-row">
              <button
                type="button"
                className="fix-workflow__btn"
                disabled={disabled}
                onClick={() => copyText('patch', buildPatchInstructionsMarkdown(headBranch, baseBranch, target))}
              >
                {copied === 'patch' ? `✓ ${t('fixTarget.copiedField')}` : t('fixTarget.copyPatchCommands')}
              </button>
              <button type="button" className="fix-workflow__btn" disabled={disabled} onClick={handleDownloadHybrid}>
                {t('fixTarget.downloadHybridMd')}
              </button>
              <button type="button" className="fix-workflow__btn" onClick={handleDownloadGha}>
                {t('fixTarget.downloadGhaExample')}
              </button>
            </div>
            <details className="fix-workflow__details">
              <summary className="fix-workflow__summary">{t('fixTarget.ghaPreview')}</summary>
              <pre className="fix-workflow__pre fix-workflow__pre--small">{buildExampleGithubActionsYaml()}</pre>
            </details>
          </div>
        )}
      </fieldset>
    </div>
  )
}
