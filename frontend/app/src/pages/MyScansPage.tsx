import { useState, useEffect, useMemo, useCallback } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import PageHeader from '../components/PageHeader'
import AdminPanel from '../components/AdminPanel'
import RefreshToolbar from '../components/RefreshToolbar'
import { useConfig } from '../hooks/useConfig'
import { useSseRefresh } from '../hooks/useSseRefresh'
import { formatEstimatedTime, formatDuration, formatQueuePosition } from '../utils/timeUtils'
import { resolveApiUrl } from '../utils/resolveApiUrl'

interface MyScanItem {
  queue_id: string
  repository_url: string
  repository_name: string
  branch?: string
  commit_hash?: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  scan_id?: string
  position?: number
  created_at: string
  started_at?: string
  completed_at?: string
  scanners?: string[]
  estimated_time_seconds?: number | null
  duration_seconds?: number | null
}

interface MyScansData {
  scans: MyScanItem[]
}

type MyScansSortKey = 'repository' | 'branch' | 'scanners' | 'status' | 'position' | 'time' | 'created'

function timeColumnSeconds(item: MyScanItem): number {
  if (item.status === 'pending' || item.status === 'running') {
    return item.estimated_time_seconds ?? 0
  }
  return item.duration_seconds ?? 0
}

function compareMyScans(a: MyScanItem, b: MyScanItem, key: MyScansSortKey, dir: 'asc' | 'desc'): number {
  if (key === 'position') {
    const ap = a.position
    const bp = b.position
    const aHas = typeof ap === 'number' && !Number.isNaN(ap)
    const bHas = typeof bp === 'number' && !Number.isNaN(bp)
    if (aHas && bHas) {
      const diff = (ap as number) - (bp as number)
      return dir === 'asc' ? diff : -diff
    }
    if (aHas && !bHas) return -1
    if (!aHas && bHas) return 1
    return 0
  }

  let cmp = 0
  switch (key) {
    case 'repository':
      cmp = a.repository_name.localeCompare(b.repository_name, undefined, { sensitivity: 'base' })
      break
    case 'branch':
      cmp = (a.branch || '').localeCompare(b.branch || '', undefined, { sensitivity: 'base' })
      break
    case 'scanners': {
      const na = (a.scanners || []).length
      const nb = (b.scanners || []).length
      cmp = na - nb
      if (cmp === 0) {
        cmp = (a.scanners || []).join('\0').localeCompare((b.scanners || []).join('\0'))
      }
      break
    }
    case 'status':
      cmp = a.status.localeCompare(b.status)
      break
    case 'time':
      cmp = timeColumnSeconds(a) - timeColumnSeconds(b)
      break
    case 'created':
      cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      break
    default:
      cmp = 0
  }
  return dir === 'asc' ? cmp : -cmp
}

function statusPillClass(status: MyScanItem['status']): string {
  switch (status) {
    case 'pending':
      return 'status-pill--pending'
    case 'running':
      return 'status-pill--running'
    case 'completed':
      return 'status-pill--active'
    case 'failed':
      return 'status-pill--failed'
    default:
      return ''
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case 'pending':
      return 'Pending'
    case 'running':
      return 'Running'
    case 'completed':
      return 'Completed'
    case 'failed':
      return 'Failed'
    default:
      return status
  }
}

