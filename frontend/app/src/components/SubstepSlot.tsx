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
    <div
      className="substep-slot-live"
      style={{
        marginTop: '0.75rem',
        paddingTop: '0.75rem',
        borderTop: '1px solid rgba(255, 255, 255, 0.1)',
      }}
    >
      <div
        key={`${current.name}|${current.message ?? ''}|${current.status}`}
        className="substep-slot-live-inner"
        title={fullTitle || undefined}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.5rem 0.65rem',
          background: typeStyle.bgColor,
          border: `1px solid ${typeStyle.borderColor}`,
          borderRadius: '6px',
          fontSize: '0.8125rem',
          minWidth: 0,
          animation: 'substepFadeIn 0.2s ease-out forwards',
        }}
      >
        <span style={{ color: getSubStepColor(current), fontWeight: 'bold', fontSize: '0.75rem', flexShrink: 0 }}>
          {getSubStepIcon(current)}
        </span>
        <span style={{ fontSize: '0.7rem', opacity: 0.6, flexShrink: 0 }} aria-hidden>{typeStyle.badge}</span>
        <span
          style={{
            minWidth: 0,
            flex: '1 1 35%',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            opacity: 0.95,
          }}
          title={current.name}
        >
          {current.name}
        </span>
        {current.message ? (
          <span
            style={{
              minWidth: 0,
              flex: '1 1 45%',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              fontSize: '0.75rem',
              opacity: 0.75,
            }}
            title={current.message}
          >
            {current.message}
          </span>
        ) : (
          <span style={{ flex: '0 0 8px' }} />
        )}
      </div>
    </div>
  )
}
