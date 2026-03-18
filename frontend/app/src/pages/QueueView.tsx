import { useState, useEffect } from 'react'
import { useConfig } from '../hooks/useConfig'

interface QueueItem {
  queue_id: string
  repository_name: string
  status: 'pending' | 'running' | 'completed' | 'failed'  // Backend standard
  position?: number
  created_at: string
  branch?: string
  scanners?: string[]  // List of scanner names
}

interface QueueData {
  items: QueueItem[]  // REST standard: collections use "items"
  queue_length: number
  max_queue_length: number
}

export default function QueueView() {
  useConfig()
  const [queueData, setQueueData] = useState<QueueData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(true)

  const fetchQueue = async () => {
    try {
      const response = await fetch('/api/queue?limit=100')
      if (!response.ok) {
        throw new Error('Failed to fetch queue')
      }
      const data = await response.json()
      setQueueData(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchQueue()
  }, [])

  // Auto-refresh every 5 seconds if enabled
  useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(() => {
      fetchQueue()
    }, 5000)

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
            <h2>Public Queue</h2>
            <p style={{ marginTop: '0.5rem', opacity: 0.8, fontSize: '0.9rem' }}>
              Anonymized view of all scans in the queue. To cancel your own scan, open{' '}
              <a href="/my-scans" style={{ color: 'var(--primary, #007bff)' }}>My Scans</a> or the scan progress page.
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
              onClick={fetchQueue}
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

        {queueData && (
          <div style={{ marginBottom: '1rem', padding: '1rem', background: 'rgba(0, 123, 255, 0.1)', borderRadius: '8px' }}>
            <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
              <div>
                <strong>Queue Length:</strong> {queueData.queue_length} / {queueData.max_queue_length}
              </div>
              <div>
                <strong>Pending:</strong> {queueData.items.filter(item => item.status === 'pending').length}
              </div>
              <div>
                <strong>Running:</strong> {queueData.items.filter(item => item.status === 'running').length}
              </div>
              <div>
                <strong>Completed:</strong> {queueData.items.filter(item => item.status === 'completed').length}
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

        {loading && !queueData ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#6c757d' }}>
            Loading queue...
          </div>
        ) : queueData && queueData.queue_length === 0 && queueData.items.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#6c757d' }}>
            Queue is empty
          </div>
        ) : queueData && queueData.items.length > 0 ? (
          <div style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))' }}>
            {queueData.items.map((item) => (
              <div
                key={item.queue_id}
                style={{
                  background: 'var(--glass-bg-dark)',
                  padding: '1.5rem',
                  borderRadius: '8px',
                  border: `1px solid ${getStatusColor(item.status)}40`,
                  boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)'
                }}
              >
                {/* Header with Position and Status */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                  <div>
                    {item.position !== undefined && (
                      <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: getStatusColor(item.status) }}>
                        #{item.position}
                      </div>
                    )}
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                      {new Date(item.created_at).toLocaleString()}
                    </div>
                  </div>
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
                </div>

                {/* Repository Name */}
                <div style={{ marginBottom: '1rem' }}>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
                    Repository
                  </div>
                  <div style={{ fontFamily: 'monospace', fontSize: '1rem', fontWeight: 'bold', wordBreak: 'break-all' }}>
                    {item.repository_name}
                  </div>
                </div>

                {/* Branch (if available) */}
                {item.branch && (
                  <div style={{ marginBottom: '1rem' }}>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
                      Branch
                    </div>
                    <div style={{ fontSize: '0.9rem' }}>
                      🌿 {item.branch}
                    </div>
                  </div>
                )}

                {/* Scanners */}
                {item.scanners && item.scanners.length > 0 && (
                  <div>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                      Scanners ({item.scanners.length})
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                      {item.scanners.map((scanner) => (
                        <span
                          key={scanner}
                          style={{
                            display: 'inline-block',
                            padding: '0.25rem 0.75rem',
                            borderRadius: '8px',
                            fontSize: '0.75rem',
                            fontWeight: '500',
                            background: 'rgba(102, 126, 234, 0.15)',
                            color: '#667eea',
                            border: '1px solid rgba(102, 126, 234, 0.3)',
                          }}
                        >
                          {scanner}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  )
}
