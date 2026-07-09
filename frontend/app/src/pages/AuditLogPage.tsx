import { useState, useEffect } from 'react'
import AdminPageShell from '../components/AdminPageShell'
import AdminPanel from '../components/AdminPanel'
import { apiFetch } from '../utils/apiClient'

interface AuditLogEntry {
  id: string
  user_id: string | null
  user_email: string | null
  action_type: string
  target: string | null
  details: unknown
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
    end_date: '',
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
        ...(filters.end_date && { end_date: filters.end_date }),
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
        ...(filters.end_date && { end_date: filters.end_date }),
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
    <AdminPageShell
      title="Audit Log"
      subtitle="Security-relevant actions performed on this instance."
      calloutTitle="Quick reference"
      callout={
        <dl className="page-kv-list">
          <div>
            <dt>Events</dt>
            <dd>Logins, configuration changes, scan control, and admin actions.</dd>
          </div>
          <div>
            <dt>Export</dt>
            <dd>Download filtered results as JSON or CSV for compliance reviews.</dd>
          </div>
          <div>
            <dt>Retention</dt>
            <dd>Entries are stored in the application database; filter by date to narrow results.</dd>
          </div>
        </dl>
      }
      loading={loading}
    >
      <AdminPanel title="Filters">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          <div className="form-group">
            <label>Action Type</label>
            <select
              value={filters.action_type}
              onChange={(e) => setFilters({ ...filters, action_type: e.target.value })}
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
          <div className="form-group">
            <label>Search</label>
            <input
              type="text"
              placeholder="Search target or email…"
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label>Start Date</label>
            <input
              type="date"
              value={filters.start_date}
              onChange={(e) => setFilters({ ...filters, start_date: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label>End Date</label>
            <input
              type="date"
              value={filters.end_date}
              onChange={(e) => setFilters({ ...filters, end_date: e.target.value })}
            />
          </div>
        </div>
        <div className="admin-page-actions" style={{ marginTop: '0.5rem' }}>
          <button type="button" className="btn-secondary" onClick={() => handleExport('json')}>
            Export JSON
          </button>
          <button type="button" className="btn-secondary" onClick={() => handleExport('csv')}>
            Export CSV
          </button>
        </div>
      </AdminPanel>

      <AdminPanel flush>
        <div className="desktop-only-table data-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>User</th>
                <th>Action</th>
                <th>Target</th>
                <th>IP</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.id}>
                  <td>{new Date(entry.created_at).toLocaleString()}</td>
                  <td>{entry.user_email || 'System'}</td>
                  <td>{entry.action_type}</td>
                  <td>{entry.target || '—'}</td>
                  <td>{entry.ip_address || '—'}</td>
                  <td>
                    <span
                      className={`status-pill${entry.result === 'success' ? ' status-pill--active' : ''}`}
                      style={
                        entry.result !== 'success'
                          ? { background: 'var(--ds-error-soft)', color: 'var(--ds-error)' }
                          : undefined
                      }
                    >
                      {entry.result}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mobile-card-list" aria-label="Audit log (mobile)">
          {entries.map((entry) => (
            <article key={entry.id} className="mobile-data-card">
              <h3 className="mobile-data-card__title">{entry.action_type}</h3>
              <p className="mobile-data-card__subtitle">{entry.user_email || 'System'}</p>
              <div className="mobile-data-card__grid">
                <div className="mobile-data-card__row">
                  <span className="mobile-data-card__label">Time</span>
                  <span className="mobile-data-card__value">{new Date(entry.created_at).toLocaleString()}</span>
                </div>
                <div className="mobile-data-card__row">
                  <span className="mobile-data-card__label">Target</span>
                  <span className="mobile-data-card__value">{entry.target || '—'}</span>
                </div>
                <div className="mobile-data-card__row">
                  <span className="mobile-data-card__label">IP</span>
                  <span className="mobile-data-card__value">{entry.ip_address || '—'}</span>
                </div>
                <div className="mobile-data-card__row">
                  <span className="mobile-data-card__label">Result</span>
                  <span
                    className={`status-pill${entry.result === 'success' ? ' status-pill--active' : ''}`}
                    style={
                      entry.result !== 'success'
                        ? { background: 'var(--ds-error-soft)', color: 'var(--ds-error)' }
                        : undefined
                    }
                  >
                    {entry.result}
                  </span>
                </div>
              </div>
            </article>
          ))}
        </div>
      </AdminPanel>

      <div className="admin-page-actions" style={{ marginTop: '1rem', justifyContent: 'space-between' }}>
        <div style={{ color: 'var(--ds-text-secondary)', fontSize: '0.875rem' }}>
          Showing {offset + 1} to {Math.min(offset + limit, total)} of {total} entries
        </div>
        <div className="admin-page-actions">
          <button
            type="button"
            className="btn-secondary"
            onClick={() => setOffset(Math.max(0, offset - limit))}
            disabled={offset === 0}
          >
            Previous
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => setOffset(offset + limit)}
            disabled={offset + limit >= total}
          >
            Next
          </button>
        </div>
      </div>
    </AdminPageShell>
  )
}
