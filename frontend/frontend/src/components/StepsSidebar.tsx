import { useState, useEffect } from 'react'
import { useWebSocket } from '../services/websocketService'

interface StepsSidebarProps {
  isOpen: boolean
  onClose: () => void
  scanId?: string | null
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

export default function StepsSidebar({ isOpen, onClose, scanId }: StepsSidebarProps) {
  const [steps, setSteps] = useState<Step[]>([])
  const [loading, setLoading] = useState(true)

  // Use the same WebSocket service as ScanView
  const { service } = useWebSocket(
    isOpen && scanId ? scanId : null
  )

  useEffect(() => {
    if (!isOpen || !scanId) {
      setLoading(false)
      return
    }

    // Handle WebSocket messages to update steps
    if (service) {
      const handleMessage = (data: WebSocketMessage) => {
        if (data.type === 'step_update' && data.steps) {
          setSteps(data.steps)
          setLoading(false)
        } else if (data.type === 'initial_steps' && data.steps) {
          setSteps(data.steps)
          setLoading(false)
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
    }
  }, [service, isOpen, scanId])

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
