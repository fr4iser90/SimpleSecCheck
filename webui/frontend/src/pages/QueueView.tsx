import { useState, useEffect } from 'react'
import { useConfig } from '../hooks/useConfig'

interface QueueItem {
  queue_id: string
  repository_name: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  position?: number
  created_at: string
  branch?: string
}

interface QueueData {
  queue: QueueItem[]
  queue_length: number
  max_queue_length: number
}

export default function QueueView() {
  const { config } = useConfig()
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
    if (!autoRefresh || !config?.features.queue_enabled) return

    const interval = setInterval(() => {
      fetchQueue()
    }, 5000)

    return () => clearInterval(interval)
  }, [autoRefresh, config?.features.queue_enabled])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return '#ffc107' // Yellow
      case 'processing':
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
      case 'processing':
        return 'Processing'
      case 'completed':
        return 'Completed'
      case 'failed':
        return 'Failed'
      default:
        return status
    }
  }

  if (!config?.features.queue_enabled) {
    return (
      <div className="container">
        <div className="card">
          <h2>Queue</h2>
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
            <h2>Public Queue</h2>
            <p style={{ marginTop: '0.5rem', opacity: 0.8, fontSize: '0.9rem' }}>
              Anonymized view of all scans in the queue
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
                <strong>Pending:</strong> {queueData.queue.filter(item => item.status === 'pending').length}
              </div>
              <div>
                <strong>Processing:</strong> {queueData.queue.filter(item => item.status === 'processing').length}
              </div>
              <div>
                <strong>Completed:</strong> {queueData.queue.filter(item => item.status === 'completed').length}
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
        ) : queueData && queueData.queue.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#6c757d' }}>
            Queue is empty
          </div>
        ) : queueData ? (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e9ecef' }}>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 'bold' }}>Position</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 'bold' }}>Repository</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 'bold' }}>Branch</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 'bold' }}>Status</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 'bold' }}>Created</th>
                </tr>
              </thead>
              <tbody>
                {queueData.queue.map((item, index) => (
                  <tr key={item.queue_id} style={{ borderBottom: '1px solid #e9ecef' }}>
                    <td style={{ padding: '0.75rem' }}>
                      {item.position !== undefined ? item.position : index + 1}
                    </td>
                    <td style={{ padding: '0.75rem', fontFamily: 'monospace', fontSize: '0.9rem' }}>
                      {item.repository_name}
                    </td>
                    <td style={{ padding: '0.75rem', color: '#6c757d' }}>
                      {item.branch || '-'}
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
                    <td style={{ padding: '0.75rem', color: '#6c757d', fontSize: '0.875rem' }}>
                      {new Date(item.created_at).toLocaleString()}
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
