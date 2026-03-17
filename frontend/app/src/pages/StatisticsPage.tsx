import { useState, useEffect } from 'react'
import { apiFetch } from '../utils/apiClient'

/** Matches backend ScanStatisticsSchema (/api/v1/scans/statistics) */
interface Statistics {
  total_scans: number
  pending_scans: number
  running_scans: number
  completed_scans: number
  failed_scans: number
  cancelled_scans: number
  total_vulnerabilities: number
  critical_vulnerabilities: number
  high_vulnerabilities: number
  medium_vulnerabilities: number
  low_vulnerabilities: number
  info_vulnerabilities: number
  repository_scans: number
  container_scans: number
  infrastructure_scans: number
  web_application_scans: number
  average_scan_duration: number
  longest_scan_duration: number
  shortest_scan_duration: number
}

const STATS_API = '/api/v1/scans/statistics'

function formatDuration(seconds: number): string {
  if (seconds <= 0 || !Number.isFinite(seconds)) return '—'
  if (seconds < 60) return `${Math.round(seconds)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return s ? `${m}m ${s}s` : `${m}m`
}

export default function StatisticsPage() {
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchStatistics = async () => {
      try {
        const response = await apiFetch(STATS_API)
        if (response.status === 404) {
          // No stats yet (e.g. route not mounted or no data) — show empty state, not error
          setStatistics(null)
          setError(null)
          return
        }
        if (!response.ok) {
          throw new Error('Failed to fetch statistics')
        }
        const data = await response.json()
        setStatistics(data)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    fetchStatistics()
  }, [])

  const severityEntries = statistics
    ? [
        { label: 'Critical', value: statistics.critical_vulnerabilities, key: 'critical' },
        { label: 'High', value: statistics.high_vulnerabilities, key: 'high' },
        { label: 'Medium', value: statistics.medium_vulnerabilities, key: 'medium' },
        { label: 'Low', value: statistics.low_vulnerabilities, key: 'low' },
        { label: 'Info', value: statistics.info_vulnerabilities, key: 'info' },
      ]
    : []

  const getSeverityColor = (key: string) => {
    switch (key) {
      case 'critical': return 'var(--color-critical)'
      case 'high': return 'var(--color-high)'
      case 'medium': return 'var(--color-medium)'
      case 'low': return 'var(--color-low)'
      default: return 'var(--color-info)'
    }
  }

  return (
    <div className="container statistics-page">
      <div className="card statistics-card">
        <header className="statistics-header">
          <h2>Statistics</h2>
          <p className="statistics-subtitle">
            Aggregated statistics from all scans
          </p>
        </header>

        {error && (
          <div className="statistics-error">
            {error}
          </div>
        )}

        {loading ? (
          <div className="statistics-loading">
            Loading statistics…
          </div>
        ) : statistics ? (
          <>
            {/* Overview: scans & findings */}
            <section className="statistics-section">
              <h3 className="statistics-section-title">Overview</h3>
              <div className="statistics-grid statistics-grid--overview">
                <div className="stat-card stat-card--primary">
                  <span className="stat-value">{statistics.total_scans}</span>
                  <span className="stat-label">Total Scans</span>
                </div>
                <div className="stat-card stat-card--danger">
                  <span className="stat-value">{statistics.total_vulnerabilities}</span>
                  <span className="stat-label">Total Findings</span>
                </div>
                <div className="stat-card stat-card--success">
                  <span className="stat-value">{statistics.completed_scans}</span>
                  <span className="stat-label">Completed</span>
                </div>
                <div className="stat-card stat-card--neutral">
                  <span className="stat-value">{statistics.pending_scans + statistics.running_scans}</span>
                  <span className="stat-label">Pending / Running</span>
                </div>
              </div>
            </section>

            {/* Findings by severity */}
            <section className="statistics-section">
              <h3 className="statistics-section-title">Findings by Severity</h3>
              <div className="statistics-grid statistics-grid--severity">
                {severityEntries.map(({ label, value, key }) => (
                  <div
                    key={key}
                    className="stat-card stat-card--severity"
                    style={{
                      ['--severity-color' as string]: getSeverityColor(key),
                    }}
                  >
                    <span className="stat-value">{value}</span>
                    <span className="stat-label">{label}</span>
                  </div>
                ))}
              </div>
            </section>

            {/* Scan types */}
            <section className="statistics-section">
              <h3 className="statistics-section-title">Scans by Type</h3>
              <div className="statistics-grid statistics-grid--types">
                <div className="stat-card stat-card--type">
                  <span className="stat-value">{statistics.repository_scans}</span>
                  <span className="stat-label">Repository</span>
                </div>
                <div className="stat-card stat-card--type">
                  <span className="stat-value">{statistics.container_scans}</span>
                  <span className="stat-label">Container</span>
                </div>
                <div className="stat-card stat-card--type">
                  <span className="stat-value">{statistics.infrastructure_scans}</span>
                  <span className="stat-label">Infrastructure</span>
                </div>
                <div className="stat-card stat-card--type">
                  <span className="stat-value">{statistics.web_application_scans}</span>
                  <span className="stat-label">Web App</span>
                </div>
              </div>
            </section>

            {/* Duration */}
            <section className="statistics-section">
              <h3 className="statistics-section-title">Scan Duration</h3>
              <div className="statistics-grid statistics-grid--duration">
                <div className="stat-card stat-card--neutral">
                  <span className="stat-value">{formatDuration(statistics.average_scan_duration)}</span>
                  <span className="stat-label">Average</span>
                </div>
                <div className="stat-card stat-card--neutral">
                  <span className="stat-value">{formatDuration(statistics.shortest_scan_duration)}</span>
                  <span className="stat-label">Shortest</span>
                </div>
                <div className="stat-card stat-card--neutral">
                  <span className="stat-value">{formatDuration(statistics.longest_scan_duration)}</span>
                  <span className="stat-label">Longest</span>
                </div>
              </div>
            </section>

            <p className="statistics-note">
              Counts reflect scans and findings stored in the system. Failed/cancelled scans are included in totals.
            </p>
          </>
        ) : (
          <div className="statistics-empty">
            No statistics available yet. Run some scans to see data here.
          </div>
        )}
      </div>
    </div>
  )
}
