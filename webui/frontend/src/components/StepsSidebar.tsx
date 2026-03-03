import { useState, useEffect } from 'react'

interface StepsSidebarProps {
  isOpen: boolean
  onClose: () => void
}

interface Step {
  number: number
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  message?: string
}

export default function StepsSidebar({ isOpen, onClose }: StepsSidebarProps) {
  const [steps, setSteps] = useState<Step[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!isOpen) return

    // Get scan_id from URL or props (for now, we'll need to pass it)
    // For simplicity, we'll use the same approach as ScanView
    const urlParams = new URLSearchParams(window.location.search)
    const scanId = urlParams.get('scan_id') || undefined
    
    if (!scanId) {
      setLoading(false)
      return
    }

    let ws: WebSocket | null = null
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null
    let heartbeatInterval: ReturnType<typeof setInterval> | null = null
    let reconnectAttempts = 0
    const maxReconnectAttempts = 10
    const reconnectDelay = 3000
    
    const connect = () => {
      try {
        const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/scan/stream?scan_id=${scanId}`
        ws = new WebSocket(wsUrl)
        
        ws.onopen = () => {
          console.log('[StepsSidebar] WebSocket connected')
          reconnectAttempts = 0
          
          heartbeatInterval = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
              ws.send('ping')
            }
          }, 25000)
        }
        
        ws.onmessage = (e) => {
          try {
            const data = JSON.parse(e.data)
            
            if (data.error) {
              console.error('[StepsSidebar] WebSocket error:', data.error)
              setLoading(false)
              return
            }
            
            // Update steps from WebSocket data
            if (data.steps && Array.isArray(data.steps)) {
              setSteps(data.steps)
              setLoading(false)
            }
          } catch (error) {
            console.error('[StepsSidebar] Failed to parse WebSocket data:', error)
            setLoading(false)
          }
        }
        
        ws.onerror = (error) => {
          console.error('[StepsSidebar] WebSocket error:', error)
          setLoading(false)
        }
        
        ws.onclose = () => {
          console.log('[StepsSidebar] WebSocket closed')
          
          if (heartbeatInterval) {
            clearInterval(heartbeatInterval)
            heartbeatInterval = null
          }
          
          if (reconnectAttempts < maxReconnectAttempts && isOpen) {
            reconnectAttempts++
            reconnectTimeout = setTimeout(() => {
              connect()
            }, reconnectDelay)
          } else {
            setLoading(false)
          }
        }
      } catch (error) {
        console.error('[StepsSidebar] WebSocket connection error:', error)
        setLoading(false)
      }
    }
    
    connect()
    
    return () => {
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout)
      }
      if (heartbeatInterval) {
        clearInterval(heartbeatInterval)
      }
      if (ws) {
        ws.close()
      }
    }
  }, [isOpen])

  if (!isOpen) return null

  return (
    <>
      {/* Overlay */}
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
        onClick={onClose}
      />
      {/* Sidebar */}
      <div
        style={{
          position: 'fixed',
          top: 0,
          right: 0,
          bottom: 0,
          width: '400px',
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
        {/* Header */}
        <div
          style={{
            padding: '1.5rem',
            borderBottom: '1px solid var(--glass-border-dark)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <h2 style={{ margin: 0, fontSize: '1.25rem' }}>📋 Scan Steps</h2>
          <button
            onClick={onClose}
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

        {/* Content */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '1.5rem',
          }}
        >
          {loading ? (
            <div style={{ opacity: 0.7 }}>Loading steps...</div>
          ) : steps.length === 0 ? (
            <div style={{ opacity: 0.7 }}>No steps available</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {steps.map((step) => (
                <div
                  key={step.number}
                  style={{
                    padding: '1rem',
                    background: 'var(--glass-bg-dark)',
                    border: '1px solid var(--glass-border-dark)',
                    borderRadius: '8px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                    <span style={{ fontWeight: 600 }}>Step {step.number}:</span>
                    <span>{step.name}</span>
                    {step.status === 'completed' && <span>✅</span>}
                    {step.status === 'running' && <span>⏳</span>}
                    {step.status === 'failed' && <span>❌</span>}
                  </div>
                  {step.message && (
                    <div style={{ fontSize: '0.875rem', opacity: 0.8, marginTop: '0.25rem' }}>
                      {step.message}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
