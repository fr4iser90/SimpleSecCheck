import { useEffect, useState } from 'react'

interface Scan {
  id: string
  timestamp: string
  has_report: boolean
  report_path: string | null
}

export default function ResultsBrowser() {
  const [scans, setScans] = useState<Scan[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/results')
      .then((response) => response.json())
      .then((data) => {
        setScans(data.scans || [])
        setLoading(false)
      })
      .catch((err) => {
        console.error('Failed to fetch results:', err)
        setLoading(false)
      })
  }, [])

  const openReport = (reportPath: string) => {
    window.open(reportPath, '_blank')
  }

  return (
    <div className="container">
      <div className="card">
        <h2>Browse Results</h2>
        <p style={{ marginBottom: '2rem', opacity: 0.8 }}>
          These are local files from the results/ directory. No database, no tracking - just file browser.
        </p>

        {loading ? (
          <div style={{ opacity: 0.7 }}>Loading...</div>
        ) : scans.length === 0 ? (
          <div style={{ opacity: 0.7 }}>No scan results found.</div>
        ) : (
          <div>
            {scans.map((scan) => (
              <div
                key={scan.id}
                style={{
                  background: 'var(--glass-bg-dark)',
                  border: '1px solid var(--glass-border-dark)',
                  borderRadius: '8px',
                  padding: '1rem',
                  marginBottom: '1rem',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>
                    {scan.id}
                  </div>
                  <div style={{ fontSize: '0.875rem', opacity: 0.7 }}>
                    {scan.timestamp}
                  </div>
                </div>
                {scan.has_report && scan.report_path && (
                  <button onClick={() => openReport(scan.report_path!)}>
                    📄 View Report
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
