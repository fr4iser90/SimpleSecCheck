import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useConfig } from '../hooks/useConfig'
import { formatEstimatedTime, formatDuration } from '../utils/timeUtils'

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
      const response = await fetch('/api/queue/my-scans')
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
              style={{
                background: 'var(--primary)',
                border: 'none',
                borderRadius: '8px',
                color: 'white',
                padding: '0.5rem 1rem',
                cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: '0.9rem',
                opacity: loading ? 0.6 : 1,
              }}
            >
              {loading ? 'Loading...' : '🔄 Refresh'}
            </button>
          </div>
        </div>

        {scansData && scansData.scans.length > 0 && (
          <div style={{ marginBottom: '1rem', padding: '1rem', background: 'rgba(0, 123, 255, 0.1)', borderRadius: '8px' }}>
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
              color: '#155724',
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
          <div style={{ padding: '2rem', textAlign: 'center', color: '#6c757d' }}>
            Loading your scans...
          </div>
        ) : scansData && scansData.scans.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#6c757d' }}>
            <p>You haven't started any scans yet.</p>
            <p style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>
              Go to <a href="/" style={{ color: 'var(--primary)' }}>Home</a> to start a new scan.
            </p>
          </div>
        ) : scansData ? (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e9ecef' }}>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 'bold' }}>Repository</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 'bold' }}>Branch</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 'bold' }}>Scanners</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 'bold' }}>Status</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 'bold' }}>Position</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 'bold' }}>Time</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 'bold' }}>Created</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 'bold' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {scansData.scans.map((item) => (
                  <tr key={item.queue_id} style={{ borderBottom: '1px solid #e9ecef' }}>
                    <td style={{ padding: '0.75rem' }}>
                      <div>
                        <div style={{ fontFamily: 'monospace', fontSize: '0.9rem' }}>
                          {item.repository_name}
                        </div>
                        {item.repository_url && (
                          <div style={{ fontSize: '0.75rem', color: '#6c757d', marginTop: '0.25rem' }}>
                            {item.repository_url}
                          </div>
                        )}
                      </div>
                    </td>
                    <td style={{ padding: '0.75rem', color: '#6c757d' }}>
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
                                background: 'rgba(0, 123, 255, 0.1)',
                                color: '#007bff',
                                border: '1px solid rgba(0, 123, 255, 0.3)',
                              }}
                            >
                              {scanner}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span style={{ color: '#6c757d', fontSize: '0.875rem' }}>-</span>
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
                    <td style={{ padding: '0.75rem', color: '#6c757d' }}>
                      {item.position !== undefined ? `#${item.position}` : '-'}
                    </td>
                    <td style={{ padding: '0.75rem', color: '#6c757d', fontSize: '0.875rem' }}>
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
                    <td style={{ padding: '0.75rem', color: '#6c757d', fontSize: '0.875rem' }}>
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
                              background: '#007bff',
                              color: 'white',
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
                                color: '#6f42c1',
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
