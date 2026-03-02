import { useState, useEffect } from 'react'
import { useConfig } from '../hooks/useConfig'

interface Statistics {
  total_scans: number
  total_findings: number
  findings_by_severity: {
    critical: number
    high: number
    medium: number
    low: number
    info: number
  }
  findings_by_tool: Record<string, number>
  false_positive_count: number
}

export default function StatisticsPage() {
  const { config } = useConfig()
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchStatistics = async () => {
      if (!config?.is_production) {
        setLoading(false)
        return
      }

      try {
        const response = await fetch('/api/statistics')
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
  }, [config?.is_production])

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return '#dc3545' // Red
      case 'high':
        return '#fd7e14' // Orange
      case 'medium':
        return '#ffc107' // Yellow
      case 'low':
        return '#17a2b8' // Cyan
      case 'info':
        return '#6c757d' // Gray
      default:
        return '#6c757d'
    }
  }

  if (!config?.is_production) {
    return (
      <div className="container">
        <div className="card">
          <h2>Statistics</h2>
          <p style={{ color: '#6c757d' }}>
            Statistics are only available in Production Mode.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="container">
      <div className="card">
        <h2>Statistics</h2>
        <p style={{ marginTop: '0.5rem', opacity: 0.8, fontSize: '0.9rem', marginBottom: '2rem' }}>
          Aggregated statistics from all scans
        </p>

        {error && (
          <div style={{
            background: 'rgba(220, 53, 69, 0.2)',
            border: '1px solid #dc3545',
            borderRadius: '8px',
            padding: '1rem',
            marginBottom: '1rem',
            color: '#dc3545'
          }}>
            {error}
          </div>
        )}

        {loading ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#6c757d' }}>
            Loading statistics...
          </div>
        ) : statistics ? (
          <>
            {/* Overview Cards */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '1rem',
              marginBottom: '2rem'
            }}>
              <div style={{
                padding: '1.5rem',
                background: 'rgba(0, 123, 255, 0.1)',
                borderRadius: '8px',
                border: '1px solid rgba(0, 123, 255, 0.3)'
              }}>
                <div style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--primary)' }}>
                  {statistics.total_scans}
                </div>
                <div style={{ color: '#6c757d', fontSize: '0.9rem', marginTop: '0.5rem' }}>
                  Total Scans
                </div>
              </div>
              <div style={{
                padding: '1.5rem',
                background: 'rgba(220, 53, 69, 0.1)',
                borderRadius: '8px',
                border: '1px solid rgba(220, 53, 69, 0.3)'
              }}>
                <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#dc3545' }}>
                  {statistics.total_findings}
                </div>
                <div style={{ color: '#6c757d', fontSize: '0.9rem', marginTop: '0.5rem' }}>
                  Total Findings
                </div>
              </div>
              <div style={{
                padding: '1.5rem',
                background: 'rgba(255, 193, 7, 0.1)',
                borderRadius: '8px',
                border: '1px solid rgba(255, 193, 7, 0.3)'
              }}>
                <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#ffc107' }}>
                  {statistics.false_positive_count}
                </div>
                <div style={{ color: '#6c757d', fontSize: '0.9rem', marginTop: '0.5rem' }}>
                  False Positives
                </div>
              </div>
            </div>

            {/* Findings by Severity */}
            <div style={{ marginBottom: '2rem' }}>
              <h3 style={{ marginBottom: '1rem' }}>Findings by Severity</h3>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
                gap: '1rem'
              }}>
                {Object.entries(statistics.findings_by_severity).map(([severity, count]) => (
                  <div
                    key={severity}
                    style={{
                      padding: '1rem',
                      background: getSeverityColor(severity) + '20',
                      borderRadius: '8px',
                      border: `1px solid ${getSeverityColor(severity)}`
                    }}
                  >
                    <div style={{
                      fontSize: '1.5rem',
                      fontWeight: 'bold',
                      color: getSeverityColor(severity),
                      textTransform: 'capitalize'
                    }}>
                      {count}
                    </div>
                    <div style={{ color: '#6c757d', fontSize: '0.9rem', marginTop: '0.25rem', textTransform: 'capitalize' }}>
                      {severity}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Findings by Tool */}
            {Object.keys(statistics.findings_by_tool).length > 0 && (
              <div style={{ marginBottom: '2rem' }}>
                <h3 style={{ marginBottom: '1rem' }}>Findings by Tool</h3>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ borderBottom: '2px solid #e9ecef' }}>
                        <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 'bold' }}>Tool</th>
                        <th style={{ padding: '0.75rem', textAlign: 'right', fontWeight: 'bold' }}>Findings</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(statistics.findings_by_tool)
                        .sort(([, a], [, b]) => b - a)
                        .map(([tool, count]) => (
                          <tr key={tool} style={{ borderBottom: '1px solid #e9ecef' }}>
                            <td style={{ padding: '0.75rem', fontFamily: 'monospace', fontSize: '0.9rem' }}>
                              {tool}
                            </td>
                            <td style={{ padding: '0.75rem', textAlign: 'right', fontWeight: 'bold' }}>
                              {count}
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Note about false positives */}
            <div style={{
              marginTop: '2rem',
              padding: '1rem',
              background: 'rgba(255, 193, 7, 0.1)',
              borderRadius: '8px',
              border: '1px solid rgba(255, 193, 7, 0.3)',
              fontSize: '0.875rem',
              color: '#856404'
            }}>
              <strong>Note:</strong> These statistics include all findings, including false positives. 
              The false positive count represents findings that have been manually marked as false positives.
            </div>
          </>
        ) : (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#6c757d' }}>
            No statistics available yet.
          </div>
        )}
      </div>
    </div>
  )
}