export default function MyScansPage() {
  useConfig()
  const navigate = useNavigate()
  const location = useLocation()
  const [scansData, setScansData] = useState<MyScansData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [flashMessage, setFlashMessage] = useState<string | null>(null)
  const [cancellingId, setCancellingId] = useState<string | null>(null)
  const [shareCopyingId, setShareCopyingId] = useState<string | null>(null)
  const [sortKey, setSortKey] = useState<MyScansSortKey>('position')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')

  const loadScans = useCallback(async ({ silent }: { silent: boolean }) => {
    try {
      const response = await fetch(resolveApiUrl('/api/queue/my-scans'))
      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Session required. Please refresh the page.')
        }
        throw new Error('Failed to fetch your scans')
      }
      const data = await response.json()
      setScansData(data)
      setError(null)
    } catch (err) {
      if (!silent) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      }
    }
  }, [])

  const [autoRefresh] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [initialLoad, setInitialLoad] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const refresh = useCallback(async (silent = false) => {
    if (!silent) setIsRefreshing(true)
    try {
      await loadScans({ silent })
      setLastUpdated(new Date())
    } finally {
      setIsRefreshing(false)
      setInitialLoad(false)
    }
  }, [loadScans])

  useSseRefresh(['scan_update', 'queue_update'], () => {
    void refresh(true)
  })

  useEffect(() => {
    void refresh(false)
  }, [refresh])

  const sortedScans = useMemo(() => {
    if (!scansData?.scans.length) return []
    const rows = [...scansData.scans]
    rows.sort((a, b) => compareMyScans(a, b, sortKey, sortDir))
    return rows
  }, [scansData, sortKey, sortDir])

  const toggleSort = (key: MyScansSortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir(key === 'created' ? 'desc' : 'asc')
    }
  }

  const sortIcon = (key: MyScansSortKey) => {
    if (sortKey !== key) return '↕'
    return sortDir === 'asc' ? '▲' : '▼'
  }

  const SortTh = (props: { col: MyScansSortKey; label: string; title: string }) => (
    <th
      scope="col"
      className="data-table__sortable"
      tabIndex={0}
      onClick={() => toggleSort(props.col)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          toggleSort(props.col)
        }
      }}
      title={props.title}
      aria-sort={sortKey === props.col ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}
    >
      {props.label}
      <span className="data-table__sort-icon" aria-hidden>
        {sortIcon(props.col)}
      </span>
    </th>
  )

  const handleCopyShareLink = async (scanId: string) => {
    setShareCopyingId(scanId)
    setError(null)
    try {
      const { apiFetch } = await import('../utils/apiClient')
      const res = await apiFetch(`/api/v1/scans/${scanId}/report-share-link`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ regenerate: false }),
      })
      if (!res.ok) {
        let msg = `Share link failed (${res.status})`
        try {
          const j = await res.json()
          msg = typeof j.detail === 'string' ? j.detail : msg
        } catch {
          /* ignore */
        }
        throw new Error(msg)
      }
      const data = (await res.json()) as { share_path: string }
      const url = `${window.location.origin}${data.share_path}`
      await navigator.clipboard.writeText(url)
      setFlashMessage('Share link copied (anyone with the link can view the report).')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not copy share link')
    } finally {
      setShareCopyingId(null)
    }
  }

  const handleCancelScanRow = async (scanId: string) => {
    if (!window.confirm('Cancel this scan? It will leave the queue or stop if running.')) return
    setCancellingId(scanId)
    setError(null)
    try {
      const { apiFetch } = await import('../utils/apiClient')
      const res = await apiFetch(`/api/v1/scans/${scanId}/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scan_id: scanId, force: false }),
      })
      if (!res.ok) {
        let msg = `Cancel failed (${res.status})`
        try {
          const j = await res.json()
          msg = typeof j.detail === 'string' ? j.detail : msg
        } catch {
          /* ignore */
        }
        throw new Error(msg)
      }
      setFlashMessage('Scan cancelled.')
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Cancel failed')
    } finally {
      setCancellingId(null)
    }
  }

  useEffect(() => {
    const flash = (location.state as { flash?: string } | null)?.flash
    if (flash) {
      setFlashMessage(flash)
      navigate(location.pathname, { replace: true, state: {} })
    }
  }, [location.state, location.pathname, navigate])

  const renderScanActions = (item: MyScanItem) => {
    const rowId = String(item.scan_id || item.queue_id)
    return (
      <div className="admin-page-actions">
        {(item.scan_id || item.queue_id) && (
          <button
            type="button"
            className="btn-primary"
            onClick={() => {
              const sid = item.scan_id || item.queue_id
              const scanState = {
                status: item.status,
                scan_id: sid,
                results_dir: item.status === 'completed' && item.scan_id ? item.scan_id : null,
                started_at: item.started_at || null,
              }
              navigate(
                sid ? `/scan?scan_id=${encodeURIComponent(sid)}` : '/scan',
                { state: scanState },
              )
            }}
            title="View steps and progress"
          >
            View steps
          </button>
        )}
        {(item.status === 'pending' || item.status === 'running') && (
          <button
            type="button"
            className="btn-danger"
            onClick={() => handleCancelScanRow(rowId)}
            disabled={cancellingId === rowId}
          >
            {cancellingId === rowId ? 'Cancelling…' : 'Cancel'}
          </button>
        )}
        {item.status === 'completed' && item.scan_id && (
          <>
            <a
              href={`/api/results/${item.scan_id}/report`}
              className="btn-secondary"
              target="_blank"
              rel="noopener noreferrer"
            >
              Results
            </a>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => handleCopyShareLink(item.scan_id!)}
              disabled={shareCopyingId === item.scan_id}
            >
              {shareCopyingId === item.scan_id ? 'Copying…' : 'Share link'}
            </button>
          </>
        )}
      </div>
    )
  }

  return (
    <div className="container">
      <PageHeader title="My Scans" subtitle="Your scan requests in the queue">
        <RefreshToolbar
          autoRefresh={autoRefresh}
          onAutoRefreshChange={() => {}}
          onRefresh={() => void refresh(false)}
          isRefreshing={isRefreshing}
          lastUpdated={lastUpdated}
        />
      </PageHeader>

      {scansData && scansData.scans.length > 0 && (
        <div className="queue-metrics">
          <span>
            <strong>{scansData.scans.length}</strong> total
          </span>
          <span>
            <strong>{scansData.scans.filter((item) => item.status === 'pending').length}</strong> pending
          </span>
          <span>
            <strong>{scansData.scans.filter((item) => item.status === 'running').length}</strong> running
          </span>
          <span>
            <strong>{scansData.scans.filter((item) => item.status === 'completed').length}</strong> completed
          </span>
        </div>
      )}

      {flashMessage && (
        <div className="success-message" role="status" style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
          <span>{flashMessage}</span>
          <button
            type="button"
            onClick={() => setFlashMessage(null)}
            className="btn-secondary"
            style={{ padding: '0.25rem 0.5rem', minHeight: 0 }}
            aria-label="Dismiss"
          >
            ×
          </button>
        </div>
      )}

      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}

      {initialLoad && !scansData ? (
        <AdminPanel>
          <div className="loading">Loading your scans…</div>
        </AdminPanel>
      ) : scansData && scansData.scans.length === 0 ? (
        <AdminPanel>
          <p style={{ textAlign: 'center', color: 'var(--ds-text-secondary)', margin: 0 }}>
            You haven&apos;t started any scans yet.
          </p>
          <p style={{ textAlign: 'center', marginTop: '0.5rem', fontSize: '0.875rem' }}>
            Go to <Link to="/">Home</Link> to start a new scan.
          </p>
        </AdminPanel>
      ) : scansData ? (
        <AdminPanel title="Scan queue" description="Sorted by queue position by default. Click column headers to re-sort." flush>
          <div className="desktop-only-table data-table-wrap data-table-wrap--my-scans">
            <table className="data-table">
              <thead>
                <tr>
                  <SortTh col="repository" label="Repository" title="Sort by repository name" />
                  <SortTh col="branch" label="Branch" title="Sort by branch" />
                  <SortTh col="scanners" label="Scanners" title="Sort by number of scanners" />
                  <SortTh col="status" label="Status" title="Sort by status" />
                  <SortTh col="position" label="Position" title="Sort by queue position" />
                  <SortTh col="time" label="Time" title="Sort by estimated time or duration" />
                  <SortTh col="created" label="Created" title="Sort by created time" />
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortedScans.map((item) => {
                  return (
                    <tr key={item.queue_id}>
                      <td>
                        <div style={{ fontFamily: 'ui-monospace, monospace', fontSize: '0.8125rem', fontWeight: 600 }}>
                          {item.repository_name}
                        </div>
                        {item.repository_url && (
                          <div style={{ fontSize: '0.75rem', color: 'var(--ds-text-secondary)', marginTop: '0.2rem' }}>
                            {item.repository_url}
                          </div>
                        )}
                      </td>
                      <td style={{ color: 'var(--ds-text-secondary)' }}>{item.branch || '—'}</td>
                      <td>
                        {item.scanners && item.scanners.length > 0 ? (
                          <div className="queue-card__chips">
                            {item.scanners.map((scanner) => (
                              <span key={scanner} className="ui-chip ui-chip--accent">
                                {scanner}
                              </span>
                            ))}
                          </div>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td>
                        <span className={`status-pill ${statusPillClass(item.status)}`}>
                          {statusLabel(item.status)}
                        </span>
                      </td>
                      <td style={{ color: 'var(--ds-text-secondary)' }}>
                        {item.position !== undefined ? `#${item.position}` : '—'}
                      </td>
                      <td style={{ color: 'var(--ds-text-secondary)', fontSize: '0.8125rem' }}>
                        {item.status === 'pending' || item.status === 'running' ? (
                          item.estimated_time_seconds ? (
                            <span title={`Estimated: ${formatEstimatedTime(item.estimated_time_seconds)}`}>
                              {formatEstimatedTime(item.estimated_time_seconds)}
                            </span>
                          ) : (
                            '—'
                          )
                        ) : item.duration_seconds ? (
                          <span title={`Duration: ${formatDuration(item.duration_seconds)}`}>
                            {formatDuration(item.duration_seconds)}
                          </span>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td style={{ color: 'var(--ds-text-secondary)', fontSize: '0.8125rem', whiteSpace: 'nowrap' }}>
                        {new Date(item.created_at).toLocaleString()}
                      </td>
                      <td>{renderScanActions(item)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <div className="mobile-card-list" aria-label="Scan queue (mobile)">
            {sortedScans.map((item) => {
              const timeLabel =
                item.status === 'pending' || item.status === 'running'
                  ? item.estimated_time_seconds
                    ? formatEstimatedTime(item.estimated_time_seconds)
                    : '—'
                  : item.duration_seconds
                    ? formatDuration(item.duration_seconds)
                    : '—'
              return (
                <article key={item.queue_id} className="mobile-data-card">
                  <h3 className="mobile-data-card__title">{item.repository_name}</h3>
                  {item.repository_url ? (
                    <p className="mobile-data-card__subtitle">{item.repository_url}</p>
                  ) : null}
                  <div className="mobile-data-card__grid">
                    <div className="mobile-data-card__row">
                      <span className="mobile-data-card__label">Status</span>
                      <span className={`status-pill ${statusPillClass(item.status)}`}>
                        {statusLabel(item.status)}
                      </span>
                    </div>
                    <div className="mobile-data-card__row">
                      <span className="mobile-data-card__label">Branch</span>
                      <span className="mobile-data-card__value">{item.branch || '—'}</span>
                    </div>
                    <div className="mobile-data-card__row">
                      <span className="mobile-data-card__label">Position</span>
                      <span className="mobile-data-card__value">
                        {formatQueuePosition(item.position, item.status)}
                      </span>
                    </div>
                    <div className="mobile-data-card__row">
                      <span className="mobile-data-card__label">Time</span>
                      <span className="mobile-data-card__value">{timeLabel}</span>
                    </div>
                    <div className="mobile-data-card__row">
                      <span className="mobile-data-card__label">Created</span>
                      <span className="mobile-data-card__value">
                        {new Date(item.created_at).toLocaleString()}
                      </span>
                    </div>
                  </div>
                  {item.scanners && item.scanners.length > 0 ? (
                    <div className="queue-card__chips" style={{ marginBottom: '0.75rem' }}>
                      {item.scanners.map((scanner) => (
                        <span key={scanner} className="ui-chip ui-chip--accent">
                          {scanner}
                        </span>
                      ))}
                    </div>
                  ) : null}
                  <div className="mobile-data-card__actions">{renderScanActions(item)}</div>
                </article>
              )
            })}
          </div>
        </AdminPanel>
      ) : null}
    </div>
  )
}
