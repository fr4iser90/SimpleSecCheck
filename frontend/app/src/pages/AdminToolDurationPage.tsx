import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { apiFetch } from '../utils/apiClient'

interface ScannerDurationStat {
  scanner_name: string
  avg_duration_seconds: number
  min_duration_seconds: number | null
  max_duration_seconds: number | null
  sample_count: number
  last_updated: string | null
}

function formatDuration(seconds: number): string {
  if (seconds <= 0 || !Number.isFinite(seconds)) return '—'
  if (seconds < 60) return `${Math.round(seconds)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return s ? `${m}m ${s}s` : `${m}m`
}

export default function AdminToolDurationPage() {
  const { isAuthenticated, user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [stats, setStats] = useState<ScannerDurationStat[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await apiFetch('/api/admin/scanner-duration-stats')
        if (!response.ok) throw new Error('Failed to fetch scanner duration stats')
        const data = await response.json()
        setStats(data.scanner_duration_stats || [])
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
        setStats([])
      } finally {
        setLoading(false)
      }
    }
    if (isAuthenticated && isAdmin) fetchStats()
    else setLoading(false)
  }, [isAuthenticated, isAdmin])

  if (!isAuthenticated || !isAdmin) {
    return (
      <div className="admin-settings-page">
        <div className="admin-settings-container">
          <h2>Access Denied</h2>
          <p>You must be logged in as an admin to view tool duration statistics.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="admin-settings-page">
      <div className="admin-settings-container">
        <div style={{ marginBottom: '1.5rem' }}>
          <Link to="/admin" style={{ color: 'var(--text-secondary)', textDecoration: 'none' }}>
            ← Admin Dashboard
          </Link>
        </div>
        <header className="statistics-header" style={{ marginBottom: '1.5rem' }}>
          <h1>Tool duration (exact time per scanner)</h1>
          <p className="statistics-subtitle" style={{ opacity: 0.8, marginTop: '0.5rem' }}>
            Admin-only: real per-tool run times used for queue estimates. No fake defaults.
          </p>
        </header>

        {error && (
          <div className="statistics-error" style={{ marginBottom: '1rem' }}>
            {error}
          </div>
        )}

        {loading ? (
          <div>Loading…</div>
        ) : stats.length === 0 ? (
          <div className="statistics-empty" style={{ padding: '2rem', textAlign: 'center' }}>
            No scanner duration data yet. Run some scans so per-tool durations are recorded; then they will appear here.
          </div>
        ) : (
          <section className="statistics-section">
            <div className="statistics-grid statistics-grid--duration" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '1rem' }}>
              {stats.map((s) => (
                <div
                  key={s.scanner_name}
                  className="stat-card stat-card--neutral"
                  style={{
                    padding: '1rem',
                    background: 'var(--glass-bg-dark)',
                    border: '1px solid var(--glass-border-dark)',
                    borderRadius: '12px',
                  }}
                >
                  <span className="stat-value" style={{ display: 'block', fontSize: '1.5rem' }}>
                    {formatDuration(s.avg_duration_seconds)}
                  </span>
                  <span className="stat-label" style={{ display: 'block', marginTop: '0.25rem' }}>
                    {s.scanner_name}
                  </span>
                  {(s.min_duration_seconds != null || s.max_duration_seconds != null) && (
                    <span style={{ fontSize: '0.8rem', opacity: 0.8, display: 'block', marginTop: '0.5rem' }}>
                      {s.min_duration_seconds != null && formatDuration(s.min_duration_seconds)}
                      {s.min_duration_seconds != null && s.max_duration_seconds != null && ' – '}
                      {s.max_duration_seconds != null && formatDuration(s.max_duration_seconds)}
                      {s.sample_count > 0 && ` (${s.sample_count} runs)`}
                    </span>
                  )}
                  {s.min_duration_seconds == null && s.max_duration_seconds == null && s.sample_count > 0 && (
                    <span style={{ fontSize: '0.8rem', opacity: 0.8, display: 'block', marginTop: '0.5rem' }}>
                      {s.sample_count} runs
                    </span>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}
