import { ReactNode, useState } from 'react'
import { useAutoScroll } from '../hooks/useAutoScroll'
import AppIcon from './AppIcon'

interface ScanStepProps {
  id: string
  title: string
  description?: string
  children: ReactNode
  trigger?: unknown
  autoScroll?: boolean
  expanded?: boolean
  completed?: boolean
  required?: boolean
  collapsible?: boolean
  stepNumber?: string
}

export default function ScanStep({
  id,
  title,
  description,
  children,
  trigger,
  autoScroll = false,
  expanded = true,
  completed = false,
  required = false,
  collapsible = false,
  stepNumber,
}: ScanStepProps) {
  const [isExpanded, setIsExpanded] = useState(expanded)
  const showContent = collapsible ? isExpanded : expanded
  const num = stepNumber || id.split('-')[1] || '•'

  const setScrollTarget = useAutoScroll({
    trigger: autoScroll ? trigger : undefined,
    enabled: autoScroll && showContent,
    delay: 400,
    offset: 100,
  })

  const titleRow = (
    <div className="panel__title-row" style={{ width: '100%' }}>
      <span className={`step-dot${completed ? ' step-dot--done' : showContent ? ' step-dot--active' : ''}`}>
        {completed ? <AppIcon name="check" size={10} /> : num}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <h2 className="panel__title">
          {title}
          {required ? <span style={{ color: 'var(--ds-error)', marginLeft: '0.2rem' }}>*</span> : null}
        </h2>
      </div>
      {completed && !collapsible ? <span className="step-badge">Completed</span> : null}
      {collapsible ? (
        <>
          {!isExpanded ? <span className="form-label-hint" style={{ marginLeft: 'auto' }}>Optional</span> : null}
          <AppIcon name="chevron" size={16} className={isExpanded ? 'panel__collapse-toggle--open' : ''} />
        </>
      ) : null}
    </div>
  )

  return (
    <section ref={setScrollTarget} id={id} className="panel scan-panel">
      {collapsible ? (
        <button
          type="button"
          className={`panel__collapse-toggle${isExpanded ? ' panel__collapse-toggle--open' : ''}`}
          onClick={() => setIsExpanded((e) => !e)}
          aria-expanded={isExpanded}
        >
          {titleRow}
        </button>
      ) : (
        <div className="panel__header">
          {titleRow}
          {description ? <p className="panel__desc">{description}</p> : null}
        </div>
      )}

      {showContent ? (
        <div className="panel__body">
          {collapsible && description ? <p className="panel__desc" style={{ marginTop: 0 }}>{description}</p> : null}
          {children}
        </div>
      ) : null}
    </section>
  )
}
