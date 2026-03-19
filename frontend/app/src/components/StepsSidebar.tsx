import { useState, useEffect } from 'react'
import { useWebSocket } from '../services/websocketService'
import { SubstepSlot } from './SubstepSlot'

interface StepsSidebarProps {
  isOpen: boolean
  onClose: () => void
  scanId?: string | null
}

interface SubStep {
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  message?: string
  started_at?: string | null
  completed_at?: string | null
}

interface Step {
  number: number
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  message?: string
  substeps?: SubStep[]
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

  // Load steps from REST API when sidebar opens
  useEffect(() => {
    if (!isOpen || !scanId) {
      setLoading(false)
      return
    }

    const fetchSteps = async () => {
      try {
        setLoading(true)
        const { apiFetch } = await import('../utils/apiClient')
        const response = await apiFetch(`/api/v1/scans/${scanId}/steps`)
        if (response.ok) {
          const data = await response.json()
          if (data.steps && data.steps.length > 0) {
            const convertedSteps: Step[] = data.steps.map((step: any) => ({
              number: step.number || 0,
              name: step.name || 'Unknown',
              status: (step.status || 'pending') as 'pending' | 'running' | 'completed' | 'failed',
              message: step.message || '',
              substeps: step.substeps ? step.substeps.map((substep: any) => ({
                name: substep.name || '',
                status: (substep.status || 'pending') as 'pending' | 'running' | 'completed' | 'failed',
                message: substep.message || '',
                started_at: substep.started_at || null,
                completed_at: substep.completed_at || null,
              })) : []
            }))
            setSteps(convertedSteps)
          }
        }
      } catch (error) {
        console.error('Failed to fetch steps:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchSteps()
  }, [isOpen, scanId])

  // Handle WebSocket messages to update steps in real-time
  useEffect(() => {
    if (!isOpen || !scanId || !service) return

    const handleMessage = (data: WebSocketMessage) => {
      if (data.type === 'step_update' && data.steps) {
        setSteps(data.steps)
      } else if (data.type === 'initial_steps' && data.steps) {
        setSteps(data.steps)
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
          background: 'var(--modal-overlay-bg)',
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
          boxShadow: 'var(--shadow-dark)',
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
              {steps.map((step) => {
                const getSubStepIcon = (substepStatus: string) => {
                  switch (substepStatus) {
                    case 'completed': return '✓'
                    case 'running': return '⟳'
                    case 'failed': return '✗'
                    default: return '○'
                  }
                }

                const getSubStepColor = (substepStatus: string) => {
                  switch (substepStatus) {
                    case 'completed': return '#28a745'
                    case 'running': return '#007bff'
                    case 'failed': return '#dc3545'
                    default: return '#6c757d'
                  }
                }

                return (
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
                    {step.substeps && step.substeps.length > 0 && (
                      <SubstepSlot
                        current={step.substeps[step.substeps.length - 1]}
                        typeStyle={{ badge: '⚙️', bgColor: 'var(--surface-muted)', borderColor: 'var(--glass-border-dark)' }}
                        getSubStepColor={(s) => getSubStepColor(s.status)}
                        getSubStepIcon={(s) => getSubStepIcon(s.status)}
                      />
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
