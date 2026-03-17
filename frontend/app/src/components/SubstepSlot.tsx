import { useState, useEffect } from 'react'

export interface SubStep {
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  message?: string
  type?: 'phase' | 'action' | 'output'
}

interface SubstepSlotProps {
  current: SubStep
  typeStyle: { badge: string; bgColor: string; borderColor: string }
  getSubStepColor: (s: SubStep) => string
  getSubStepIcon: (s: SubStep) => string
}

const FADE_OUT_MS = 150

export function SubstepSlot({ current, typeStyle, getSubStepColor, getSubStepIcon }: SubstepSlotProps) {
  const [prev, setPrev] = useState<SubStep | null>(null)
  const [display, setDisplay] = useState<SubStep>(current)

  useEffect(() => {
    const changed = current.name !== display.name || current.message !== display.message
    if (changed) {
      setPrev(display)
      setDisplay(current)
      const t = setTimeout(() => setPrev(null), FADE_OUT_MS)
      return () => clearTimeout(t)
    } else {
      setDisplay(current)
    }
  }, [current.name, current.message, current.status])

  const renderLine = (substep: SubStep, className: string) => (
    <div
      className={className}
      style={{
        position: 'absolute',
        inset: 0,
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        padding: '0.5rem',
        background: typeStyle.bgColor,
        border: `1px solid ${typeStyle.borderColor}`,
        borderRadius: '6px',
        fontSize: '0.875rem',
      }}
    >
      <span style={{ color: getSubStepColor(substep), fontWeight: 'bold', fontSize: '0.75rem' }}>
        {getSubStepIcon(substep)}
      </span>
      <span style={{ fontSize: '0.7rem', opacity: 0.6 }}>{typeStyle.badge}</span>
      <span style={{ flex: 1, opacity: 0.9 }}>{substep.name}</span>
      {substep.message && (
        <span style={{ fontSize: '0.75rem', opacity: 0.7 }}>{substep.message}</span>
      )}
    </div>
  )

  return (
    <div style={{
      marginTop: '0.75rem',
      paddingTop: '0.75rem',
      borderTop: '1px solid rgba(255, 255, 255, 0.1)',
      position: 'relative',
      minHeight: '2.5rem',
    }}>
      {prev && renderLine(prev, 'substep-fade-out')}
      {renderLine(display, 'substep-fade-in')}
    </div>
  )
}
