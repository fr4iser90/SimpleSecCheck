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

export function SubstepSlot({ current, typeStyle, getSubStepColor, getSubStepIcon }: SubstepSlotProps) {
  const fullTitle = [current.name, current.message].filter(Boolean).join(' — ')

  return (
    <div className="substep-slot-live">
      <div
        key={`${current.name}|${current.message ?? ''}|${current.status}`}
        className="substep-slot-live-inner"
        title={fullTitle || undefined}
      >
        <span className="substep-slot-live-icon" style={{ color: getSubStepColor(current) }}>
          {getSubStepIcon(current)}
        </span>
        <span className="substep-slot-live-badge" aria-hidden>{typeStyle.badge}</span>
        <div className="substep-slot-live-text">
          <span className="substep-slot-live-name" title={current.name}>
            {current.name}
          </span>
          {current.message ? (
            <span className="substep-slot-live-message" title={current.message}>
              {current.message}
            </span>
          ) : null}
        </div>
      </div>
    </div>
  )
}
