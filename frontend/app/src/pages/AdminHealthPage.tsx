import { useState, useCallback } from 'react'
import AdminPageShell from '../components/AdminPageShell'
import RefreshToolbar from '../components/RefreshToolbar'
import { useAutoRefresh } from '../hooks/useAutoRefresh'
import { POLL_ADMIN_HEALTH_MS } from '../constants/polling'
import { apiFetch } from '../utils/apiClient'

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
  const [data, setData] = useState<SystemHealth | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async ({ silent }: { silent: boolean }) => {
    try {
      if (!silent) setError(null)
      const r = await apiFetch('/api/admin/system-health')
      if (!r.ok) throw new Error('Failed to load system health')
      setData(await r.json())
    } catch (e: unknown) {
      if (!silent) setError(e instanceof Error ? e.message : 'Load failed')
    }
  }, [])

  const { autoRefresh, setAutoRefresh, refresh, isRefreshing, initialLoad, lastUpdated } = useAutoRefresh(load, {
    intervalMs: POLL_ADMIN_HEALTH_MS,
  })

  const pill = (ok: boolean | undefined) => (
    <span
      className={`status-pill${ok ? ' status-pill--active' : ''}`}
      style={ok ? undefined : { background: 'var(--ds-error-soft)', color: 'var(--ds-error)' }}
    >
      {ok ? 'OK' : 'FAIL'}
    </span>
  )

  return (
    <AdminPageShell
      title="System Health"
      subtitle="Live connectivity checks for core services."
      calloutTitle="Quick reference"
      callout={
        <dl className="page-kv-list">
          <div>
            <dt>Database</dt>
            <dd>PostgreSQL — required for users, scans, and configuration.</dd>
          </div>
          <div>
            <dt>Redis</dt>
            <dd>Queue and caching layer between API and workers.</dd>
          </div>
          <div>
            <dt>Worker</dt>
            <dd>Scanner worker HTTP API — must be reachable for scans to run.</dd>
          </div>
        </dl>
      }
      error={error}
      loading={initialLoad && !data}
      actions={
        <RefreshToolbar
          autoRefresh={autoRefresh}
          onAutoRefreshChange={setAutoRefresh}
          onRefresh={refresh}
          isRefreshing={isRefreshing}
          lastUpdated={lastUpdated}
          intervalMs={POLL_ADMIN_HEALTH_MS}
          compact
        />
      }
    >
      {data && (
        <>
          <div className="admin-page-actions" style={{ marginBottom: '1.25rem' }}>
            <strong>Overall:</strong>
            <span
              style={{
                textTransform: 'uppercase',
                fontWeight: 700,
                color: data.overall === 'healthy' ? 'var(--ds-success)' : 'var(--ds-warning)',
              }}
            >
              {data.overall}
            </span>
          </div>
          <div className="admin-health-grid">
            <div className="settings-section">
              <h3 style={{ marginTop: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                PostgreSQL {pill(data.database?.status)}
              </h3>
              <pre className="code-stream" style={{ maxHeight: 160, margin: 0 }}>
                {JSON.stringify(data.database, null, 2)}
              </pre>
            </div>
            <div className="settings-section">
              <h3 style={{ marginTop: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                Redis {pill(data.redis?.status)}
              </h3>
              <pre className="code-stream" style={{ maxHeight: 160, margin: 0 }}>
                {JSON.stringify(data.redis, null, 2)}
              </pre>
            </div>
            <div className="settings-section">
              <h3 style={{ marginTop: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                Worker API {pill(data.worker?.reachable)}
              </h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--ds-text-secondary)', margin: '0 0 0.5rem' }}>
                {data.worker?.url}
              </p>
              {data.worker?.http_status != null && (
                <p style={{ fontSize: '0.85rem' }}>HTTP {data.worker.http_status}</p>
              )}
              {data.worker?.error && (
                <p style={{ fontSize: '0.85rem', color: 'var(--ds-error)' }}>{data.worker.error}</p>
              )}
            </div>
          </div>
        </>
      )}
    </AdminPageShell>
  )
}
