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

  // AI Prompt state
  const [aiPromptCopied, setAiPromptCopied] = useState(false)
  const [tokenSaving, setTokenSaving] = useState(false)
  const [policyPath, setPolicyPath] = useState("config/finding-policy.json")
  const [customPolicyPath, setCustomPolicyPath] = useState("")
  const [useCustomPath, setUseCustomPath] = useState(false)

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

  const handleCopyAIPrompt = async () => {
    try {
      const finalPolicyPath = useCustomPath ? customPolicyPath : policyPath
      const response = await fetch(
        `/api/scan/ai-prompt?token_saving=${tokenSaving}&policy_path=${encodeURIComponent(finalPolicyPath)}`
      )
      if (response.ok) {
        const data = await response.json()
        await navigator.clipboard.writeText(data.prompt)
        setAiPromptCopied(true)
        setTimeout(() => setAiPromptCopied(false), 3000)
      } else {
        alert('Failed to generate AI prompt')
      }
    } catch (error) {
      console.error('Error copying AI prompt:', error)
      alert('Failed to copy AI prompt')
    }
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
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div>
                <h2 style={{ margin: 0 }}>✅ Scan Completed</h2>
                <p style={{ margin: '0.5rem 0 0 0' }}>Scan ID: {status.scan_id}</p>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={tokenSaving}
                    onChange={(e) => setTokenSaving(e.target.checked)}
                    style={{ cursor: 'pointer' }}
                  />
                  <span>Token Saving (中文)</span>
                </label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                    <span>Policy:</span>
                    {!useCustomPath ? (
                      <>
                        <select
                          value={policyPath}
                          onChange={(e) => {
                            if (e.target.value === "custom") {
                              setUseCustomPath(true)
                              setCustomPolicyPath("")
                            } else {
                              setPolicyPath(e.target.value)
                            }
                          }}
                          style={{
                            padding: '0.25rem 0.5rem',
                            borderRadius: '4px',
                            border: '1px solid #ccc',
                            fontSize: '0.9rem',
                            cursor: 'pointer'
                          }}
                        >
                          <option value="config/finding-policy.json">config/finding-policy.json</option>
                          <option value="config/policy/finding-policy.json">config/policy/finding-policy.json</option>
                          <option value="security/finding-policy.json">security/finding-policy.json</option>
                          <option value=".security/finding-policy.json">.security/finding-policy.json</option>
                          <option value="custom">Custom...</option>
                        </select>
                      </>
                    ) : (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        <input
                          type="text"
                          value={customPolicyPath}
                          onChange={(e) => setCustomPolicyPath(e.target.value)}
                          placeholder="e.g., config/my-policy.json"
                          style={{
                            padding: '0.25rem 0.5rem',
                            borderRadius: '4px',
                            border: '1px solid #ccc',
                            fontSize: '0.9rem',
                            width: '200px'
                          }}
                          onKeyDown={(e) => {
                            if (e.key === 'Escape') {
                              setUseCustomPath(false)
                              setCustomPolicyPath("")
                              setPolicyPath("config/finding-policy.json")
                            }
                          }}
                        />
                        <button
                          onClick={() => {
                            setUseCustomPath(false)
                            setCustomPolicyPath("")
                            setPolicyPath("config/finding-policy.json")
                          }}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            cursor: 'pointer',
                            fontSize: '1rem',
                            color: '#dc3545',
                            padding: '0',
                            lineHeight: '1'
                          }}
                          title="Reset to default"
                        >
                          ✕
                        </button>
                      </div>
                    )}
                  </label>
                </div>
                <button
                  onClick={handleCopyAIPrompt}
                  style={{
                    padding: '0.5rem 1rem',
                    background: aiPromptCopied ? '#28a745' : '#6c757d',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontWeight: 'bold',
                    transition: 'background 0.2s'
                  }}
                >
                  {aiPromptCopied ? '✓ Copied!' : '🤖 AI Prompt'}
                </button>
                {getResultLink() && (
                  <a 
                    href={getResultLink()} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    style={{
                      display: 'inline-block',
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
            </div>
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
