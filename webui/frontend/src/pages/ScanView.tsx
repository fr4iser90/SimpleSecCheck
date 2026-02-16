import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
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
  const location = useLocation()
  
  // Get initial status from navigation state (passed from ScanForm)
  const [status, setStatus] = useState<ScanStatusData>(
    location.state || {
      status: 'idle',
      scan_id: null,
      results_dir: null,
      started_at: null,
    }
  )

  // Poll status every 2 seconds if scan is running
  useEffect(() => {
    if (status.status === 'running' && status.scan_id) {
      const interval = setInterval(async () => {
        try {
          const response = await fetch('/api/scan/status')
          if (response.ok) {
            const newStatus = await response.json()
            setStatus(newStatus)
            // If scan is done, stop polling
            if (newStatus.status === 'done' || newStatus.status === 'error') {
              clearInterval(interval)
            }
          }
        } catch (error) {
          console.error('Failed to fetch scan status:', error)
        }
      }, 2000)
      
      return () => clearInterval(interval)
    }
  }, [status.status, status.scan_id])

  // Helper function to get result link
  const getResultLink = (): string | undefined => {
    if (status.status === 'done' && status.scan_id) {
      // Use the scan_id to construct the report link
      return `/api/results/${status.scan_id}/report`
    }
    return undefined
  }

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

      {(status.status === 'running' || (status.status === 'done' && !status.results_dir) || (status.scan_id && status.status === 'idle')) && (
        <div className="card">
          <h2>Live Logs</h2>
          <LiveLogs />
        </div>
      )}

      {status.status === 'done' && status.results_dir && (
        <>
          <div className="card">
            <h2>✅ Scan Completed</h2>
            <p>Scan ID: {status.scan_id}</p>
            {getResultLink() && (
              <a 
                href={getResultLink()} 
                target="_blank" 
                rel="noopener noreferrer"
                style={{
                  display: 'inline-block',
                  marginTop: '1rem',
                  padding: '0.75rem 1.5rem',
                  background: '#007bff',
                  color: 'white',
                  textDecoration: 'none',
                  borderRadius: '4px',
                  fontWeight: 'bold'
                }}
              >
                📊 View Results
              </a>
            )}
          </div>
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
