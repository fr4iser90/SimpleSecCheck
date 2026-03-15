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
  onToggle
}: ScannerCardProps) {
  return (
    <div
      onClick={() => enabled && onToggle(name)}
      className={`glass scanner-card ${selected ? 'selected' : ''} ${!enabled ? 'disabled' : ''}`}
    >
      {/* Checkbox in top-right corner */}
      <div className="scanner-card-checkbox">
        <input
          type="checkbox"
          checked={selected}
          onChange={() => {}} // Handled by parent onClick
          disabled={!enabled}
        />
      </div>

      {/* Icon and Name */}
      <div className="scanner-card-header">
        <span className="scanner-card-icon">{icon}</span>
        <h3 className={`scanner-card-name ${!enabled ? 'disabled' : ''}`}>
          {name}
        </h3>
      </div>

      {/* Description */}
      <p className="scanner-card-description">
        {description}
      </p>

      {/* Categories */}
      <div className="scanner-card-categories">
        {categories.map((category, idx) => (
          <span key={idx} className="scanner-card-category">
            {category}
          </span>
        ))}
      </div>

      {/* Requires Condition */}
      {requiresCondition && (
        <div className="scanner-card-requires">
          ⚠️ Requires: {requiresCondition}
        </div>
      )}

      {/* Selected Badge */}
      {selected && (
        <div className="scanner-card-selected-badge">
          ✓ Selected
        </div>
      )}
    </div>
  )
}
