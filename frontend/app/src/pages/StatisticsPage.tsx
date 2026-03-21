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
  distinct_targets_scanned: number
  distinct_repositories_scanned: number
  distinct_repo_owners_scanned: number
  average_scan_duration: number
  longest_scan_duration: number
  shortest_scan_duration: number
  scanner_duration_stats?: Array<{
    scanner_name: string
    avg_duration_seconds: number
    min_duration_seconds: number | null
    max_duration_seconds: number | null
    sample_count: number
    last_updated: string | null
  }>
  daily_scan_counts?: Array<{
    date: string
    total_scans: number
    repository_scans: number
    container_scans: number
    infrastructure_scans: number
    web_application_scans: number
  }>
}

const STATS_API = '/api/v1/scans/statistics'
type ChartMode = 'all' | 'repository' | 'container' | 'infrastructure' | 'web'
type ChartView = 'cumulative' | 'period'
type ChartPoint = { date: string, value: number }

interface DailySeriesPoint {
  date: string
  total_scans: number
  repository_scans: number
  container_scans: number
  infrastructure_scans: number
  web_application_scans: number
}

type ChartGranularity = 'day' | 'week' | 'month'

function isoDayUTC(d: Date): string {
  const y = d.getUTCFullYear()
  const m = String(d.getUTCMonth() + 1).padStart(2, '0')
  const day = String(d.getUTCDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function parseIsoDayUTC(day: string): Date {
  return new Date(`${day}T00:00:00Z`)
}

function weekStartIsoUTC(day: string): string {
  const d = parseIsoDayUTC(day)
  const dayOfWeek = d.getUTCDay() // 0=Sun, 1=Mon, ...
  const shift = dayOfWeek === 0 ? 6 : dayOfWeek - 1
  d.setUTCDate(d.getUTCDate() - shift)
  return isoDayUTC(d)
}

function monthKeyUTC(day: string): string {
  return day.slice(0, 7)
}

function densifyDailySeries(raw: DailySeriesPoint[]): DailySeriesPoint[] {
  if (!raw.length) return []

  const byDate = new Map(raw.map((r) => [r.date, r]))
  const sorted = [...raw].sort((a, b) => a.date.localeCompare(b.date))
  const first = parseIsoDayUTC(sorted[0].date)
  const now = new Date()
  const today = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()))
  const out: DailySeriesPoint[] = []

  for (let d = new Date(first); d <= today; d.setUTCDate(d.getUTCDate() + 1)) {
    const date = isoDayUTC(d)
    const existing = byDate.get(date)
    out.push(existing ?? {
      date,
      total_scans: 0,
      repository_scans: 0,
      container_scans: 0,
      infrastructure_scans: 0,
      web_application_scans: 0,
    })
  }

  return out
}

function aggregateSeries(points: DailySeriesPoint[]): { granularity: ChartGranularity, data: DailySeriesPoint[] } {
  if (!points.length) return { granularity: 'day', data: [] }

  if (points.length <= 120) {
    return { granularity: 'day', data: points }
  }

  if (points.length <= 540) {
    const weekly = new Map<string, DailySeriesPoint>()
    points.forEach((p) => {
      const key = weekStartIsoUTC(p.date)
      const prev = weekly.get(key)
      if (prev) {
        prev.total_scans += p.total_scans
        prev.repository_scans += p.repository_scans
        prev.container_scans += p.container_scans
        prev.infrastructure_scans += p.infrastructure_scans
        prev.web_application_scans += p.web_application_scans
      } else {
        weekly.set(key, { ...p, date: key })
      }
    })
    return {
      granularity: 'week',
      data: [...weekly.values()].sort((a, b) => a.date.localeCompare(b.date)),
    }
  }

  const monthly = new Map<string, DailySeriesPoint>()
  points.forEach((p) => {
    const key = monthKeyUTC(p.date)
    const prev = monthly.get(key)
    if (prev) {
      prev.total_scans += p.total_scans
      prev.repository_scans += p.repository_scans
      prev.container_scans += p.container_scans
      prev.infrastructure_scans += p.infrastructure_scans
      prev.web_application_scans += p.web_application_scans
    } else {
      monthly.set(key, { ...p, date: key })
    }
  })
  return {
    granularity: 'month',
    data: [...monthly.values()].sort((a, b) => a.date.localeCompare(b.date)),
  }
}

function formatDuration(seconds: number): string {
  if (seconds <= 0 || !Number.isFinite(seconds)) return '—'
  if (seconds < 60) return `${Math.round(seconds)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return s ? `${m}m ${s}s` : `${m}m`
}

function formatCountCompact(value: number): string {
  if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k`
  return String(value)
}

function formatDateLabel(date: string, granularity: ChartGranularity): string {
  if (granularity === 'month') return date
  return date.slice(0, 7)
}

