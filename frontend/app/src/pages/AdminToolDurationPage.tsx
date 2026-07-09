import { useState, useEffect } from 'react'
import AdminPageShell from '../components/AdminPageShell'
import AdminPanel from '../components/AdminPanel'
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
    void fetchStats()
  }, [])

  return (
    <AdminPageShell
      title="Tool duration"
      subtitle="Admin-only: real per-tool run times used for queue estimates. No fake defaults."
      error={error}
      loading={loading}
    >
      {stats.length === 0 ? (
        <AdminPanel>
          <p style={{ textAlign: 'center', color: 'var(--ds-text-secondary)', margin: 0 }}>
            No scanner duration data yet. Run some scans so per-tool durations are recorded; then they will appear
            here.
          </p>
        </AdminPanel>
      ) : (
        <div className="admin-metrics">
          {stats.map((s) => (
            <div key={s.scanner_name} className="admin-metric">
              <div className="admin-metric__value admin-metric__value--info">
                {formatDuration(s.avg_duration_seconds)}
              </div>
              <div className="admin-metric__label">{s.scanner_name}</div>
              {(s.min_duration_seconds != null || s.max_duration_seconds != null) && (
                <div style={{ fontSize: '0.75rem', color: 'var(--ds-text-secondary)', marginTop: '0.5rem' }}>
                  {s.min_duration_seconds != null && formatDuration(s.min_duration_seconds)}
                  {s.min_duration_seconds != null && s.max_duration_seconds != null && ' – '}
                  {s.max_duration_seconds != null && formatDuration(s.max_duration_seconds)}
                  {s.sample_count > 0 && ` (${s.sample_count} runs)`}
                </div>
              )}
              {s.min_duration_seconds == null && s.max_duration_seconds == null && s.sample_count > 0 && (
                <div style={{ fontSize: '0.75rem', color: 'var(--ds-text-secondary)', marginTop: '0.5rem' }}>
                  {s.sample_count} runs
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </AdminPageShell>
  )
}
