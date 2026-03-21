import { useState, useEffect, useMemo, type CSSProperties } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useConfig } from '../hooks/useConfig'
import { formatEstimatedTime, formatDuration } from '../utils/timeUtils'
import { resolveApiUrl } from '../utils/resolveApiUrl'

interface MyScanItem {
  queue_id: string
  repository_url: string
  repository_name: string
  branch?: string
  commit_hash?: string
  status: 'pending' | 'running' | 'completed' | 'failed'  // Backend standard
  scan_id?: string
  position?: number
  created_at: string
  started_at?: string
  completed_at?: string
  scanners?: string[]  // List of scanner names
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

export default function MyScansPage() {
  useConfig()
  const navigate = useNavigate()
  const location = useLocation()
  const [scansData, setScansData] = useState<MyScansData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [flashMessage, setFlashMessage] = useState<string | null>(null)
  const [cancellingId, setCancellingId] = useState<string | null>(null)
  const [shareCopyingId, setShareCopyingId] = useState<string | null>(null)
  /** Next in queue first: lowest position at top; rows without position stay at the end. */
  const [sortKey, setSortKey] = useState<MyScansSortKey>('position')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')

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

  const sortIndicator = (key: MyScansSortKey) =>
    sortKey === key ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ''

  const sortableThStyle: CSSProperties = {
    padding: '0.75rem',
    textAlign: 'left',
    fontWeight: 'bold',
    cursor: 'pointer',
    userSelect: 'none',
    whiteSpace: 'nowrap',
  }

  const SortTh = (props: { col: MyScansSortKey; label: string; title: string }) => (
    <th
      scope="col"
      style={sortableThStyle}
      tabIndex={0}
      onClick={() => toggleSort(props.col)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          toggleSort(props.col)
        }
      }}
      title={props.title}
      aria-sort={
        sortKey === props.col ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'
      }
    >
      {props.label}
      {sortIndicator(props.col)}
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
      await fetchMyScans()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Cancel failed')
    } finally {
      setCancellingId(null)
    }
  }

  const fetchMyScans = async () => {
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
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMyScans()
  }, [])

  useEffect(() => {
    const flash = (location.state as { flash?: string } | null)?.flash
    if (flash) {
      setFlashMessage(flash)
      navigate(location.pathname, { replace: true, state: {} })
    }
  }, [location.state, location.pathname, navigate])

  // Auto-refresh every 3 seconds if enabled
  useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(() => {
      fetchMyScans()
    }, 3000)

    return () => clearInterval(interval)
  }, [autoRefresh])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return '#ffc107' // Yellow
      case 'running':
        return '#007bff' // Blue
      case 'completed':
        return '#28a745' // Green
      case 'failed':
        return '#dc3545' // Red
      default:
        return '#6c757d' // Gray
    }
  }

  const primaryButtonStyle = {
    background: 'var(--accent-gradient)',
    border: 'none',
    borderRadius: '8px',
    color: '#fff',
    padding: '0.5rem 1rem',
    cursor: loading ? 'not-allowed' : 'pointer',
    fontSize: '0.9rem',
    opacity: loading ? 0.6 : 1,
  }

  const getStatusLabel = (status: string) => {
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



  return (
    <div className="container">
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
          <div>
            <h2>My Scans</h2>
            <p style={{ marginTop: '0.5rem', opacity: 0.8, fontSize: '0.9rem' }}>
              Your scan requests in the queue
            </p>
          </div>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
              <span style={{ fontSize: '0.9rem' }}>Auto-refresh</span>
            </label>
            <button
              onClick={fetchMyScans}
              disabled={loading}
              style={primaryButtonStyle}
            >
              {loading ? 'Loading...' : '🔄 Refresh'}
            </button>
          </div>
        </div>

        {scansData && scansData.scans.length > 0 && (
          <div className="surface-muted-box" style={{ marginBottom: '1rem', padding: '1rem' }}>
            <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
              <div>
                <strong>Total Scans:</strong> {scansData.scans.length}
              </div>
              <div>
                <strong>Pending:</strong> {scansData.scans.filter(item => item.status === 'pending').length}
              </div>
              <div>
                <strong>Running:</strong> {scansData.scans.filter(item => item.status === 'running').length}
              </div>
              <div>
                <strong>Completed:</strong> {scansData.scans.filter(item => item.status === 'completed').length}
              </div>
            </div>
          </div>
        )}

        {flashMessage && (
          <div
            style={{
              background: 'rgba(40, 167, 69, 0.15)',
              border: '1px solid #28a745',
              borderRadius: '8px',
              padding: '0.75rem 1rem',
              marginBottom: '1rem',
              color: 'var(--color-pass)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: '1rem',
            }}
          >
            <span>{flashMessage}</span>
            <button
              type="button"
              onClick={() => setFlashMessage(null)}
              style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '1.1rem' }}
              aria-label="Dismiss"
            >
              ×
            </button>
          </div>
        )}

        {error && (
          <div style={{
            background: 'rgba(220, 53, 69, 0.2)',
            border: '1px solid #dc3545',
            borderRadius: '8px',
            padding: '1rem',
            marginBottom: '1rem',
            color: '#dc3545'
          }}>
            {error}
          </div>
        )}

        {loading && !scansData ? (
          <div className="text-secondary" style={{ padding: '2rem', textAlign: 'center' }}>
            Loading your scans...
          </div>
        ) : scansData && scansData.scans.length === 0 ? (
          <div className="text-secondary" style={{ padding: '2rem', textAlign: 'center' }}>
            <p>You haven't started any scans yet.</p>
            <p style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>
              Go to <a href="/" style={{ color: 'var(--accent)' }}>Home</a> to start a new scan.
            </p>
          </div>
        ) : scansData ? (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr className="table-head-row" style={{ borderBottom: '1px solid var(--glass-border-main)' }}>
                  <SortTh col="repository" label="Repository" title="Sort by repository name" />
                  <SortTh col="branch" label="Branch" title="Sort by branch" />
                  <SortTh col="scanners" label="Scanners" title="Sort by number of scanners, then name" />
                  <SortTh col="status" label="Status" title="Sort by status" />
                  <SortTh
                    col="position"
                    label="Position"
                    title="Sort by queue position (default: next in line first)"
                  />
                  <SortTh
                    col="time"
                    label="Time"
                    title="Sort by estimated time (queued/running) or duration (finished)"
                  />
                  <SortTh col="created" label="Created" title="Sort by created time" />
                  <th scope="col" style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 'bold' }}>
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedScans.map((item) => (
                  <tr key={item.queue_id} style={{ borderBottom: '1px solid var(--glass-border-main)' }}>
                    <td style={{ padding: '0.75rem' }}>
                      <div>
                        <div style={{ fontFamily: 'monospace', fontSize: '0.9rem' }}>
                          {item.repository_name}
                        </div>
                        {item.repository_url && (
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                            {item.repository_url}
                          </div>
                        )}
                      </div>
                    </td>
                    <td style={{ padding: '0.75rem', color: 'var(--text-secondary)' }}>
                      {item.branch || '-'}
                    </td>
                    <td style={{ padding: '0.75rem' }}>
                      {item.scanners && item.scanners.length > 0 ? (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                          {item.scanners.map((scanner) => (
                            <span
                              key={scanner}
                              style={{
                                display: 'inline-block',
                                padding: '0.125rem 0.5rem',
                                borderRadius: '8px',
                                fontSize: '0.75rem',
                                fontWeight: '500',
                                background: 'var(--surface-muted)',
                                color: 'var(--accent)',
                                border: '1px solid var(--glass-border-main)',
                              }}
                            >
                              {scanner}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>-</span>
                      )}
                    </td>
                    <td style={{ padding: '0.75rem' }}>
                      <span style={{
                        display: 'inline-block',
                        padding: '0.25rem 0.75rem',
                        borderRadius: '12px',
                        fontSize: '0.875rem',
                        fontWeight: 'bold',
                        background: getStatusColor(item.status) + '20',
                        color: getStatusColor(item.status),
                        border: `1px solid ${getStatusColor(item.status)}`
                      }}>
                        {getStatusLabel(item.status)}
                      </span>
                    </td>
                    <td style={{ padding: '0.75rem', color: 'var(--text-secondary)' }}>
                      {item.position !== undefined ? `#${item.position}` : '-'}
                    </td>
                    <td style={{ padding: '0.75rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                      {item.status === 'pending' || item.status === 'running' ? (
                        item.estimated_time_seconds ? (
                          <span title={`Estimated time: ${formatEstimatedTime(item.estimated_time_seconds)}`}>
                            {formatEstimatedTime(item.estimated_time_seconds)}
                          </span>
                        ) : (
                          <span style={{ opacity: 0.6 }}>-</span>
                        )
                      ) : item.duration_seconds ? (
                        <span title={`Actual duration: ${formatDuration(item.duration_seconds)}`}>
                          {formatDuration(item.duration_seconds)}
                        </span>
                      ) : (
                        <span style={{ opacity: 0.6 }}>-</span>
                      )}
                    </td>
                    <td style={{ padding: '0.75rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                      {new Date(item.created_at).toLocaleString()}
                    </td>
                    <td style={{ padding: '0.75rem' }}>
                      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                        {(item.scan_id || item.queue_id) && (
                          <button
                            onClick={() => {
                              navigate('/scan', {
                                state: {
                                  status: item.status,
                                  scan_id: item.scan_id || item.queue_id,
                                  results_dir:
                                    item.status === 'completed' && item.scan_id
                                      ? item.scan_id
                                      : null,
                                  started_at: item.started_at || null,
                                },
                              })
                            }}
                            style={{
                              padding: '0.375rem 0.75rem',
                              background: 'var(--accent-gradient)',
                              color: '#fff',
                              border: 'none',
                              borderRadius: '4px',
                              cursor: 'pointer',
                              fontSize: '0.875rem',
                              fontWeight: '500',
                            }}
                            title="View Steps & Progress"
                          >
                            View Steps
                          </button>
                        )}
                        {(item.status === 'pending' || item.status === 'running') &&
                          (item.scan_id || item.queue_id) && (
                            <button
                              type="button"
                              onClick={() =>
                                handleCancelScanRow(String(item.scan_id || item.queue_id))
                              }
                              disabled={cancellingId === String(item.scan_id || item.queue_id)}
                              style={{
                                padding: '0.375rem 0.75rem',
                                background: 'transparent',
                                color: '#dc3545',
                                border: '1px solid rgba(220, 53, 69, 0.5)',
                                borderRadius: '4px',
                                cursor:
                                  cancellingId === String(item.scan_id || item.queue_id)
                                    ? 'wait'
                                    : 'pointer',
                                fontSize: '0.875rem',
                                fontWeight: '500',
                                opacity:
                                  cancellingId === String(item.scan_id || item.queue_id) ? 0.6 : 1,
                              }}
                              title="Cancel this scan"
                            >
                              {cancellingId === String(item.scan_id || item.queue_id)
                                ? 'Cancelling…'
                                : 'Cancel'}
                            </button>
                          )}
                        {item.status === 'completed' && item.scan_id && (
                          <>
                            <a
                              href={`/api/results/${item.scan_id}/report`}
                              className="action-button action-completed"
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{
                                padding: '0.375rem 0.75rem',
                                background: '#28a745',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: 'pointer',
                                fontSize: '0.875rem',
                                fontWeight: '500',
                                textDecoration: 'none',
                                display: 'inline-block',
                              }}
                            >
                              View Results
                            </a>
                            <button
                              type="button"
                              onClick={() => handleCopyShareLink(item.scan_id!)}
                              disabled={shareCopyingId === item.scan_id}
                              style={{
                                padding: '0.375rem 0.75rem',
                                background: 'transparent',
                                color: 'var(--accent)',
                                border: '1px solid rgba(111, 66, 193, 0.45)',
                                borderRadius: '4px',
                                cursor:
                                  shareCopyingId === item.scan_id ? 'wait' : 'pointer',
                                fontSize: '0.875rem',
                                fontWeight: '500',
                                opacity: shareCopyingId === item.scan_id ? 0.7 : 1,
                              }}
                              title="Copy a shareable link (token in URL)"
                            >
                              {shareCopyingId === item.scan_id
                                ? 'Copying…'
                                : 'Copy share link'}
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
    </div>
  )
}