export default function StatisticsPage() {
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [chartMode, setChartMode] = useState<ChartMode>('all')
  const [chartView, setChartView] = useState<ChartView>('cumulative')

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

  const denseDailySeries = densifyDailySeries(statistics?.daily_scan_counts ?? [])
  const { granularity, data: displaySeries } = aggregateSeries(denseDailySeries)
  const baseChartPoints = displaySeries.map((d) => {
    let value = d.total_scans
    if (chartMode === 'repository') value = d.repository_scans
    else if (chartMode === 'container') value = d.container_scans
    else if (chartMode === 'infrastructure') value = d.infrastructure_scans
    else if (chartMode === 'web') value = d.web_application_scans
    return { date: d.date, value }
  })
  const chartPoints: ChartPoint[] = chartView === 'cumulative'
    ? baseChartPoints.reduce<ChartPoint[]>((acc, point) => {
        const prev = acc.length > 0 ? acc[acc.length - 1].value : 0
        acc.push({ date: point.date, value: prev + point.value })
        return acc
      }, [])
    : baseChartPoints
  const renderPoints: ChartPoint[] = (
    chartView === 'cumulative' && chartPoints.length > 0
      ? [{ date: chartPoints[0].date, value: 0 }, ...chartPoints]
      : chartPoints
  )
  const chartMax = Math.max(1, chartPoints.reduce((max, point) => Math.max(max, point.value), 0))
  const currentCount = chartPoints[chartPoints.length - 1]?.value ?? 0

  const chartLabel = (() => {
    switch (chartMode) {
      case 'repository': return 'Repository scan-runs'
      case 'container': return 'Container scan-runs'
      case 'infrastructure': return 'Infrastructure scan-runs'
      case 'web': return 'Web scan-runs'
      default: return 'All scan-runs'
    }
  })()
  const periodLabel = granularity === 'day' ? 'daily' : (granularity === 'week' ? 'weekly' : 'monthly')
  const viewLabel = chartView === 'cumulative' ? 'cumulative' : 'per period'

  const svgWidth = 900
  const svgHeight = 280
  const paddingLeft = 56
  const paddingRight = 16
  const paddingTop = 16
  const paddingBottom = 34
  const innerWidth = svgWidth - paddingLeft - paddingRight
  const innerHeight = svgHeight - paddingTop - paddingBottom
  const stepX = renderPoints.length > 1 ? innerWidth / (renderPoints.length - 1) : 0
  const toX = (index: number) => (
    renderPoints.length === 1
      ? paddingLeft + innerWidth / 2
      : paddingLeft + (stepX * index)
  )
  const toY = (value: number) => paddingTop + innerHeight - (value / chartMax) * innerHeight

  const linePoints = renderPoints.map((point, index) => `${toX(index)},${toY(point.value)}`).join(' ')
  const areaPath = renderPoints.length > 0
    ? `M ${toX(0)} ${paddingTop + innerHeight} L ${linePoints} L ${toX(renderPoints.length - 1)} ${paddingTop + innerHeight} Z`
    : ''
  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((ratio) => ({
    y: paddingTop + innerHeight - (ratio * innerHeight),
    value: Math.round(chartMax * ratio),
  }))
  const xTickCount = Math.min(6, Math.max(2, chartPoints.length))
  const xTickIndices = Array.from({ length: xTickCount }, (_, i) => {
    if (xTickCount === 1) return 0
    return Math.round((i / (xTickCount - 1)) * (chartPoints.length - 1))
  })

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
                <div className="stat-card stat-card--neutral">
                  <span className="stat-value">{statistics.cancelled_scans}</span>
                  <span className="stat-label">Cancelled</span>
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

            {/* Coverage */}
            <section className="statistics-section">
              <h3 className="statistics-section-title">Coverage</h3>
              <div className="statistics-grid statistics-grid--overview">
                <div className="stat-card stat-card--neutral">
                  <span className="stat-value">{statistics.distinct_targets_scanned}</span>
                  <span className="stat-label">Distinct Targets</span>
                </div>
                <div className="stat-card stat-card--neutral">
                  <span className="stat-value">{statistics.distinct_repositories_scanned}</span>
                  <span className="stat-label">Distinct Repositories</span>
                </div>
                <div className="stat-card stat-card--neutral">
                  <span className="stat-value">{statistics.distinct_repo_owners_scanned}</span>
                  <span className="stat-label">Distinct Repo Owners / Orgs</span>
                </div>
              </div>
            </section>

            {/* Daily trend */}
            <section className="statistics-section">
              <h3 className="statistics-section-title">Trend Since Start</h3>
              <div className="statistics-chart-toolbar">
                <button
                  type="button"
                  className={`statistics-chip ${chartMode === 'all' ? 'statistics-chip--active' : ''}`}
                  onClick={() => setChartMode('all')}
                >
                  All
                </button>
                <button
                  type="button"
                  className={`statistics-chip ${chartMode === 'repository' ? 'statistics-chip--active' : ''}`}
                  onClick={() => setChartMode('repository')}
                >
                  Repo
                </button>
                <button
                  type="button"
                  className={`statistics-chip ${chartMode === 'container' ? 'statistics-chip--active' : ''}`}
                  onClick={() => setChartMode('container')}
                >
                  Container
                </button>
                <button
                  type="button"
                  className={`statistics-chip ${chartMode === 'infrastructure' ? 'statistics-chip--active' : ''}`}
                  onClick={() => setChartMode('infrastructure')}
                >
                  Infrastructure
                </button>
                <button
                  type="button"
                  className={`statistics-chip ${chartMode === 'web' ? 'statistics-chip--active' : ''}`}
                  onClick={() => setChartMode('web')}
                >
                  Web
                </button>
                <button
                  type="button"
                  className={`statistics-chip ${chartView === 'cumulative' ? 'statistics-chip--active' : ''}`}
                  onClick={() => setChartView('cumulative')}
                >
                  Cumulative
                </button>
                <button
                  type="button"
                  className={`statistics-chip ${chartView === 'period' ? 'statistics-chip--active' : ''}`}
                  onClick={() => setChartView('period')}
                >
                  Per Period
                </button>
              </div>

              {chartPoints.length > 0 ? (
                <div className="statistics-chart-card">
                  <div className="statistics-linechart" aria-label={chartLabel}>
                    <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} role="img" aria-label={chartLabel}>
                      {yTicks.map((tick) => (
                        <g key={tick.value}>
                          <line
                            x1={paddingLeft}
                            x2={paddingLeft + innerWidth}
                            y1={tick.y}
                            y2={tick.y}
                            className="statistics-linechart-grid"
                          />
                          <text
                            x={paddingLeft - 8}
                            y={tick.y + 4}
                            className="statistics-linechart-ylabel"
                            textAnchor="end"
                          >
                            {formatCountCompact(tick.value)}
                          </text>
                        </g>
                      ))}

                      <line
                        x1={paddingLeft}
                        x2={paddingLeft}
                        y1={paddingTop}
                        y2={paddingTop + innerHeight}
                        className="statistics-linechart-axis"
                      />
                      <line
                        x1={paddingLeft}
                        x2={paddingLeft + innerWidth}
                        y1={paddingTop + innerHeight}
                        y2={paddingTop + innerHeight}
                        className="statistics-linechart-axis"
                      />

                      {areaPath && <path d={areaPath} className="statistics-linechart-area" />}
                      {linePoints && <polyline points={linePoints} className="statistics-linechart-line" />}

                      {xTickIndices.map((index) => (
                        <text
                          key={`${index}-${chartPoints[index]?.date ?? 'x'}`}
                          x={toX(index)}
                          y={svgHeight - 8}
                          className="statistics-linechart-xlabel"
                          textAnchor="middle"
                        >
                          {formatDateLabel(chartPoints[index]?.date ?? '', granularity)}
                        </text>
                      ))}
                    </svg>
                  </div>
                  <p className="statistics-chart-caption">{chartLabel} ({periodLabel}, {viewLabel}) - Current: {currentCount}</p>
                </div>
              ) : (
                <div className="statistics-empty">No daily scan data yet.</div>
              )}
            </section>

            {/* Duration by tool (per-scanner) */}
            {statistics.scanner_duration_stats && statistics.scanner_duration_stats.length > 0 && (
              <section className="statistics-section">
                <h3 className="statistics-section-title">Duration by tool</h3>
                <div className="statistics-grid statistics-grid--duration">
                  {statistics.scanner_duration_stats.map((s) => (
                    <div key={s.scanner_name} className="stat-card stat-card--neutral">
                      <span className="stat-value">{formatDuration(s.avg_duration_seconds)}</span>
                      <span className="stat-label">{s.scanner_name}</span>
                      {(s.min_duration_seconds != null || s.max_duration_seconds != null) && (
                        <span className="stat-sublabel" style={{ fontSize: '0.8rem', opacity: 0.8 }}>
                          {s.min_duration_seconds != null && formatDuration(s.min_duration_seconds)}
                          {s.min_duration_seconds != null && s.max_duration_seconds != null && ' – '}
                          {s.max_duration_seconds != null && formatDuration(s.max_duration_seconds)}
                          {s.sample_count > 0 && ` (${s.sample_count} runs)`}
                        </span>
                      )}
                      {s.min_duration_seconds == null && s.max_duration_seconds == null && s.sample_count > 0 && (
                        <span className="stat-sublabel" style={{ fontSize: '0.8rem', opacity: 0.8 }}>
                          {s.sample_count} runs
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Duration (whole-scan aggregates; optional) */}
            <section className="statistics-section">
              <h3 className="statistics-section-title">Scan duration (all scans)</h3>
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
