import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import ReportViewer from '../components/ReportViewer'
import LiveLogs from '../components/LiveLogs'
import StepsSidebar from '../components/StepsSidebar'
import AIPromptModal from '../components/AIPromptModal'

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

  const [isStepsSidebarOpen, setIsStepsSidebarOpen] = useState(false)
  const [isLogsSidebarOpen, setIsLogsSidebarOpen] = useState(false)
  const [isAIPromptModalOpen, setIsAIPromptModalOpen] = useState(false)

  // Listen for messages from iframe (HTML Report)
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      // Security: Only accept messages from same origin
      if (event.origin !== window.location.origin && !event.origin.includes('localhost:8080')) {
        return
      }
      
      if (event.data && event.data.type === 'OPEN_AI_PROMPT_MODAL') {
        setIsAIPromptModalOpen(true)
      }
    }

    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [])

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

  // Show loading/running state
  if (status.status === 'running' || (status.status === 'done' && !status.results_dir)) {
    return (
      <div style={{ 
        height: 'calc(100vh - 80px)', // Full height minus header
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '2rem',
        padding: '2rem',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>⏳</div>
          <h2>Scan in Progress...</h2>
          <p style={{ opacity: 0.7, marginTop: '0.5rem' }}>
            Scan ID: {status.scan_id}
          </p>
        </div>
        <div style={{ 
          width: '100%', 
          maxWidth: '800px',
          background: 'var(--glass-bg-dark)',
          border: '1px solid var(--glass-border-dark)',
          borderRadius: '8px',
          padding: '1.5rem',
        }}>
          <LiveLogs />
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button
            onClick={() => setIsStepsSidebarOpen(true)}
            style={{
              padding: '0.75rem 1.5rem',
              background: 'var(--glass-bg-dark)',
              border: '1px solid var(--glass-border-dark)',
              borderRadius: '8px',
              color: 'var(--text-dark)',
              cursor: 'pointer',
            }}
          >
            📋 View Steps
          </button>
        </div>
      </div>
    )
  }

  // Show error state
  if (status.status === 'error') {
    return (
      <div style={{ 
        height: 'calc(100vh - 80px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem',
      }}>
        <div style={{
          maxWidth: '800px',
          width: '100%',
          background: 'rgba(220, 53, 69, 0.2)',
          border: '1px solid #dc3545',
          borderRadius: '8px',
          padding: '2rem',
          color: '#dc3545',
        }}>
          <strong style={{ fontSize: '1.5rem' }}>❌ Scan failed</strong>
          {status.error_message && (
            <div style={{ 
              marginTop: '1rem', 
              padding: '1rem', 
              background: 'rgba(0, 0, 0, 0.2)', 
              borderRadius: '4px',
              fontFamily: 'monospace',
              fontSize: '0.9rem',
              wordBreak: 'break-word',
              whiteSpace: 'pre-wrap',
              maxHeight: '400px',
              overflowY: 'auto'
            }}>
              {status.error_message}
            </div>
          )}
          {status.error_code && (
            <div style={{ marginTop: '1rem', fontSize: '0.9rem', opacity: 0.8 }}>
              Exit code: {status.error_code}
            </div>
          )}
          <button
            onClick={() => navigate('/')}
            style={{
              marginTop: '1.5rem',
              padding: '0.75rem 1.5rem',
              background: '#dc3545',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 'bold',
            }}
          >
            Start New Scan
          </button>
        </div>
      </div>
    )
  }

  // Show full-page report when scan is done
  if (status.status === 'done' && status.results_dir) {
    return (
      <div style={{ 
        height: 'calc(100vh - 80px)', // Full height minus header
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
      }}>
        {/* Full-Page Report */}
        <div style={{ 
          flex: 1,
          overflow: 'hidden',
          position: 'relative',
        }}>
          <ReportViewer />
        </div>

        {/* Floating Action Buttons */}
        <div style={{
          position: 'fixed',
          bottom: '2rem',
          right: '2rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
          zIndex: 100,
        }}>
          <button
            onClick={() => setIsStepsSidebarOpen(true)}
            style={{
              padding: '1rem',
              background: 'var(--glass-bg-dark)',
              backdropFilter: 'blur(10px)',
              border: '1px solid var(--glass-border-dark)',
              borderRadius: '50%',
              width: '56px',
              height: '56px',
              color: 'var(--text-dark)',
              cursor: 'pointer',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
              fontSize: '1.5rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            title="View Steps"
          >
            📋
          </button>
          <button
            onClick={() => setIsLogsSidebarOpen(true)}
            style={{
              padding: '1rem',
              background: 'var(--glass-bg-dark)',
              backdropFilter: 'blur(10px)',
              border: '1px solid var(--glass-border-dark)',
              borderRadius: '50%',
              width: '56px',
              height: '56px',
              color: 'var(--text-dark)',
              cursor: 'pointer',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
              fontSize: '1.5rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            title="View Logs"
          >
            📄
          </button>
        </div>

        {/* Steps Sidebar */}
        <StepsSidebar
          isOpen={isStepsSidebarOpen}
          onClose={() => setIsStepsSidebarOpen(false)}
        />

        {/* Logs Sidebar */}
        {isLogsSidebarOpen && (
          <>
            <div
              style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'rgba(0, 0, 0, 0.5)',
                zIndex: 999,
              }}
              onClick={() => setIsLogsSidebarOpen(false)}
            />
            <div
              style={{
                position: 'fixed',
                top: 0,
                right: 0,
                bottom: 0,
                width: '500px',
                maxWidth: '90vw',
                background: 'var(--glass-bg-dark)',
                backdropFilter: 'blur(20px)',
                borderLeft: '1px solid var(--glass-border-dark)',
                boxShadow: '-4px 0 20px rgba(0, 0, 0, 0.3)',
                zIndex: 1000,
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  padding: '1.5rem',
                  borderBottom: '1px solid var(--glass-border-dark)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <h2 style={{ margin: 0, fontSize: '1.25rem' }}>📄 Scan Logs</h2>
                <button
                  onClick={() => setIsLogsSidebarOpen(false)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    fontSize: '1.5rem',
                    cursor: 'pointer',
                    color: 'var(--text-dark)',
                    padding: '0.25rem 0.5rem',
                    lineHeight: 1,
                  }}
                  title="Close"
                >
                  ✕
                </button>
              </div>
              <div
                style={{
                  flex: 1,
                  overflow: 'auto',
                  padding: '1.5rem',
                }}
              >
                <LiveLogs />
              </div>
            </div>
          </>
        )}

        {/* AI Prompt Modal */}
        <AIPromptModal
          isOpen={isAIPromptModalOpen}
          onClose={() => setIsAIPromptModalOpen(false)}
        />
      </div>
    )
  }

  // Default: No scan
  return (
    <div style={{ 
      height: 'calc(100vh - 80px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }}>
      <div style={{ textAlign: 'center' }}>
        <h2>No active scan</h2>
        <button
          onClick={() => navigate('/')}
          style={{
            marginTop: '1rem',
            padding: '0.75rem 1.5rem',
            background: 'var(--glass-bg-dark)',
            border: '1px solid var(--glass-border-dark)',
            borderRadius: '8px',
            color: 'var(--text-dark)',
            cursor: 'pointer',
          }}
        >
          Start New Scan
        </button>
      </div>
    </div>
  )
}
