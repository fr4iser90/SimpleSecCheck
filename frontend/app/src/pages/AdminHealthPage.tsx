import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../hooks/useAuth'
import { apiFetch } from '../utils/apiClient'
import { Link } from 'react-router-dom'

interface SystemHealth {
  overall: string
  database: { status?: boolean; error?: string; [k: string]: unknown }
  redis: { status?: boolean; error?: string; [k: string]: unknown }
  worker: {
    url?: string
    reachable?: boolean
    http_status?: number
    error?: string
  }
}

export default function AdminHealthPage() {
  const { isAuthenticated, user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [data, setData] = useState<SystemHealth | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      setError(null)
      const r = await apiFetch('/api/admin/system-health')
      if (!r.ok) throw new Error('Failed to load system health')
      setData(await r.json())
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Load failed')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!isAuthenticated || !isAdmin) return
    void load()
    const t = setInterval(load, 15000)
    return () => clearInterval(t)
  }, [isAuthenticated, isAdmin, load])

  if (!isAuthenticated || !isAdmin) {
    return (
      <div className="admin-settings-page">
        <div className="admin-settings-container">
          <h2>Access Denied</h2>
        </div>
      </div>
    )
  }

  const pill = (ok: boolean | undefined) => (
    <span
      style={{
        padding: '0.2rem 0.6rem',
        borderRadius: 6,
        fontSize: '0.8rem',
        fontWeight: 600,
        background: ok ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)',
        color: ok ? 'var(--color-pass)' : 'var(--color-critical)',
      }}
    >
      {ok ? 'OK' : 'FAIL'}
    </span>
  )

  return (
    <div className="admin-settings-page">
      <div className="admin-settings-container">
        <p style={{ marginBottom: '1rem' }}>
          <Link to="/admin">← Admin</Link>
        </p>
        <h2>System Health</h2>
        <p className="section-description" style={{ marginBottom: '1.5rem' }}>
          Database, Redis, and worker API checks. Refreshes every 15s.
        </p>
        {error && <div className="error-message">{error}</div>}
        {loading && !data && <div className="loading">Loading…</div>}
        {data && (
          <>
            <div style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <strong>Overall:</strong>
              <span
                style={{
                  textTransform: 'uppercase',
                  fontWeight: 700,
                  color:
                    data.overall === 'healthy' ? 'var(--color-pass)' : 'var(--color-high)',
                }}
              >
                {data.overall}
              </span>
              <button type="button" className="btn-secondary" onClick={() => { setLoading(true); void load() }}>
                Refresh now
              </button>
            </div>
            <div
              style={{
                display: 'grid',
                gap: '1rem',
                gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
              }}
            >
              <div
                className="settings-section"
                style={{ padding: '1.25rem', border: '1px solid var(--glass-border-dark)', borderRadius: 12 }}
              >
                <h3 style={{ marginTop: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  PostgreSQL {pill(data.database?.status)}
                </h3>
                <pre
                  style={{
                    fontSize: '0.75rem',
                    overflow: 'auto',
                    maxHeight: 160,
                    margin: 0,
                    color: 'var(--text-secondary)',
                  }}
                >
                  {JSON.stringify(data.database, null, 2)}
                </pre>
              </div>
              <div
                className="settings-section"
                style={{ padding: '1.25rem', border: '1px solid var(--glass-border-dark)', borderRadius: 12 }}
              >
                <h3 style={{ marginTop: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  Redis {pill(data.redis?.status)}
                </h3>
                <pre
                  style={{
                    fontSize: '0.75rem',
                    overflow: 'auto',
                    maxHeight: 160,
                    margin: 0,
                    color: 'var(--text-secondary)',
                  }}
                >
                  {JSON.stringify(data.redis, null, 2)}
                </pre>
              </div>
              <div
                className="settings-section"
                style={{ padding: '1.25rem', border: '1px solid var(--glass-border-dark)', borderRadius: 12 }}
              >
                <h3 style={{ marginTop: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  Worker API {pill(data.worker?.reachable)}
                </h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0 0 0.5rem' }}>
                  {data.worker?.url}
                </p>
                {data.worker?.http_status != null && (
                  <p style={{ fontSize: '0.85rem' }}>HTTP {data.worker.http_status}</p>
                )}
                {data.worker?.error && (
                  <p style={{ fontSize: '0.85rem', color: 'var(--color-critical)' }}>{data.worker.error}</p>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
