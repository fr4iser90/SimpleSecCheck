import AppIcon from './AppIcon'

interface ScannerCardProps {
  name: string
  description: string
  categories: string[]
  icon: string
  priority: number
  enabled: boolean
  selected: boolean
  requiresCondition?: string | null
  onToggle: (name: string) => void
}

export default function ScannerCard({
  name,
  description,
  categories,
  icon,
  enabled,
  selected,
  requiresCondition,
  onToggle,
}: ScannerCardProps) {
  return (
    <div
      role="button"
      tabIndex={enabled ? 0 : -1}
      onClick={() => enabled && onToggle(name)}
      onKeyDown={(e) => {
        if (enabled && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault()
          onToggle(name)
        }
      }}
      className={`scanner-card ${selected ? 'selected' : ''} ${!enabled ? 'disabled' : ''}`}
    >
      <span className="scanner-card-check" aria-hidden>
        {selected ? <AppIcon name="check" size={10} /> : null}
      </span>

      <div className="scanner-card-header">
        <span className="scanner-card-icon">{icon}</span>
        <h3 className={`scanner-card-name ${!enabled ? 'disabled' : ''}`}>{name}</h3>
      </div>

      <p className="scanner-card-description">{description}</p>

      <div className="scanner-card-categories">
        {categories.map((category, idx) => (
          <span key={idx} className="scanner-card-category">
            {category}
          </span>
        ))}
      </div>

      {requiresCondition && (
        <div className="scanner-card-requires">Requires: {requiresCondition}</div>
      )}
    </div>
  )
}
