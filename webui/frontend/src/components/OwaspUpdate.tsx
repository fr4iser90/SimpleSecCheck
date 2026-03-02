import { useEffect, useRef, useState } from 'react'
import { useConfig } from '../hooks/useConfig'

interface UpdateStatus {
  status: 'idle' | 'running' | 'done' | 'error'
  started_at: string | null
  finished_at: string | null
  error_code?: number | null
  error_message?: string | null
  database_age_days?: number | null
  database_exists?: boolean | null
}

export default function OwaspUpdate() {
  const { config } = useConfig()
  const [status, setStatus] = useState<UpdateStatus>({
    status: 'idle',
    started_at: null,
    finished_at: null,
    database_age_days: null,
    database_exists: null,
  })
  const [logs, setLogs] = useState<string[]>([])
  const [isUpdating, setIsUpdating] = useState(false)
  const logsEndRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)
  
  // In production, hide completely (auto-update runs in background)
  // In dev, always show (manual control)
  const shouldShow = !config?.is_production

  // Poll for status and logs
  useEffect(() => {
    let pollInterval: number | null = null
    let lastCount = 0

    const fetchStatus = async () => {
      try {
        const response = await fetch('/api/owasp/status')
        if (!response.ok) {
          console.error('[OwaspUpdate] Failed to fetch status:', response.status)
          return
        }
        const data = await response.json()
        setStatus(data)
        setIsUpdating(data.status === 'running')
      } catch (err) {
        console.error('[OwaspUpdate] Error fetching status:', err)
      }
    }

    const fetchLogs = async () => {
      try {
        const response = await fetch('/api/owasp/logs')
        if (!response.ok) {
          console.error('[OwaspUpdate] Failed to fetch logs:', response.status)
          return
        }

        const data = await response.json()
        if (data.lines && Array.isArray(data.lines)) {
          // Only update if we have new lines
          if (data.lines.length > lastCount) {
            setLogs(data.lines)
            lastCount = data.lines.length
          }
        }
      } catch (err) {
        console.error('[OwaspUpdate] Error fetching logs:', err)
      }
    }

    // Fetch immediately
    fetchStatus()
    if (isUpdating) {
      fetchLogs()
    }

    // Poll every 500ms for real-time updates
    pollInterval = window.setInterval(() => {
      fetchStatus()
      if (isUpdating) {
        fetchLogs()
      }
    }, 500)

    return () => {
      if (pollInterval) {
        clearInterval(pollInterval)
      }
    }
  }, [isUpdating])

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, autoScroll])

  const handleStartUpdate = async () => {
    try {
      const response = await fetch('/api/owasp/update', {
        method: 'POST',
      })
      if (!response.ok) {
        const error = await response.json()
        alert(`Failed to start update: ${error.detail || 'Unknown error'}`)
        return
      }
      const data = await response.json()
      setStatus(data)
      setIsUpdating(true)
    } catch (err) {
      console.error('[OwaspUpdate] Error starting update:', err)
      alert('Failed to start update. Check console for details.')
    }
  }

  const handleStopUpdate = async () => {
    try {
      const response = await fetch('/api/owasp/stop', {
        method: 'POST',
      })
      if (!response.ok) {
        const error = await response.json()
        alert(`Failed to stop update: ${error.detail || 'Unknown error'}`)
        return
      }
      const data = await response.json()
      setStatus(data)
      setIsUpdating(false)
    } catch (err) {
      console.error('[OwaspUpdate] Error stopping update:', err)
      alert('Failed to stop update. Check console for details.')
    }
  }

  const getStatusColor = () => {
    switch (status.status) {
      case 'running':
        return '#007bff'
      case 'done':
        return '#28a745'
      case 'error':
        return '#dc3545'
      default:
        return '#6c757d'
    }
  }

  const getStatusText = () => {
    switch (status.status) {
      case 'running':
        return '🔄 Updating...'
      case 'done':
        return '✅ Update completed'
      case 'error':
        return '❌ Update failed'
      default:
        return '⏸️ Idle'
    }
  }

  // Don't render in production (auto-update runs in background)
  if (!shouldShow) {
    return null
  }

  return (
    <div>
      <div style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h3 style={{ margin: 0, marginBottom: '0.5rem' }}>OWASP Dependency Check Database</h3>
          <p style={{ margin: 0, opacity: 0.8, fontSize: '0.9rem' }}>
            Update the vulnerability database to get the latest CVE information.
            This may take 5-15 minutes depending on your connection.
          </p>
        </div>
        <div>
          {status.status === 'idle' && (
            <button
              onClick={handleStartUpdate}
              style={{
                padding: '0.75rem 1.5rem',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontWeight: 'bold',
                fontSize: '1rem',
              }}
            >
              🔄 Update Database
            </button>
          )}
          {status.status === 'running' && (
            <button
              onClick={handleStopUpdate}
              style={{
                padding: '0.75rem 1.5rem',
                background: '#dc3545',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontWeight: 'bold',
                fontSize: '1rem',
              }}
            >
              ⏹️ Stop Update
            </button>
          )}
          {(status.status === 'done' || status.status === 'error') && (
            <button
              onClick={handleStartUpdate}
              style={{
                padding: '0.75rem 1.5rem',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontWeight: 'bold',
                fontSize: '1rem',
              }}
            >
              🔄 Update Again
            </button>
          )}
        </div>
      </div>

      <div style={{ marginBottom: '1rem', padding: '1rem', background: 'rgba(0, 0, 0, 0.2)', borderRadius: '4px', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <span style={{ color: getStatusColor(), fontWeight: 'bold' }}>{getStatusText()}</span>
            {status.started_at && (
              <span style={{ fontSize: '0.9rem', opacity: 0.7, color: 'var(--text-dark, #f8f9fa)' }}>
                Started: {new Date(status.started_at).toLocaleString()}
              </span>
            )}
            {status.finished_at && (
              <span style={{ fontSize: '0.9rem', opacity: 0.7, color: 'var(--text-dark, #f8f9fa)' }}>
                Finished: {new Date(status.finished_at).toLocaleString()}
              </span>
            )}
          </div>
          
          {/* Database age information */}
          {status.database_exists !== null && (
            <div style={{ fontSize: '0.9rem', opacity: 0.8 }}>
              {status.database_exists ? (
                status.database_age_days != null ? (
                  (() => {
                    const ageDays = status.database_age_days as number;
                    return ageDays < 1 ? (
                      <span style={{ color: '#28a745' }}>
                        📊 Database: Up to date (less than 1 day old)
                      </span>
                    ) : ageDays < 7 ? (
                      <span style={{ color: '#28a745' }}>
                        📊 Database: Recent ({ageDays} days old)
                      </span>
                    ) : ageDays < 30 ? (
                      <span style={{ color: '#ffc107' }}>
                        📊 Database: Moderate ({ageDays} days old - update recommended)
                      </span>
                    ) : (
                      <span style={{ color: '#dc3545' }}>
                        📊 Database: Outdated ({ageDays} days old - update strongly recommended!)
                      </span>
                    );
                  })()
                ) : (
                  <span style={{ color: '#6c757d' }}>
                    📊 Database: Found (age unknown)
                  </span>
                )
              ) : (
                <span style={{ color: '#6c757d' }}>
                  📊 Database: Not found (will be created on first update)
                </span>
              )}
            </div>
          )}
          
          {status.error_message && (
            <div style={{ marginTop: '0.5rem', color: '#dc3545' }}>
              Error: {status.error_message}
            </div>
          )}
        </div>
      </div>

      {(status.status === 'running' || logs.length > 0) && (
        <div style={{ marginTop: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <h4 style={{ margin: 0 }}>Update Logs</h4>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem' }}>
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
              />
              Auto-scroll
            </label>
          </div>
          <div
            style={{
              background: '#1e1e1e',
              color: '#d4d4d4',
              padding: '1rem',
              borderRadius: '4px',
              fontFamily: 'monospace',
              fontSize: '0.9rem',
              maxHeight: '400px',
              overflowY: 'auto',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {logs.length === 0 ? (
              <div style={{ opacity: 0.5 }}>Waiting for update logs...</div>
            ) : (
              logs.map((line, index) => (
                <div key={index} style={{ marginBottom: '0.25rem' }}>
                  {line}
                </div>
              ))
            )}
            <div ref={logsEndRef} />
          </div>
        </div>
      )}
    </div>
  )
}
