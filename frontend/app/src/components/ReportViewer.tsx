import { useCallback, useEffect, useMemo, useState } from 'react'
import AIPromptModal from './AIPromptModal'
import { resolveApiUrl } from '../utils/resolveApiUrl'
import { computeSecurityScore } from '../utils/securityScore'
import {
  ExecutedTool,
  formatReportTimestamp,
  overallStatusFromCounts,
  resolveFindingPolicyPath,
  stepsToExecutedTools,
  toolsProgress,
} from '../utils/reportTools'
import '../styles/scan-report.css'

const PAGE_SIZE = 100

interface FindingSummary {
  total_vulnerabilities: number
  critical_vulnerabilities: number
  high_vulnerabilities: number
  medium_vulnerabilities: number
  low_vulnerabilities: number
  info_vulnerabilities: number
}

interface FindingItem {
  tool: string
  policy_key?: string
  severity: string
  path: string
  line: string
  message: string
  rule_id: string
  cwe?: string | null
  fix_hint?: string | null
}

interface FindingsPagination {
  total: number
  returned: number
  has_more: boolean
  next_path?: string | null
}

interface FindingsResponse {
  scan_id: string
  status: string
  generated_at?: string | null
  findings: FindingItem[]
  summary: FindingSummary
  pagination?: FindingsPagination | null
  source: string
}

interface ScanMeta {
  id: string
  name?: string
  target_url?: string
  completed_at?: string | null
  metadata?: Record<string, unknown>
}

interface ReportViewerProps {
  scanId?: string | null
}

function severityColor(severity: string): string {
  switch (severity.toUpperCase()) {
    case 'CRITICAL':
      return 'var(--color-critical)'
    case 'HIGH':
      return 'var(--color-high)'
    case 'MEDIUM':
      return 'var(--color-medium)'
    case 'LOW':
      return 'var(--color-low)'
    default:
      return 'var(--color-info)'
  }
}

function SeverityPill({ severity }: { severity: string }) {
  return (
    <span
      className="scan-report__sev-pill"
      style={{ ['--scan-report-severity-color' as string]: severityColor(severity) }}
    >
      {severity}
    </span>
  )
}

function StatusBadge({ status }: { status: 'Critical' | 'High' | 'OK' }) {
  const cls =
    status === 'Critical'
      ? 'scan-report__badge scan-report__badge--critical'
      : status === 'High'
        ? 'scan-report__badge scan-report__badge--high'
        : 'scan-report__badge scan-report__badge--ok'
  return <span className={cls}>{status}</span>
}

function ToolStatusRow({ tool }: { tool: ExecutedTool }) {
  const statusClass = `scan-report__tool-item scan-report__tool-item--${tool.status}`
  const statusLabel =
    tool.status === 'complete'
      ? 'completed'
      : tool.status === 'skipped'
        ? 'skipped'
        : tool.status
  const msgShort =
    tool.message.length > 72 ? `${tool.message.slice(0, 72)}…` : tool.message

  return (
    <div className={statusClass} title={tool.message || undefined}>
      <span className="scan-report__tool-dot" aria-hidden />
      <div className="scan-report__tool-text">
        <span className="scan-report__tool-name">{tool.name}</span>
        {tool.message ? (
          <span className="scan-report__tool-msg">({msgShort})</span>
        ) : tool.status === 'complete' ? (
          <span className="scan-report__tool-msg">({tool.name} scan completed)</span>
        ) : (
          <span className="scan-report__tool-msg">({statusLabel})</span>
        )}
      </div>
    </div>
  )
}

