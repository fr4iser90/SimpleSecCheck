import { useState, useEffect } from 'react'
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
    expires_at: ''
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
    const interval = setInterval(loadData, 30000) // Refresh every 30 seconds
    return () => clearInterval(interval)
  }, [])

  const handleBlock = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const response = await apiFetch('/api/admin/security/ip-control/block', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(blockForm)
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
        method: 'POST'
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
    <div className="container" style={{ padding: '2rem' }}>
      <div style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>IP & Abuse Protection</h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            Monitor and protect against abuse, brute force, and suspicious activity
          </p>
        </div>
        <button className="primary" onClick={() => setShowBlockModal(true)}>
          + Block IP
        </button>
      </div>

      {/* Statistics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        <div style={{
          background: 'var(--glass-bg-dark)',
          padding: '1.5rem',
          borderRadius: '8px',
          border: '1px solid var(--glass-border-dark)'
        }}>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--color-critical)' }}>
            {statistics.total_blocked}
          </div>
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Blocked IPs</div>
        </div>
        <div style={{
          background: 'var(--glass-bg-dark)',
          padding: '1.5rem',
          borderRadius: '8px',
          border: '1px solid var(--glass-border-dark)'
        }}>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--color-high)' }}>
            {statistics.total_activity_24h}
          </div>
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Activity Events (24h)</div>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '2rem' }}>Loading...</div>
      ) : (
        <>
          {/* Blocked IPs */}
          <div style={{ marginBottom: '2rem' }}>
            <h2 style={{ marginBottom: '1rem' }}>Blocked IPs</h2>
            <div style={{
              background: 'var(--glass-bg-dark)',
              borderRadius: '8px',
              overflow: 'hidden',
              border: '1px solid var(--glass-border-dark)'
            }}>
              {blockedIPs.length === 0 ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                  No blocked IPs
                </div>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: 'rgba(255, 255, 255, 0.05)' }}>
                      <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid var(--glass-border-dark)' }}>IP Address</th>
                      <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid var(--glass-border-dark)' }}>Reason</th>
                      <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid var(--glass-border-dark)' }}>Blocked At</th>
                      <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid var(--glass-border-dark)' }}>Expires</th>
                      <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid var(--glass-border-dark)' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {blockedIPs.map((ip) => (
                      <tr key={ip.id} style={{ borderBottom: '1px solid var(--glass-border-dark)' }}>
                        <td style={{ padding: '1rem', fontSize: '0.9rem', fontFamily: 'monospace' }}>{ip.ip_address}</td>
                        <td style={{ padding: '1rem', fontSize: '0.9rem' }}>{ip.reason}</td>
                        <td style={{ padding: '1rem', fontSize: '0.9rem' }}>
                          {new Date(ip.blocked_at).toLocaleString()}
                        </td>
                        <td style={{ padding: '1rem', fontSize: '0.9rem' }}>
                          {ip.expires_at ? new Date(ip.expires_at).toLocaleString() : 'Permanent'}
                        </td>
                        <td style={{ padding: '1rem', fontSize: '0.9rem' }}>
                          <button
                            onClick={() => handleUnblock(ip.ip_address)}
                            style={{ fontSize: '0.85rem', padding: '0.25rem 0.5rem' }}
                          >
                            Unblock
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>

          {/* Suspicious Activity */}
          <div>
            <h2 style={{ marginBottom: '1rem' }}>Suspicious Activity (Last 24h)</h2>
            <div style={{
              background: 'var(--glass-bg-dark)',
              borderRadius: '8px',
              overflow: 'hidden',
              border: '1px solid var(--glass-border-dark)'
            }}>
              {suspicious.length === 0 ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                  No suspicious activity detected
                </div>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: 'rgba(255, 255, 255, 0.05)' }}>
                      <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid var(--glass-border-dark)' }}>IP Address</th>
                      <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid var(--glass-border-dark)' }}>Event Type</th>
                      <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid var(--glass-border-dark)' }}>Count</th>
                      <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid var(--glass-border-dark)' }}>Window Start</th>
                    </tr>
                  </thead>
                  <tbody>
                    {suspicious.map((activity, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid var(--glass-border-dark)' }}>
                        <td style={{ padding: '1rem', fontSize: '0.9rem', fontFamily: 'monospace' }}>{activity.ip_address}</td>
                        <td style={{ padding: '1rem', fontSize: '0.9rem' }}>{activity.event_type}</td>
                        <td style={{ padding: '1rem', fontSize: '0.9rem' }}>
                          <span style={{
                            padding: '0.25rem 0.5rem',
                            borderRadius: '4px',
                            background: activity.count > 10 ? 'rgba(220, 53, 69, 0.2)' : 'rgba(255, 193, 7, 0.2)',
                            color: activity.count > 10 ? 'var(--color-critical)' : 'var(--color-medium)'
                          }}>
                            {activity.count}
                          </span>
                        </td>
                        <td style={{ padding: '1rem', fontSize: '0.9rem' }}>
                          {new Date(activity.window_start).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </>
      )}

      {/* Block Modal */}
      {showBlockModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.7)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            background: 'var(--glass-bg-dark)',
            padding: '2rem',
            borderRadius: '8px',
            width: '90%',
            maxWidth: '500px',
            border: '1px solid var(--glass-border-dark)'
          }}>
            <h2 style={{ marginTop: 0 }}>Block IP Address</h2>
            <form onSubmit={handleBlock}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem' }}>IP Address</label>
                <input
                  type="text"
                  required
                  placeholder="192.168.1.100"
                  value={blockForm.ip_address}
                  onChange={(e) => setBlockForm({ ...blockForm, ip_address: e.target.value })}
                  style={{ width: '100%' }}
                />
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem' }}>Reason</label>
                <select
                  value={blockForm.reason}
                  onChange={(e) => setBlockForm({ ...blockForm, reason: e.target.value })}
                  style={{ width: '100%' }}
                >
                  <option value="manual">Manual</option>
                  <option value="brute_force">Brute Force</option>
                  <option value="request_spike">Request Spike</option>
                  <option value="suspicious_activity">Suspicious Activity</option>
                </select>
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem' }}>Expires At (Optional)</label>
                <input
                  type="datetime-local"
                  value={blockForm.expires_at}
                  onChange={(e) => setBlockForm({ ...blockForm, expires_at: e.target.value })}
                  style={{ width: '100%' }}
                />
                <small style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                  Leave empty for permanent block
                </small>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                <button type="button" onClick={() => setShowBlockModal(false)}>Cancel</button>
                <button type="submit" className="primary">Block IP</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
