import { useState, useEffect } from 'react'
import AdminPageShell from '../components/AdminPageShell'
import AdminPanel from '../components/AdminPanel'
import { apiFetch } from '../utils/apiClient'

interface BlockedIP {
  id: string
  ip_address: string
  reason: string
  blocked_at: string
  expires_at: string | null
}

interface SuspiciousActivity {
  ip_address: string
  event_type: string
  count: number
  window_start: string
}

export default function IPControlPage() {
  const [blockedIPs, setBlockedIPs] = useState<BlockedIP[]>([])
  const [suspicious, setSuspicious] = useState<SuspiciousActivity[]>([])
  const [statistics, setStatistics] = useState({ total_blocked: 0, total_activity_24h: 0 })
  const [loading, setLoading] = useState(true)
  const [showBlockModal, setShowBlockModal] = useState(false)
  const [blockForm, setBlockForm] = useState({
    ip_address: '',
    reason: 'manual',
    expires_at: '',
  })

  const loadData = async () => {
    setLoading(true)
    try {
      const response = await apiFetch('/api/admin/security/ip-control')
      if (response.ok) {
        const data = await response.json()
        setBlockedIPs(data.blocked_ips || [])
        setSuspicious(data.suspicious_activity || [])
        setStatistics(data.statistics || {})
      }
    } catch (error) {
      console.error('Failed to load IP control data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 30000)
    return () => clearInterval(interval)
  }, [])

  const handleBlock = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const response = await apiFetch('/api/admin/security/ip-control/block', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(blockForm),
      })
      if (response.ok) {
        setShowBlockModal(false)
        setBlockForm({ ip_address: '', reason: 'manual', expires_at: '' })
        loadData()
      } else {
        const error = await response.json()
        alert(error.detail || 'Failed to block IP')
      }
    } catch (error) {
      console.error('Failed to block IP:', error)
      alert('Failed to block IP')
    }
  }

  const handleUnblock = async (ip: string) => {
    if (!confirm(`Are you sure you want to unblock ${ip}?`)) return
    try {
      const response = await apiFetch(`/api/admin/security/ip-control/unblock?ip_address=${encodeURIComponent(ip)}`, {
        method: 'POST',
      })
      if (response.ok) {
        loadData()
      } else {
        const error = await response.json()
        alert(error.detail || 'Failed to unblock IP')
      }
    } catch (error) {
      console.error('Failed to unblock IP:', error)
      alert('Failed to unblock IP')
    }
  }

  return (
    <AdminPageShell
      title="IP & Abuse Protection"
      subtitle="Monitor and protect against abuse, brute force, and suspicious activity"
      loading={loading}
      actions={
        <button type="button" className="btn-primary" onClick={() => setShowBlockModal(true)}>
          + Block IP
        </button>
      }
    >
      <div className="admin-metrics">
        <div className="admin-metric">
          <div className="admin-metric__value admin-metric__value--critical">{statistics.total_blocked}</div>
          <div className="admin-metric__label">Blocked IPs</div>
        </div>
        <div className="admin-metric">
          <div className="admin-metric__value admin-metric__value--high">{statistics.total_activity_24h}</div>
          <div className="admin-metric__label">Activity Events (24h)</div>
        </div>
      </div>

      <AdminPanel title="Blocked IPs" flush>
        {blockedIPs.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--ds-text-secondary)' }}>No blocked IPs</div>
        ) : (
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>IP Address</th>
                  <th>Reason</th>
                  <th>Blocked At</th>
                  <th>Expires</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {blockedIPs.map((ip) => (
                  <tr key={ip.id}>
                    <td style={{ fontFamily: 'monospace' }}>{ip.ip_address}</td>
                    <td>{ip.reason}</td>
                    <td>{new Date(ip.blocked_at).toLocaleString()}</td>
                    <td>{ip.expires_at ? new Date(ip.expires_at).toLocaleString() : 'Permanent'}</td>
                    <td>
                      <button type="button" className="btn-secondary" onClick={() => handleUnblock(ip.ip_address)}>
                        Unblock
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </AdminPanel>

      <AdminPanel title="Suspicious Activity (Last 24h)" flush>
        {suspicious.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--ds-text-secondary)' }}>
            No suspicious activity detected
          </div>
        ) : (
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>IP Address</th>
                  <th>Event Type</th>
                  <th>Count</th>
                  <th>Window Start</th>
                </tr>
              </thead>
              <tbody>
                {suspicious.map((activity, idx) => (
                  <tr key={idx}>
                    <td style={{ fontFamily: 'monospace' }}>{activity.ip_address}</td>
                    <td>{activity.event_type}</td>
                    <td>
                      <span
                        className="status-pill"
                        style={
                          activity.count > 10
                            ? { background: 'var(--ds-error-soft)', color: 'var(--ds-error)' }
                            : { background: 'var(--ds-warning-soft)', color: 'var(--ds-warning)' }
                        }
                      >
                        {activity.count}
                      </span>
                    </td>
                    <td>{new Date(activity.window_start).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </AdminPanel>

      {showBlockModal && (
        <div className="ui-modal-overlay">
          <div className="ui-modal">
            <h2 className="ui-modal__title">Block IP Address</h2>
            <form onSubmit={handleBlock}>
              <div className="form-group">
                <label>IP Address</label>
                <input
                  type="text"
                  required
                  placeholder="192.168.1.100"
                  value={blockForm.ip_address}
                  onChange={(e) => setBlockForm({ ...blockForm, ip_address: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Reason</label>
                <select
                  value={blockForm.reason}
                  onChange={(e) => setBlockForm({ ...blockForm, reason: e.target.value })}
                >
                  <option value="manual">Manual</option>
                  <option value="brute_force">Brute Force</option>
                  <option value="request_spike">Request Spike</option>
                  <option value="suspicious_activity">Suspicious Activity</option>
                </select>
              </div>
              <div className="form-group">
                <label>Expires At (Optional)</label>
                <input
                  type="datetime-local"
                  value={blockForm.expires_at}
                  onChange={(e) => setBlockForm({ ...blockForm, expires_at: e.target.value })}
                />
                <small style={{ color: 'var(--ds-text-secondary)', fontSize: '0.85rem' }}>
                  Leave empty for permanent block
                </small>
              </div>
              <div className="ui-modal__actions">
                <button type="button" className="btn-secondary" onClick={() => setShowBlockModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Block IP
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AdminPageShell>
  )
}
