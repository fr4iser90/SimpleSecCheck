import { useState, useEffect } from 'react'
import { useConfig } from '../hooks/useConfig'

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
}

interface MyScansData {
  scans: MyScanItem[]
}

export default function MyScansPage() {
  const { config } = useConfig()
  const [scansData, setScansData] = useState<MyScansData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(true)

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

  // Auto-refresh every 3 seconds if enabled
  useEffect(() => {
    if (!autoRefresh || !config?.features.queue_enabled) return

    const interval = setInterval(() => {
      fetchMyScans()
    }, 3000)

    return () => clearInterval(interval)
  }, [autoRefresh, config?.features.queue_enabled])

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

  const formatDuration = (started: string | undefined, completed: string | undefined) => {
    if (!started) return '-'
    const start = new Date(started)
    const end = completed ? new Date(completed) : new Date()
    const seconds = Math.floor((end.getTime() - start.getTime()) / 1000)
    
    if (seconds < 60) return `${seconds}s`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}m ${remainingSeconds}s`
  }

  if (!config?.features.queue_enabled) {
    return (
      <div className="container">
        <div className="card">
          <h2>My Scans</h2>
          <p style={{ color: '#6c757d' }}>
            Queue system is only available in Production Mode.
          </p>
        </div>
      </div>
    )
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
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 'bold' }}>Commit</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 'bold' }}>Status</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 'bold' }}>Position</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 'bold' }}>Duration</th>
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
                    <td style={{ padding: '0.75rem', fontFamily: 'monospace', fontSize: '0.85rem', color: '#6c757d' }}>
                      {item.commit_hash ? item.commit_hash.substring(0, 7) : '-'}
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
                      {formatDuration(item.started_at, item.completed_at)}
                    </td>
                    <td style={{ padding: '0.75rem', color: '#6c757d', fontSize: '0.875rem' }}>
                      {new Date(item.created_at).toLocaleString()}
                    </td>
                    <td style={{ padding: '0.75rem' }}>
                      {item.status === 'completed' && item.scan_id && (
                        <a
                          href={`/api/my-results/${item.scan_id}/report`}
                          className="action-button action-completed"
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          View Results
                        </a>
                      )}
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
