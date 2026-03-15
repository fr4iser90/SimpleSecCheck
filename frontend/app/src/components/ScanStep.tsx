import { ReactNode } from 'react'
import { useAutoScroll } from '../hooks/useAutoScroll'

interface ScanStepProps {
  id: string
  title: string
  children: ReactNode
  trigger?: any // Value that triggers auto-scroll when changed
  autoScroll?: boolean
  expanded?: boolean
  completed?: boolean
  required?: boolean
}

export default function ScanStep({
  id,
  title,
  children,
  trigger,
  autoScroll = false,
  expanded = true,
  completed = false,
  required = false
}: ScanStepProps) {
  const setScrollTarget = useAutoScroll({
    trigger: autoScroll ? trigger : undefined,
    enabled: autoScroll && expanded,
    delay: 400,
    offset: 100
  })

  return (
    <div
      ref={setScrollTarget}
      id={id}
      className={`glass scan-step ${completed ? 'completed' : ''}`}
    >
      {/* Step Header */}
      <div className="scan-step-header" style={{ marginBottom: expanded ? '1rem' : 0 }}>
        <div className={`scan-step-number ${completed ? 'completed' : 'pending'}`}>
          {completed ? '✓' : id.split('-')[1] || '•'}
        </div>
        <h2 className="scan-step-title">
          {title}
          {required && <span className="scan-step-required">*</span>}
        </h2>
        {completed && (
          <span className="scan-step-completed-badge">
            Completed
          </span>
        )}
      </div>

      {/* Step Content */}
      {expanded && (
        <div className="scan-step-content">
          {children}
        </div>
      )}
    </div>
  )
}
