import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../utils/apiClient'

interface RegistryScanner {
  name: string
  enabled?: boolean
  scan_types?: string[]
  priority?: number
  description?: string
}

interface ScannerStatus {
  workers_running: number
  queue_size: number
  active_scans: number
  average_scan_time: number | null
  timeouts_today: number
  errors_today: number
  scans_completed_today: number
  queue_items: Array<{
    scan_id: string
    name: string
    target: string
    created_at: string | null
    priority: number
  }>
}

export default function ScannerManagementPage() {
  const [status, setStatus] = useState<ScannerStatus | null>(null)
  const [registry, setRegistry] = useState<RegistryScanner[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const loadStatus = async () => {
    setLoading(true)
    try {
      const response = await apiFetch('/api/admin/scanner')
      if (response.ok) {
        const data = await response.json()
        setStatus(data)
      }
    } catch (error) {
      console.error('Failed to load scanner status:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadRegistry = async () => {
    try {
      const response = await apiFetch('/api/scanners')
      if (response.ok) {
        const data = await response.json()
        setRegistry(Array.isArray(data.scanners) ? data.scanners : [])
      }
    } catch {
      setRegistry([])
    }
  }

  useEffect(() => {
    loadStatus()
    void loadRegistry()
    const interval = setInterval(loadStatus, 5000) // Refresh every 5 seconds
    return () => clearInterval(interval)
  }, [])

  const handleAction = async (action: 'pause' | 'resume' | 'restart') => {
    setActionLoading(action)
    try {
      const endpoint = action === 'restart' ? '/api/admin/scanner/restart-worker' : `/api/admin/scanner/${action}`
      const response = await apiFetch(endpoint, { method: 'POST' })
      if (response.ok) {
        const data = await response.json()
        alert(data.message || `${action} successful`)
        loadStatus()
      } else {
        const error = await response.json()
        alert(error.detail || `Failed to ${action}`)
      }
    } catch (error) {
      console.error(`Failed to ${action}:`, error)
      alert(`Failed to ${action}`)
    } finally {
      setActionLoading(null)
    }
  }

  const formatTime = (seconds: number | null): string => {
    if (!seconds) return 'N/A'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}m ${secs}s`
  }

  return (
    <div className="container" style={{ padding: '2rem' }}>
      <div style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>Scan Engine</h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            Workers, queue snapshot, and registered scanners. Tool timeouts &amp; tokens:{' '}
            <Link to="/admin/tool-settings">Tool settings</Link>.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={() => handleAction('pause')}
            disabled={actionLoading !== null}
            style={{ background: 'var(--color-high)' }}
          >
            {actionLoading === 'pause' ? 'Pausing...' : 'Pause'}
          </button>
          <button
            onClick={() => handleAction('resume')}
            disabled={actionLoading !== null}
            style={{ background: 'var(--color-pass)' }}
          >
            {actionLoading === 'resume' ? 'Resuming...' : 'Resume'}
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '2rem' }}>Loading...</div>
      ) : status ? (
        <>
          {/* Status Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
            <div style={{
              background: 'var(--glass-bg-main)',
              padding: '1.5rem',
              borderRadius: '8px',
              border: '1px solid var(--glass-border-main)'
            }}>
              <div style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--color-pass)' }}>
                {status.workers_running}
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Workers Running</div>
            </div>
            <div style={{
              background: 'var(--glass-bg-main)',
              padding: '1.5rem',
              borderRadius: '8px',
              border: '1px solid var(--glass-border-main)'
            }}>
              <div style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--color-medium)' }}>
                {status.queue_size}
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Queue Size</div>
            </div>
            <div style={{
              background: 'var(--glass-bg-main)',
              padding: '1.5rem',
              borderRadius: '8px',
              border: '1px solid var(--glass-border-main)'
            }}>
              <div style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--color-info)' }}>
                {status.active_scans}
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Active Scans</div>
            </div>
            <div style={{
              background: 'var(--glass-bg-main)',
              padding: '1.5rem',
              borderRadius: '8px',
              border: '1px solid var(--glass-border-main)'
            }}>
              <div style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--text-main)' }}>
                {formatTime(status.average_scan_time)}
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Avg Scan Time</div>
            </div>
          </div>

          {/* Today's Metrics */}
          <div style={{ marginBottom: '2rem' }}>
            <h2 style={{ marginBottom: '1rem' }}>Today's Metrics</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
              <div style={{
                background: 'var(--glass-bg-main)',
                padding: '1.5rem',
                borderRadius: '8px',
                border: '1px solid var(--glass-border-main)'
              }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--color-pass)' }}>
                  {status.scans_completed_today}
                </div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Completed</div>
              </div>
              <div style={{
                background: 'var(--glass-bg-main)',
                padding: '1.5rem',
                borderRadius: '8px',
                border: '1px solid var(--glass-border-main)'
              }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--color-critical)' }}>
                  {status.errors_today}
                </div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Errors</div>
              </div>
              <div style={{
                background: 'var(--glass-bg-main)',
                padding: '1.5rem',
                borderRadius: '8px',
                border: '1px solid var(--glass-border-main)'
              }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--color-high)' }}>
                  {status.timeouts_today}
                </div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Timeouts</div>
              </div>
            </div>
          </div>

          <div style={{ marginBottom: '2rem' }}>
            <h2 style={{ marginBottom: '1rem' }}>Scanner registry ({registry.length})</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '0.75rem' }}>
              Tools discovered in the scanner image (DB snapshot). Binary versions are resolved when each tool
              runs; use refresh on this page to sync after image updates.
            </p>
            {registry.length === 0 ? (
              <div style={{ padding: '1rem', color: 'var(--text-secondary)' }}>No scanners in DB yet.</div>
            ) : (
              <div style={{ overflowX: 'auto', border: '1px solid var(--glass-border-main)', borderRadius: 8 }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                  <thead>
                    <tr style={{ background: 'rgba(255,255,255,0.05)' }}>
                      <th style={{ padding: '0.75rem', textAlign: 'left' }}>Scanner</th>
                      <th style={{ padding: '0.75rem', textAlign: 'left' }}>Types</th>
                      <th style={{ padding: '0.75rem', textAlign: 'left' }}>Priority</th>
                      <th style={{ padding: '0.75rem', textAlign: 'left' }}>Enabled</th>
                    </tr>
                  </thead>
                  <tbody>
                    {registry.map((s) => (
                      <tr key={s.name} style={{ borderTop: '1px solid var(--glass-border-main)' }}>
                        <td style={{ padding: '0.75rem' }}>{s.name}</td>
                        <td style={{ padding: '0.75rem' }}>{(s.scan_types || []).join(', ') || '—'}</td>
                        <td style={{ padding: '0.75rem' }}>{s.priority ?? '—'}</td>
                        <td style={{ padding: '0.75rem' }}>{s.enabled !== false ? 'Yes' : 'No'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Queue Items */}
          <div>
            <h2 style={{ marginBottom: '1rem' }}>Queue (next 10 pending)</h2>
            <div style={{
              background: 'var(--glass-bg-main)',
              borderRadius: '8px',
              overflow: 'hidden',
              border: '1px solid var(--glass-border-main)'
            }}>
              {status.queue_items.length === 0 ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                  Queue is empty
                </div>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: 'rgba(255, 255, 255, 0.05)' }}>
                      <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid var(--glass-border-main)' }}>Scan Name</th>
                      <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid var(--glass-border-main)' }}>Target</th>
                      <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid var(--glass-border-main)' }}>Priority</th>
                      <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid var(--glass-border-main)' }}>Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {status.queue_items.map((item) => (
                      <tr key={item.scan_id} style={{ borderBottom: '1px solid var(--glass-border-main)' }}>
                        <td style={{ padding: '1rem', fontSize: '0.9rem' }}>{item.name}</td>
                        <td style={{ padding: '1rem', fontSize: '0.85rem', fontFamily: 'monospace' }}>
                          {item.target.length > 50 ? `${item.target.substring(0, 50)}...` : item.target}
                        </td>
                        <td style={{ padding: '1rem', fontSize: '0.9rem' }}>
                          <span style={{
                            padding: '0.25rem 0.5rem',
                            borderRadius: '4px',
                            background: item.priority > 0 ? 'rgba(255, 193, 7, 0.2)' : 'rgba(108, 117, 125, 0.2)',
                            color: item.priority > 0 ? 'var(--color-medium)' : 'var(--text-secondary)'
                          }}>
                            {item.priority}
                          </span>
                        </td>
                        <td style={{ padding: '1rem', fontSize: '0.9rem' }}>
                          {item.created_at ? new Date(item.created_at).toLocaleString() : 'N/A'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </>
      ) : (
        <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
          Failed to load scanner status
        </div>
      )}
    </div>
  )
}
