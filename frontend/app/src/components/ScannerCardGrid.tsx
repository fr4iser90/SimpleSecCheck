import { useState } from 'react'
import ScannerCard from './ScannerCard'

interface Scanner {
  name: string
  description?: string
  categories?: string[]
  icon?: string
  scan_types: string[]
  priority: number
  requires_condition: string | null
  enabled: boolean
}

interface ScannerCardGridProps {
  scanners: Scanner[]
  selectedScanners: string[]
  onToggle: (scannerName: string) => void
  onSelectAll: () => void
  onDeselectAll: () => void
  loading?: boolean
  error?: string | null
}

export default function ScannerCardGrid({
  scanners,
  selectedScanners,
  onToggle,
  onSelectAll,
  onDeselectAll,
  loading,
  error
}: ScannerCardGridProps) {
  const [cardsExpanded, setCardsExpanded] = useState(false)

  if (loading) {
    return (
      <div className="scanner-grid-loading">
        🔄 Loading scanners...
      </div>
    )
  }

  if (error) {
    return (
      <div className="glass scanner-grid-error">
        ⚠️ {error}
      </div>
    )
  }

  if (scanners.length === 0) {
    return (
      <div className="scanner-grid-empty">
        No scanners available for this scan type.
      </div>
    )
  }

  // Sort scanners by priority
  const sortedScanners = [...scanners].sort((a, b) => a.priority - b.priority)

  return (
    <div>
      {/* Action Buttons - always visible */}
      <div className="scanner-grid-actions">
        <button
          type="button"
          onClick={onSelectAll}
          className="scanner-grid-button"
        >
          Select All
        </button>
        <button
          type="button"
          onClick={onDeselectAll}
          className="scanner-grid-button"
        >
          Deselect All
        </button>
        <button
          type="button"
          onClick={() => setCardsExpanded((e) => !e)}
          className="scanner-grid-button"
          title={cardsExpanded ? 'Hide scanner list' : 'Show scanner list'}
        >
          {cardsExpanded ? '▼ Hide list' : '▶ Show list'}
        </button>
        {selectedScanners.length > 0 && (
          <div className="glass scanner-grid-selection-count">
            ✓ {selectedScanners.length} scanner{selectedScanners.length !== 1 ? 's' : ''} selected
          </div>
        )}
      </div>

      {/* Scanner Cards Grid - collapsed by default */}
      {cardsExpanded && (
        <div className="scanner-grid-cards">
          {sortedScanners.map(scanner => (
            <ScannerCard
              key={scanner.name}
              name={scanner.name}
              description={scanner.description || `Security scanner: ${scanner.name}`}
              categories={scanner.categories || ['Security Scanning']}
              icon={scanner.icon || '🔧'}
              priority={scanner.priority}
              enabled={scanner.enabled}
              selected={selectedScanners.includes(scanner.name)}
              requiresCondition={scanner.requires_condition}
              onToggle={onToggle}
            />
          ))}
        </div>
      )}

      {/* Selection Status */}
      {selectedScanners.length === 0 && (
        <div className="glass scanner-grid-warning">
          ⚠️ Please select at least one scanner to start the scan.
        </div>
      )}
    </div>
  )
}
