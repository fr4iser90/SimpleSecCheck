import { useState, useEffect } from 'react'
import { apiFetch } from '../utils/apiClient'

interface AuditLogEntry {
  id: string
  user_id: string | null
  user_email: string | null
  action_type: string
  target: string | null
  details: any
  ip_address: string | null
  user_agent: string | null
  result: string
  created_at: string
}

export default function AuditLogPage() {
  const [entries, setEntries] = useState<AuditLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [limit] = useState(100)
  const [offset, setOffset] = useState(0)
  const [filters, setFilters] = useState({
    action_type: '',
    search: '',
    start_date: '',
    end_date: ''
  })

  const loadAuditLog = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString(),
        ...(filters.action_type && { action_type: filters.action_type }),
        ...(filters.search && { search: filters.search }),
        ...(filters.start_date && { start_date: filters.start_date }),
        ...(filters.end_date && { end_date: filters.end_date })
      })

      const response = await apiFetch(`/api/admin/audit-log?${params}`)
      if (response.ok) {
        const data = await response.json()
        setEntries(data.entries || [])
        setTotal(data.total || 0)
      }
    } catch (error) {
      console.error('Failed to load audit log:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAuditLog()
  }, [offset, filters])

  const handleExport = async (format: 'json' | 'csv') => {
    try {
      const params = new URLSearchParams({
        format,
        ...(filters.action_type && { action_type: filters.action_type }),
        ...(filters.start_date && { start_date: filters.start_date }),
        ...(filters.end_date && { end_date: filters.end_date })
      })

      const response = await apiFetch(`/api/admin/audit-log/export?${params}`)
      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `audit_log_${new Date().toISOString().split('T')[0]}.${format}`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      }
    } catch (error) {
      console.error('Failed to export audit log:', error)
    }
  }

  return (
    <div className="container" style={{ padding: '2rem' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h1>Audit Log</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
          Track all security-relevant events in the system
        </p>
      </div>

      {/* Filters */}
      <div style={{
        background: 'var(--glass-bg-dark)',
        padding: '1.5rem',
        borderRadius: '8px',
        marginBottom: '1.5rem',
        border: '1px solid var(--glass-border-dark)'
      }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Action Type</label>
            <select
              value={filters.action_type}
              onChange={(e) => setFilters({ ...filters, action_type: e.target.value })}
              style={{ width: '100%' }}
            >
              <option value="">All Actions</option>
              <option value="USER_CREATED">User Created</option>
              <option value="USER_UPDATED">User Updated</option>
              <option value="USER_DELETED">User Deleted</option>
              <option value="FEATURE_FLAG_CHANGED">Feature Flag Changed</option>
              <option value="LOGIN_FAILED">Login Failed</option>
              <option value="USER_LOGIN">User Login</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Search</label>
            <input
              type="text"
              placeholder="Search target or email..."
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              style={{ width: '100%' }}
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Start Date</label>
            <input
              type="date"
              value={filters.start_date}
              onChange={(e) => setFilters({ ...filters, start_date: e.target.value })}
              style={{ width: '100%' }}
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem' }}>End Date</label>
            <input
              type="date"
              value={filters.end_date}
              onChange={(e) => setFilters({ ...filters, end_date: e.target.value })}
              style={{ width: '100%' }}
            />
          </div>
        </div>
        <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem' }}>
          <button onClick={() => handleExport('json')}>Export JSON</button>
          <button onClick={() => handleExport('csv')}>Export CSV</button>
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '2rem' }}>Loading...</div>
      ) : (
        <>
          <div style={{
            background: 'var(--glass-bg-dark)',
            borderRadius: '8px',
            overflow: 'hidden',
            border: '1px solid var(--glass-border-dark)'
          }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr className="table-head-row">
                  <th className="table-cell-head">Time</th>
                  <th className="table-cell-head">User</th>
                  <th className="table-cell-head">Action</th>
                  <th className="table-cell-head">Target</th>
                  <th className="table-cell-head">IP</th>
                  <th className="table-cell-head">Result</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr key={entry.id} className="table-row-divider">
                    <td className="table-cell">
                      {new Date(entry.created_at).toLocaleString()}
                    </td>
                    <td className="table-cell">
                      {entry.user_email || 'System'}
                    </td>
                    <td className="table-cell">
                      {entry.action_type}
                    </td>
                    <td className="table-cell">
                      {entry.target || '-'}
                    </td>
                    <td className="table-cell">
                      {entry.ip_address || '-'}
                    </td>
                    <td className="table-cell">
                      <span style={{
                        color: entry.result === 'success' ? 'var(--color-pass)' : 'var(--color-critical)'
                      }}>
                        {entry.result}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ color: 'var(--text-secondary)' }}>
              Showing {offset + 1} to {Math.min(offset + limit, total)} of {total} entries
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                onClick={() => setOffset(Math.max(0, offset - limit))}
                disabled={offset === 0}
              >
                Previous
              </button>
              <button
                onClick={() => setOffset(offset + limit)}
                disabled={offset + limit >= total}
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