export default function ReportViewer({ scanId }: ReportViewerProps) {
  const [scanMeta, setScanMeta] = useState<ScanMeta | null>(null)
  const [executedTools, setExecutedTools] = useState<ExecutedTool[]>([])
  const [summary, setSummary] = useState<FindingSummary | null>(null)
  const [findings, setFindings] = useState<FindingItem[]>([])
  const [generatedAt, setGeneratedAt] = useState<string | null>(null)
  const [source, setSource] = useState<string>('file')
  const [metaLoading, setMetaLoading] = useState(true)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [nextPath, setNextPath] = useState<string | null>(null)
  const [totalFiltered, setTotalFiltered] = useState(0)
  const [isAiModalOpen, setIsAiModalOpen] = useState(false)

  const [severityFilter, setSeverityFilter] = useState('')
  const [toolFilter, setToolFilter] = useState('')
  const [pathSearch, setPathSearch] = useState('')

  const toolOptions = useMemo(() => {
    const tools = new Set(findings.map((f) => f.tool).filter(Boolean))
    return Array.from(tools).sort((a, b) => a.localeCompare(b))
  }, [findings])

  const policyPath = useMemo(
    () => resolveFindingPolicyPath(scanMeta?.metadata),
    [scanMeta?.metadata],
  )

  const securityScore = useMemo(() => {
    if (!summary) return null
    return computeSecurityScore({
      critical: summary.critical_vulnerabilities,
      high: summary.high_vulnerabilities,
      medium: summary.medium_vulnerabilities,
      low: summary.low_vulnerabilities,
      info: summary.info_vulnerabilities,
    })
  }, [summary])

  const overallStatus = useMemo(() => {
    if (!summary) return 'OK' as const
    return overallStatusFromCounts(
      summary.critical_vulnerabilities,
      summary.high_vulnerabilities,
    )
  }, [summary])

  const { total: toolsTotal, passed: toolsPassed } = useMemo(
    () => toolsProgress(executedTools),
    [executedTools],
  )

  const reportTimestamp = useMemo(() => {
    const iso = scanMeta?.completed_at ?? generatedAt
    return formatReportTimestamp(iso)
  }, [scanMeta?.completed_at, generatedAt])

  const buildQuery = useCallback(
    (offset: number) => {
      const params = new URLSearchParams()
      params.set('limit', String(PAGE_SIZE))
      params.set('offset', String(offset))
      if (severityFilter) params.set('severity', severityFilter)
      if (toolFilter) params.set('tool', toolFilter)
      if (pathSearch.trim()) params.set('path_prefix', pathSearch.trim())
      return `/api/v1/scans/${encodeURIComponent(scanId!)}/findings?${params.toString()}`
    },
    [scanId, severityFilter, toolFilter, pathSearch],
  )

  useEffect(() => {
    if (!scanId) return
    let cancelled = false
    setMetaLoading(true)

    void (async () => {
      try {
        const { apiFetch } = await import('../utils/apiClient')
        const [scanRes, stepsRes] = await Promise.all([
          apiFetch(`/api/v1/scans/${encodeURIComponent(scanId)}`),
          apiFetch(`/api/v1/scans/${encodeURIComponent(scanId)}/steps`),
        ])
        if (cancelled) return

        if (scanRes.ok) {
          const scan = (await scanRes.json()) as ScanMeta
          setScanMeta(scan)
        }

        if (stepsRes.ok) {
          const stepsData = (await stepsRes.json()) as { steps?: Array<{ name?: string; status?: string; message?: string }> }
          setExecutedTools(stepsToExecutedTools(stepsData.steps ?? []))
        }
      } catch {
        /* non-fatal: report still works from findings alone */
      } finally {
        if (!cancelled) setMetaLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [scanId])

  const loadFindings = useCallback(
    async (append = false, pathOverride?: string) => {
      if (!scanId) return
      if (append) setLoadingMore(true)
      else setLoading(true)
      setError(null)

      try {
        const { apiFetch } = await import('../utils/apiClient')
        const url = pathOverride ?? buildQuery(append ? findings.length : 0)
        const response = await apiFetch(url)
        if (!response.ok) {
          let msg = `Failed to load findings (${response.status})`
          try {
            const j = await response.json()
            const d = j.detail
            msg = typeof d === 'string' ? d : msg
          } catch {
            /* ignore */
          }
          throw new Error(msg)
        }
        const data = (await response.json()) as FindingsResponse
        setSummary(data.summary)
        setGeneratedAt(data.generated_at ?? null)
        setSource(data.source)
        setFindings((prev) => (append ? [...prev, ...data.findings] : data.findings))
        setTotalFiltered(data.pagination?.total ?? data.findings.length)
        setNextPath(data.pagination?.has_more ? data.pagination.next_path ?? null : null)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load report')
        if (!append) {
          setFindings([])
          setSummary(null)
        }
      } finally {
        setLoading(false)
        setLoadingMore(false)
      }
    },
    [scanId, buildQuery, findings.length],
  )

  useEffect(() => {
    if (!scanId) return
    void loadFindings(false)
  }, [scanId, severityFilter, toolFilter, pathSearch])

  const handleShareLink = async () => {
    if (!scanId) return
    try {
      const { apiFetch } = await import('../utils/apiClient')
      const res = await apiFetch(`/api/v1/scans/${scanId}/report-share-link`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ regenerate: false }),
      })
      if (!res.ok) throw new Error(`Share link failed (${res.status})`)
      const data = (await res.json()) as { share_path: string }
      await navigator.clipboard.writeText(`${window.location.origin}${data.share_path}`)
      window.alert('Share link copied.')
    } catch (e) {
      window.alert(e instanceof Error ? e.message : 'Could not copy share link')
    }
  }

  const aiPromptDisabled = !summary || summary.total_vulnerabilities === 0

  if (!scanId) {
    return (
      <div className="scan-report__empty panel">
        <div className="panel__body">No scan selected.</div>
      </div>
    )
  }

  if ((loading || metaLoading) && findings.length === 0 && !summary) {
    return (
      <div className="scan-report">
        <div className="panel">
          <div className="panel__body scan-report__empty">Loading report…</div>
        </div>
      </div>
    )
  }

  if (error && findings.length === 0 && !summary) {
    return (
      <div className="scan-report">
        <div className="panel">
          <div className="panel__body">
            <p className="error-message" role="alert">{error}</p>
            <button type="button" className="btn-secondary" onClick={() => void loadFindings(false)}>
              Retry
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="scan-report">
      <div className="scan-report__hero panel">
        <div className="panel__body">
          <div className="scan-report__header">
            <div className="scan-report__title-block">
              <h2 className="scan-report__headline">
                SimpleSecCheck Security Scan Summary
                <StatusBadge status={overallStatus} />
              </h2>
              <p className="scan-report__meta">
                {scanId}
                {reportTimestamp ? ` · ${reportTimestamp}` : ''}
                {source ? ` · ${source}` : ''}
              </p>
              {scanMeta?.target_url && (
                <p className="scan-report__target" title={scanMeta.target_url}>
                  Target: {scanMeta.name ?? scanMeta.target_url}
                </p>
              )}
            </div>
            <div className="scan-report__actions">
              <button
                type="button"
                className="btn-primary scan-report__ai-btn"
                disabled={aiPromptDisabled}
                title={aiPromptDisabled ? 'No findings available for AI prompt.' : 'Generate AI remediation prompt'}
                onClick={() => setIsAiModalOpen(true)}
              >
                AI Prompt
              </button>
              <a
                href={resolveApiUrl(`/api/results/${scanId}/report`)}
                className="btn-secondary"
                target="_blank"
                rel="noopener noreferrer"
              >
                Export HTML
              </a>
              <button type="button" className="btn-secondary" onClick={() => void handleShareLink()}>
                Copy share link
              </button>
            </div>
          </div>

          {summary && securityScore && (
            <div className="scan-report__summary-grid">
              <div
                className="scan-report__summary-card scan-report__summary-card--critical"
                style={{ ['--scan-report-severity-color' as string]: 'var(--color-critical)' }}
              >
                <strong>{summary.critical_vulnerabilities}</strong>
                <span>Critical Issues</span>
              </div>
              <div
                className="scan-report__summary-card scan-report__summary-card--high"
                style={{ ['--scan-report-severity-color' as string]: 'var(--color-high)' }}
              >
                <strong>{summary.high_vulnerabilities}</strong>
                <span>High Severity</span>
              </div>
              <div
                className="scan-report__summary-card scan-report__summary-card--medium"
                style={{ ['--scan-report-severity-color' as string]: 'var(--color-medium)' }}
              >
                <strong>{summary.medium_vulnerabilities}</strong>
                <span>Medium Severity</span>
              </div>
              <div className="scan-report__summary-card scan-report__summary-card--tools">
                <strong>{toolsTotal > 0 ? `${toolsPassed}/${toolsTotal}` : '—'}</strong>
                <span>Tools Complete</span>
              </div>
              <div
                className="scan-report__score-banner"
                style={{ ['--scan-report-score-color' as string]: securityScore.color }}
              >
                <div className="scan-report__score-value">
                  {securityScore.score}
                  <span className="scan-report__score-denom">/ 100</span>
                </div>
                <div className="scan-report__score-label">
                  Security Score: {securityScore.label}
                </div>
              </div>
            </div>
          )}

          {aiPromptDisabled && (
            <p className="scan-report__hint">No findings available</p>
          )}
        </div>
      </div>

      {executedTools.length > 0 && (
        <div className="panel">
          <div className="panel__header">
            <h3 className="panel__title">Scans Executed</h3>
          </div>
          <div className="panel__body">
            <p className="scan-report__section-lead">
              The following security tools were executed during this scan:
            </p>
            <div className="scan-report__tools-grid">
              {executedTools.map((tool) => (
                <ToolStatusRow key={tool.name} tool={tool} />
              ))}
            </div>
            <p className="scan-report__tools-legend">
              Green = Complete · Yellow = Running · Red = Failed · Gray = Skipped
            </p>
          </div>
        </div>
      )}

      <div className="panel">
        <div className="panel__header">
          <h3 className="panel__title">All Findings</h3>
        </div>
        <div className="panel__toolbar scan-report__filters">
          <label>
            Severity
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              aria-label="Filter by severity"
            >
              <option value="">All</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
              <option value="INFO">Info</option>
            </select>
          </label>
          <label>
            Tool
            <select
              value={toolFilter}
              onChange={(e) => setToolFilter(e.target.value)}
              aria-label="Filter by tool"
            >
              <option value="">All</option>
              {toolOptions.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </label>
          <label>
            Path
            <input
              type="search"
              value={pathSearch}
              onChange={(e) => setPathSearch(e.target.value)}
              placeholder="prefix…"
              aria-label="Filter by path prefix"
            />
          </label>
          <span className="scan-report__count">
            {findings.length} shown{totalFiltered > findings.length ? ` · ${totalFiltered} total` : ''}
          </span>
        </div>

        <div className="panel__body panel__body--flush">
          {findings.length === 0 ? (
            <div className="scan-report__empty">
              {summary && summary.total_vulnerabilities === 0 && !severityFilter && !toolFilter && !pathSearch.trim()
                ? 'No findings in this scan.'
                : 'No findings match the current filters.'}
            </div>
          ) : (
            <div className="data-table-wrap data-table-wrap--wide">
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Severity</th>
                    <th scope="col">Tool</th>
                    <th scope="col">Rule</th>
                    <th scope="col">Path</th>
                    <th scope="col">Line</th>
                    <th scope="col">Message</th>
                  </tr>
                </thead>
                <tbody>
                  {findings.map((f, idx) => (
                    <tr key={`${f.tool}-${f.rule_id}-${f.path}-${f.line}-${idx}`}>
                      <td><SeverityPill severity={f.severity || 'INFO'} /></td>
                      <td>{f.tool}</td>
                      <td><code>{f.rule_id || '—'}</code></td>
                      <td className="scan-report__path">{f.path || '—'}</td>
                      <td>{f.line || '—'}</td>
                      <td className="scan-report__message">{f.message || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {nextPath && (
            <div className="scan-report__load-more">
              <button
                type="button"
                className="btn-secondary"
                disabled={loadingMore}
                onClick={() => void loadFindings(true, nextPath)}
              >
                {loadingMore ? 'Loading…' : 'Load more findings'}
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="panel scan-report__policy-panel">
        <div className="panel__header">
          <h3 className="panel__title">Finding Policy</h3>
          {policyPath && <span className="scan-report__policy-badge">Active</span>}
        </div>
        <div className="panel__body">
          {policyPath ? (
            <>
              <p className="scan-report__policy-active">
                A custom finding policy is active for this scan.
              </p>
              <p className="scan-report__policy-path">
                Policy file:{' '}
                <code>
                  {policyPath.startsWith('/target/')
                    ? policyPath
                    : `/target/${policyPath.replace(/^\//, '')}`}
                </code>
              </p>
              <p className="scan-report__policy-note">
                No findings were accepted by the policy in this scan.
              </p>
            </>
          ) : (
            <p className="scan-report__policy-note">
              This scan did not use a custom finding policy path in metadata.
            </p>
          )}
        </div>
      </div>

      <AIPromptModal
        isOpen={isAiModalOpen}
        onClose={() => setIsAiModalOpen(false)}
        scanId={scanId}
      />
    </div>
  )
}
