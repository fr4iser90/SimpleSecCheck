import { useEffect, useState } from 'react'
import { resolveApiUrl } from '../utils/resolveApiUrl'

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
    fetch(resolveApiUrl('/api/results'))
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

  const openReport = (scanId: string) => {
    window.location.href = resolveApiUrl(`/api/results/${scanId}/report`)
  }

  return (
    <div className="container">
      <div className="card">
        <h2>Browse Results</h2>
        <p style={{ marginBottom: '2rem', opacity: 0.8 }}>
          These are local files from the results/ directory. Click on a scan to view its report.
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
                  background: 'var(--glass-bg-main)',
                  border: '1px solid var(--glass-border-main)',
                  borderRadius: '8px',
                  padding: '1rem',
                  marginBottom: '1rem',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  cursor: scan.has_report ? 'pointer' : 'default',
                  transition: 'all 0.2s ease',
                  ...(scan.has_report && {
                    ':hover': {
                      background: 'var(--glass-bg-light)',
                      borderColor: '#007bff',
                    }
                  })
                }}
                onClick={() => {
                  if (scan.has_report && scan.report_path) {
                    openReport(scan.id)
                  }
                }}
                onMouseEnter={(e) => {
                  if (scan.has_report) {
                    e.currentTarget.style.background = 'var(--glass-bg-light)'
                    e.currentTarget.style.borderColor = '#007bff'
                  }
                }}
                onMouseLeave={(e) => {
                  if (scan.has_report) {
                    e.currentTarget.style.background = 'var(--glass-bg-main)'
                    e.currentTarget.style.borderColor = 'var(--glass-border-main)'
                  }
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
                  <button 
                    onClick={(e) => {
                      e.stopPropagation()
                      openReport(scan.id)
                    }}
                    style={{
                      padding: '0.5rem 1rem',
                      background: '#007bff',
                      color: 'white',
                      border: 'none',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontWeight: 500,
                    }}
                  >
                    📄 View Report
                  </button>
                )}
                {!scan.has_report && (
                  <span style={{ opacity: 0.5, fontSize: '0.875rem' }}>
                    No report available
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
