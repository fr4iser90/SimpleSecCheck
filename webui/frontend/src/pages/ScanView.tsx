import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ScanStatus from '../components/ScanStatus'
import LiveLogs from '../components/LiveLogs'
import ReportViewer from '../components/ReportViewer'

interface ScanStatusData {
  status: 'idle' | 'running' | 'done' | 'error'
  scan_id: string | null
  results_dir: string | null
  started_at: string | null
  error_code?: number | null
  error_message?: string | null
}

export default function ScanView() {
  const navigate = useNavigate()
  const [status, setStatus] = useState<ScanStatusData>({
    status: 'idle',
    scan_id: null,
    results_dir: null,
    started_at: null,
  })

  useEffect(() => {
    // Poll scan status
    const interval = setInterval(async () => {
      try {
        const response = await fetch('/api/scan/status')
        if (response.ok) {
          const data = await response.json()
          setStatus(data)
        }
      } catch (err) {
        console.error('Failed to fetch scan status:', err)
      }
    }, 2000) // Poll every 2 seconds

    return () => clearInterval(interval)
  }, [])

  const handleNewScan = () => {
    navigate('/')
  }

  return (
    <div className="container">
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2>Scan Status</h2>
          <button onClick={handleNewScan}>Start New Scan</button>
        </div>
        <ScanStatus status={status} />
      </div>

      {(status.status === 'running' || (status.status === 'done' && !status.results_dir)) && (
        <div className="card">
          <h2>Live Logs</h2>
          <LiveLogs />
        </div>
      )}

      {status.status === 'done' && status.results_dir && (
        <>
          <div className="card">
            <h2>Security Report</h2>
            <ReportViewer />
          </div>
          <div className="card">
            <h2>Scan Logs</h2>
            <LiveLogs />
          </div>
        </>
      )}

      {status.status === 'error' && (
        <div className="card">
          <div style={{ 
            background: 'rgba(220, 53, 69, 0.2)', 
            border: '1px solid #dc3545', 
            borderRadius: '8px', 
            padding: '1rem',
            color: '#dc3545'
          }}>
            <strong>❌ Scan failed</strong>
            {status.error_message && (
              <div style={{ 
                marginTop: '0.75rem', 
                padding: '0.75rem', 
                background: 'rgba(0, 0, 0, 0.1)', 
                borderRadius: '4px',
                fontFamily: 'monospace',
                fontSize: '0.9rem',
                wordBreak: 'break-word',
                whiteSpace: 'pre-wrap',  // Preserve line breaks
                maxHeight: '300px',
                overflowY: 'auto'
              }}>
                {status.error_message}
              </div>
            )}
            {status.error_code && (
              <div style={{ marginTop: '0.5rem', fontSize: '0.9rem', opacity: 0.8 }}>
                Exit code: {status.error_code}
              </div>
            )}
            {!status.error_message && (
              <div style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>
                Check the logs below or the Docker container logs for details.
                {status.results_dir && (
                  <div style={{ marginTop: '0.5rem' }}>
                    Logs may be available in: {status.results_dir}/logs/
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
