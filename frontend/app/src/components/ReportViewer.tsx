import { useCallback, useEffect, useMemo, useState } from 'react'
import { resolveApiUrl } from '../utils/resolveApiUrl'
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

export default function ReportViewer({ scanId }: ReportViewerProps) {
  const [summary, setSummary] = useState<FindingSummary | null>(null)
  const [findings, setFindings] = useState<FindingItem[]>([])
  const [generatedAt, setGeneratedAt] = useState<string | null>(null)
  const [source, setSource] = useState<string>('file')
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [nextPath, setNextPath] = useState<string | null>(null)
  const [totalFiltered, setTotalFiltered] = useState(0)

  const [severityFilter, setSeverityFilter] = useState('')
  const [toolFilter, setToolFilter] = useState('')
  const [pathSearch, setPathSearch] = useState('')

  const toolOptions = useMemo(() => {
    const tools = new Set(findings.map((f) => f.tool).filter(Boolean))
    return Array.from(tools).sort((a, b) => a.localeCompare(b))
  }, [findings])

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
  }, [scanId, severityFilter, toolFilter, pathSearch]) // eslint-disable-line react-hooks/exhaustive-deps

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

  const severityCards = summary
    ? [
        { label: 'Critical', value: summary.critical_vulnerabilities, key: 'critical' },
        { label: 'High', value: summary.high_vulnerabilities, key: 'high' },
        { label: 'Medium', value: summary.medium_vulnerabilities, key: 'medium' },
        { label: 'Low', value: summary.low_vulnerabilities, key: 'low' },
        { label: 'Info', value: summary.info_vulnerabilities, key: 'info' },
        { label: 'Total', value: summary.total_vulnerabilities, key: 'total' },
      ]
    : []

  if (!scanId) {
    return (
      <div className="scan-report__empty panel">
        <div className="panel__body">No scan selected.</div>
      </div>
    )
  }

  if (loading && findings.length === 0) {
    return (
      <div className="scan-report">
        <div className="panel">
          <div className="panel__body scan-report__empty">Loading report…</div>
        </div>
      </div>
    )
  }

  if (error && findings.length === 0) {
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
      <div className="scan-report__header">
        <div className="scan-report__title-block">
          <h2>Security report</h2>
          <p className="scan-report__meta">
            Scan {scanId}
            {generatedAt ? ` · ${new Date(generatedAt).toLocaleString()}` : ''}
            {source ? ` · ${source}` : ''}
          </p>
        </div>
        <div className="scan-report__actions">
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

      {summary && (
        <div className="scan-report__severity-grid">
          {severityCards.map((card) => (
            <div
              key={card.key}
              className="scan-report__severity-card"
              style={
                card.key !== 'total'
                  ? { ['--scan-report-severity-color' as string]: severityColor(card.key.toUpperCase()) }
                  : undefined
              }
            >
              <strong>{card.value}</strong>
              <span>{card.label}</span>
            </div>
          ))}
        </div>
      )}

      <div className="panel">
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
              {summary && summary.total_vulnerabilities === 0
                ? 'All clear — no findings after policy.'
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
    </div>
  )
}
