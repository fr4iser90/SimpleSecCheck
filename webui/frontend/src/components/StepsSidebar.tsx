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

    const fetchSteps = async () => {
      try {
        const response = await fetch('/api/scan/logs')
        if (response.ok) {
          const data = await response.json()
          if (data.lines && Array.isArray(data.lines)) {
            // Parse steps from log lines
            const stepMap = new Map<number, Step>()
            
            data.lines.forEach((line: string) => {
              // Match patterns like "Step 1: Cloning Git repository..." or "✓ Step 2: Initializing scan..."
              const stepMatch = line.match(/([⏳✓❌]?)\s*Step\s+(\d+):\s*(.+)/i)
              if (stepMatch) {
                const [, statusIcon, stepNum, message] = stepMatch
                const stepNumber = parseInt(stepNum, 10)
                
                let status: Step['status'] = 'pending'
                if (statusIcon === '✓') status = 'completed'
                else if (statusIcon === '⏳') status = 'running'
                else if (statusIcon === '❌') status = 'failed'
                
                // Extract step name (before "..." or "completed" etc.)
                const nameMatch = message.match(/^(.+?)(?:\s+\.\.\.|\s+completed|$)/i)
                const stepName = nameMatch ? nameMatch[1].trim() : message.trim()
                
                if (!stepMap.has(stepNumber)) {
                  stepMap.set(stepNumber, {
                    number: stepNumber,
                    name: stepName,
                    status: status,
                    message: message.trim(),
                  })
                } else {
                  // Update existing step
                  const existing = stepMap.get(stepNumber)!
                  existing.status = status
                  existing.message = message.trim()
                }
              }
            })
            
            // Convert map to sorted array
            const sortedSteps = Array.from(stepMap.values()).sort((a, b) => a.number - b.number)
            setSteps(sortedSteps)
          }
        }
      } catch (error) {
        console.error('Failed to fetch steps:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchSteps()
    const interval = setInterval(fetchSteps, 2000) // Poll every 2 seconds

    return () => clearInterval(interval)
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
