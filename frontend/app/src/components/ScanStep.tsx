import { ReactNode, useState } from 'react'
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
  /** When true, step header is clickable to expand/collapse; initial state from `expanded` */
  collapsible?: boolean
}

export default function ScanStep({
  id,
  title,
  children,
  trigger,
  autoScroll = false,
  expanded = true,
  completed = false,
  required = false,
  collapsible = false
}: ScanStepProps) {
  const [isExpanded, setIsExpanded] = useState(expanded)
  const showContent = collapsible ? isExpanded : expanded

  const setScrollTarget = useAutoScroll({
    trigger: autoScroll ? trigger : undefined,
    enabled: autoScroll && showContent,
    delay: 400,
    offset: 100
  })

  return (
    <div
      ref={setScrollTarget}
      id={id}
      className={`glass scan-step ${completed ? 'completed' : ''} ${collapsible ? 'scan-step-collapsible' : ''}`}
    >
      {/* Step Header */}
      <div
        className="scan-step-header"
        style={{ marginBottom: showContent ? '1rem' : 0 }}
        onClick={collapsible ? () => setIsExpanded((e) => !e) : undefined}
        role={collapsible ? 'button' : undefined}
        tabIndex={collapsible ? 0 : undefined}
        onKeyDown={collapsible ? (ev) => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); setIsExpanded((e) => !e); } } : undefined}
        aria-expanded={collapsible ? isExpanded : undefined}
      >
        <div className={`scan-step-number ${completed ? 'completed' : 'pending'}`}>
          {completed ? '✓' : id.split('-')[1] || '•'}
        </div>
        <h2 className="scan-step-title">
          {title}
          {required && <span className="scan-step-required">*</span>}
        </h2>
        {collapsible && (
          <span className="scan-step-chevron" aria-hidden>
            {isExpanded ? '▼' : '▶'}
          </span>
        )}
        {completed && (
          <span className="scan-step-completed-badge">
            Completed
          </span>
        )}
      </div>

      {/* Step Content */}
      {showContent && (
        <div className="scan-step-content">
          {children}
        </div>
      )}
    </div>
  )
}
