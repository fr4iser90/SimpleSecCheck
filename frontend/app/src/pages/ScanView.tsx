import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import ReportViewer from '../components/ReportViewer'
import StepsSidebar from '../components/StepsSidebar'
import AIPromptModal from '../components/AIPromptModal'
import { useWebSocket } from '../services/websocketService'

// Backend is the source of truth!
// Backend uses TWO status systems:
// 1. Queue system: 'pending', 'running', 'completed', 'failed'
// 2. Scan system: 'idle', 'running', 'done', 'error'
interface ScanStatusData {
  status: 'idle' | 'running' | 'done' | 'error' | 'pending' | 'completed' | 'failed'
  scan_id: string | null
  results_dir: string | null
  started_at: string | null
  error_code?: number | null
  error_message?: string | null
}

interface QueueStatus {
  queue_id: string
  repository_name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  position?: number
  created_at: string
  scan_id?: string
}

interface Step {
  number: number
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  message?: string
}

interface WebSocketMessage {
  type: string
  steps?: Step[]
  progress_percentage?: number
  total_steps?: number
  scan_id?: string
  timestamp?: number
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

  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null)
  const [steps, setSteps] = useState<Step[]>([])
  const [progress, setProgress] = useState<number>(0)
  const [isStepsSidebarOpen, setIsStepsSidebarOpen] = useState(false)
  const [isLogsSidebarOpen, setIsLogsSidebarOpen] = useState(false)
  const [isAIPromptModalOpen, setIsAIPromptModalOpen] = useState(false)

  // Check if scan_id is a queue_id (UUID format)
  const isQueueId = (id: string | null): boolean => {
    if (!id) return false
    // UUID format: 8-4-4-4-12 hex characters
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
    return uuidRegex.test(id)
  }

  // Poll queue status if scan_id is a queue_id (ALWAYS poll, not just when pending/idle!)
  useEffect(() => {
    if (status.scan_id && isQueueId(status.scan_id) && (status.status === 'pending' || status.status === 'idle' || status.status === 'running')) {
      const fetchQueueStatus = async () => {
        try {
          const { apiFetch } = await import('../utils/apiClient')
          const response = await apiFetch(`/api/queue/${status.scan_id}/status`)
          if (response.ok) {
            const data = await response.json()
            setQueueStatus(data)
            
            // Update status based on queue status (Backend is source of truth!)
            // Map queue status to scan status for consistency
            if (data.status === 'running') {
              setStatus(prev => ({ ...prev, status: 'running' }))
            } else if (data.status === 'completed') {
              // Queue uses 'completed', but we need 'done' for scan system
              if (data.scan_id) {
                setStatus(prev => ({
                  ...prev,
                  status: 'done',
                  scan_id: data.scan_id,
                  results_dir: data.results_dir || prev.results_dir,
                }))
              } else {
                setStatus(prev => ({ ...prev, status: 'completed' }))
              }
            } else if (data.status === 'failed') {
              // Queue uses 'failed', but we need 'error' for scan system
              setStatus(prev => ({ ...prev, status: 'error' }))
            } else if (data.status === 'pending') {
              setStatus(prev => ({ ...prev, status: 'pending' }))
            }
          }
        } catch (error) {
          console.error('Failed to fetch queue status:', error)
        }
      }

      fetchQueueStatus()
      const interval = setInterval(fetchQueueStatus, 3000) // Poll every 3 seconds
      return () => clearInterval(interval)
    }
  }, [status.scan_id, status.status])

  // Poll scan status if running (non-queue scan or after queue scan started)
  useEffect(() => {
    if (status.status === 'running' && status.scan_id && !isQueueId(status.scan_id)) {
      const interval = setInterval(async () => {
        try {
          const { apiFetch } = await import('../utils/apiClient')
          const response = await apiFetch('/api/scan/status')
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

  // WebSocket: Real-time scan updates using new service
  const { service } = useWebSocket(
    status.status === 'running' && status.scan_id ? status.scan_id : null
  )

  // Handle WebSocket messages to update steps and progress
  useEffect(() => {
    if (!service) return

    const handleMessage = (data: WebSocketMessage) => {
      if (data.type === 'step_update' && data.steps) {
        setSteps(data.steps)
        if (data.progress_percentage !== undefined) {
          setProgress(data.progress_percentage)
        }
      } else if (data.type === 'initial_steps' && data.steps) {
        setSteps(data.steps)
        if (data.progress_percentage !== undefined) {
          setProgress(data.progress_percentage)
        }
      }
    }

    // Set up message handler
    service.onMessage(handleMessage)

    return () => {
      // Clean up message handler
      if (service) {
        service.onMessage(() => {}) // Clear handler
      }
    }
  }, [service])


  // Listen for messages from iframe (HTML Report)
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
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

  // Progress is now calculated in backend and sent via WebSocket

  // Show queue waiting state (Backend queue status: 'pending')
  if (status.status === 'pending') {
    const estimatedWaitMinutes = queueStatus?.position ? Math.ceil(queueStatus.position * 2) : 0 // Rough estimate: 2 min per scan
    
    return (
      <div style={{ 
        height: 'calc(100vh - 80px)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '2rem',
        padding: '2rem',
      }}>
        <div style={{ textAlign: 'center', maxWidth: '600px' }}>
          <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>⏳</div>
          <h2>Waiting in Queue</h2>
          <p style={{ opacity: 0.7, marginTop: '0.5rem', fontSize: '1.1rem' }}>
            Your scan is queued and will start automatically
          </p>
          
          {queueStatus ? (
            <>
              <div style={{
                marginTop: '2rem',
                padding: '1.5rem',
                background: 'var(--glass-bg-dark)',
                border: '1px solid var(--glass-border-dark)',
                borderRadius: '12px',
                width: '100%',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                  <span style={{ opacity: 0.8 }}>Position in Queue:</span>
                  <strong style={{ fontSize: '1.5rem' }}>#{queueStatus.position || '?'}</strong>
                </div>
                {estimatedWaitMinutes > 0 && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                    <span style={{ opacity: 0.8 }}>Estimated Wait:</span>
                    <strong>{estimatedWaitMinutes} minutes</strong>
                  </div>
                )}
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ opacity: '0.8' }}>Repository:</span>
                  <strong>{queueStatus.repository_name}</strong>
                </div>
              </div>
            </>
          ) : (
            <div style={{
              marginTop: '2rem',
              padding: '1.5rem',
              background: 'var(--glass-bg-dark)',
              border: '1px solid var(--glass-border-dark)',
              borderRadius: '12px',
              width: '100%',
            }}>
              <div style={{ opacity: 0.7 }}>Loading queue information...</div>
            </div>
          )}

          <div style={{
            marginTop: '2rem',
            width: '100%',
            maxWidth: '600px',
            background: 'var(--glass-bg-dark)',
            border: '1px solid var(--glass-border-dark)',
            borderRadius: '8px',
            padding: '1rem',
          }}>
            <div style={{ marginBottom: '0.5rem', fontSize: '0.9rem', opacity: 0.8 }}>
              Waiting for your turn...
            </div>
            <div style={{
              width: '100%',
              height: '8px',
              background: 'rgba(255, 255, 255, 0.1)',
              borderRadius: '4px',
              overflow: 'hidden',
            }}>
              <div style={{
                width: '100%',
                height: '100%',
                background: 'linear-gradient(90deg, #007bff, #0056b3)',
                animation: 'pulse 2s ease-in-out infinite',
              }} />
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Show loading/running state with steps (Backend status: 'running' from both systems)
  if (status.status === 'running' || ((status.status === 'done' || status.status === 'completed') && !status.results_dir)) {
    
    return (
      <div style={{ 
        height: 'calc(100vh - 80px)',
        display: 'flex',
        flexDirection: 'column',
        padding: '2rem',
        gap: '2rem',
      }}>
        {/* Header with Progress */}
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🔄</div>
          <h2>Scan in Progress...</h2>
          <p style={{ opacity: 0.7, marginTop: '0.5rem' }}>
            Scan ID: {status.scan_id}
          </p>
          
          {/* Progress Bar */}
          {steps.length > 0 && (
            <div style={{
              marginTop: '2rem',
              maxWidth: '800px',
              margin: '2rem auto 0',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.9rem', opacity: 0.8 }}>Progress</span>
                <strong style={{ fontSize: '1.1rem' }}>{progress}%</strong>
              </div>
              <div style={{
                width: '100%',
                height: '12px',
                background: 'rgba(255, 255, 255, 0.1)',
                borderRadius: '6px',
                overflow: 'hidden',
              }}>
                <div style={{
                  width: `${progress}%`,
                  height: '100%',
                  background: 'linear-gradient(90deg, #28a745, #20c997)',
                  transition: 'width 0.3s ease',
                }} />
              </div>
            </div>
          )}
        </div>

        {/* Steps Cards */}
        {steps.length > 0 && (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
            gap: '1rem',
            maxWidth: '1200px',
            margin: '0 auto',
            width: '100%',
          }}>
            {steps.map((step) => {
              const getStepColor = () => {
                switch (step.status) {
                  case 'completed': return '#28a745'
                  case 'running': return '#007bff'
                  case 'failed': return '#dc3545'
                  default: return '#6c757d'
                }
              }
              
              const getStepIcon = () => {
                switch (step.status) {
                  case 'completed': return '✅'
                  case 'running': return '⏳'
                  case 'failed': return '❌'
                  default: return '⏸️'
                }
              }

              return (
                <div
                  key={step.number}
                  style={{
                    padding: '1.5rem',
                    background: 'var(--glass-bg-dark)',
                    border: `2px solid ${getStepColor()}`,
                    borderRadius: '12px',
                    transition: 'all 0.3s ease',
                    opacity: step.status === 'pending' ? 0.6 : 1,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
                    <span style={{ fontSize: '1.5rem' }}>{getStepIcon()}</span>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '1rem' }}>
                        Step {step.number}
                      </div>
                      <div style={{ fontSize: '0.875rem', opacity: 0.8, marginTop: '0.25rem' }}>
                        {step.name}
                      </div>
                    </div>
                  </div>
                  {step.status === 'running' && (
                    <div style={{
                      width: '100%',
                      height: '4px',
                      background: 'rgba(0, 123, 255, 0.2)',
                      borderRadius: '2px',
                      overflow: 'hidden',
                      marginTop: '0.5rem',
                    }}>
                      <div style={{
                        width: '60%',
                        height: '100%',
                        background: '#007bff',
                        animation: 'pulse 1.5s ease-in-out infinite',
                      }} />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}

        {/* Logs Section removed - Backend sends logs: [] for security, no need to display */}
      </div>
    )
  }

  // Show error state (Backend status: 'error' from scan system or 'failed' from queue system)
  if (status.status === 'error' || status.status === 'failed') {
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

  // Show full-page report when scan is done (Backend status: 'done' from scan system or 'completed' from queue system)
  if ((status.status === 'done' || status.status === 'completed') && status.results_dir) {
    return (
      <div style={{ 
        height: 'calc(100vh - 80px)',
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
          <ReportViewer scanId={status.scan_id} />
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
          scanId={status.scan_id}
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
                <div style={{ opacity: 0.7, textAlign: 'center', padding: '2rem' }}>
                  Logs are not displayed for security reasons.
                </div>
              </div>
            </div>
          </>
        )}

        {/* AI Prompt Modal */}
        <AIPromptModal
          isOpen={isAIPromptModalOpen}
          onClose={() => setIsAIPromptModalOpen(false)}
          scanId={status.scan_id}
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