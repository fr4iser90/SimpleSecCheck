import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import AdminPageShell from '../components/AdminPageShell'
import AdminPanel from '../components/AdminPanel'
import { useToast } from '../context/ToastContext'
import { POLL_ADMIN_SCANNER_MS } from '../constants/polling'
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
  const toast = useToast()
  const [status, setStatus] = useState<ScannerStatus | null>(null)
  const [registry, setRegistry] = useState<RegistryScanner[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const loadStatus = async (silent = false) => {
    if (!silent) setLoading(true)
    try {
      const response = await apiFetch('/api/admin/scanner')
      if (response.ok) {
        const data = await response.json()
        setStatus(data)
      }
    } catch (error) {
      console.error('Failed to load scanner status:', error)
    } finally {
      if (!silent) setLoading(false)
    }
  }

  const loadRegistry = async () => {
    try {
      const response = await apiFetch('/api/scanners/')
      if (response.ok) {
        const data = await response.json()
        setRegistry(Array.isArray(data.scanners) ? data.scanners : [])
      }
    } catch {
      setRegistry([])
    }
  }

  useEffect(() => {
    void loadStatus(false)
    void loadRegistry()
    const interval = setInterval(() => void loadStatus(true), POLL_ADMIN_SCANNER_MS)
    return () => clearInterval(interval)
  }, [])

  const handleAction = async (action: 'pause' | 'resume' | 'restart') => {
    setActionLoading(action)
    try {
      const endpoint = action === 'restart' ? '/api/admin/scanner/restart-worker' : `/api/admin/scanner/${action}`
      const response = await apiFetch(endpoint, { method: 'POST' })
      if (response.ok) {
        const data = await response.json()
        toast.success(data.message || `${action} successful`)
        loadStatus()
      } else {
        const error = await response.json()
        toast.error(error.detail || `Failed to ${action}`)
      }
    } catch (error) {
      console.error(`Failed to ${action}:`, error)
      toast.error(`Failed to ${action}`)
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
    <AdminPageShell
      title="Scan Engine"
      subtitle="Worker status, queue snapshot, and registered scanner tools."
      calloutTitle="Quick reference"
      callout={
        <dl className="page-kv-list">
          <div>
            <dt>Workers</dt>
            <dd>Pause or resume the scan worker without restarting the whole stack.</dd>
          </div>
          <div>
            <dt>Queue</dt>
            <dd>Live pending jobs — ordering and concurrency: <Link to="/admin/execution">Execution</Link>.</dd>
          </div>
          <div>
            <dt>Tools</dt>
            <dd>Per-scanner timeouts and tokens: <Link to="/admin/tool-settings">Tool settings</Link>.</dd>
          </div>
        </dl>
      }
      loading={loading && !status}
      actions={
        <div className="admin-page-actions">
          <button
            type="button"
            className="btn-secondary"
            onClick={() => handleAction('pause')}
            disabled={actionLoading !== null}
          >
            {actionLoading === 'pause' ? 'Pausing…' : 'Pause'}
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={() => handleAction('resume')}
            disabled={actionLoading !== null}
          >
            {actionLoading === 'resume' ? 'Resuming…' : 'Resume'}
          </button>
        </div>
      }
    >
      {status ? (
        <>
          <div className="admin-metrics">
            <div className="admin-metric">
              <div className="admin-metric__value admin-metric__value--pass">{status.workers_running}</div>
              <div className="admin-metric__label">Workers Running</div>
            </div>
            <div className="admin-metric">
              <div className="admin-metric__value admin-metric__value--high">{status.queue_size}</div>
              <div className="admin-metric__label">Queue Size</div>
            </div>
            <div className="admin-metric">
              <div className="admin-metric__value admin-metric__value--info">{status.active_scans}</div>
              <div className="admin-metric__label">Active Scans</div>
            </div>
            <div className="admin-metric">
              <div className="admin-metric__value admin-metric__value--neutral">{formatTime(status.average_scan_time)}</div>
              <div className="admin-metric__label">Avg Scan Time</div>
            </div>
          </div>

          <AdminPanel title="Today's metrics">
            <div className="admin-metrics" style={{ marginBottom: 0 }}>
              <div className="admin-metric">
                <div className="admin-metric__value admin-metric__value--pass">{status.scans_completed_today}</div>
                <div className="admin-metric__label">Completed</div>
              </div>
              <div className="admin-metric">
                <div className="admin-metric__value admin-metric__value--critical">{status.errors_today}</div>
                <div className="admin-metric__label">Errors</div>
              </div>
              <div className="admin-metric">
                <div className="admin-metric__value admin-metric__value--high">{status.timeouts_today}</div>
                <div className="admin-metric__label">Timeouts</div>
              </div>
            </div>
          </AdminPanel>

          <AdminPanel
            title={`Scanner registry (${registry.length})`}
            description="Tools discovered in the scanner image (DB snapshot). Binary versions are resolved when each tool runs; use refresh on this page to sync after image updates."
            flush
          >
            {registry.length === 0 ? (
              <div style={{ padding: '1.5rem', color: 'var(--ds-text-secondary)' }}>No scanners in DB yet.</div>
            ) : (
              <div className="data-table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Scanner</th>
                      <th>Types</th>
                      <th>Priority</th>
                      <th>Enabled</th>
                    </tr>
                  </thead>
                  <tbody>
                    {registry.map((s) => (
                      <tr key={s.name}>
                        <td>{s.name}</td>
                        <td>{(s.scan_types || []).join(', ') || '—'}</td>
                        <td>{s.priority ?? '—'}</td>
                        <td>{s.enabled !== false ? 'Yes' : 'No'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </AdminPanel>

          <AdminPanel title="Queue (next 10 pending)" flush>
            {status.queue_items.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--ds-text-secondary)' }}>
                Queue is empty
              </div>
            ) : (
              <div className="data-table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Scan Name</th>
                      <th>Target</th>
                      <th>Priority</th>
                      <th>Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {status.queue_items.map((item) => (
                      <tr key={item.scan_id}>
                        <td>{item.name}</td>
                        <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                          {item.target.length > 50 ? `${item.target.substring(0, 50)}...` : item.target}
                        </td>
                        <td>
                          <span className={`status-pill${item.priority > 0 ? ' status-pill--pending' : ''}`}>
                            {item.priority}
                          </span>
                        </td>
                        <td>{item.created_at ? new Date(item.created_at).toLocaleString() : 'N/A'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </AdminPanel>
        </>
      ) : (
        !loading && (
          <AdminPanel>
            <p style={{ textAlign: 'center', color: 'var(--ds-text-secondary)', margin: 0 }}>
              Failed to load scanner status
            </p>
          </AdminPanel>
        )
      )}
    </AdminPageShell>
  )
}
