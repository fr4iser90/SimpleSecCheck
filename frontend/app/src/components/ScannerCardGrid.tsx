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
  error,
}: ScannerCardGridProps) {
  const [search, setSearch] = useState('')

  if (loading) {
    return <div className="scanner-grid-loading">Loading scanners…</div>
  }

  if (error) {
    return <div className="scanner-grid-error">{error}</div>
  }

  if (scanners.length === 0) {
    return <div className="scanner-grid-empty">No scanners available for this scan type.</div>
  }

  const sortedScanners = [...scanners].sort((a, b) => a.priority - b.priority)
  const q = search.trim().toLowerCase()
  const filtered = q
    ? sortedScanners.filter(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          (s.description || '').toLowerCase().includes(q) ||
          (s.categories || []).some((c) => c.toLowerCase().includes(q)),
      )
    : sortedScanners

  return (
    <div className="panel__body--flush" style={{ margin: '-1.25rem' }}>
      <div className="panel__toolbar">
        <input
          type="search"
          placeholder="Filter scanners…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            flex: 1,
            minWidth: 160,
            maxWidth: 260,
            padding: '0.4375rem 0.625rem',
            fontSize: '0.8125rem',
            border: '1px solid var(--ds-border)',
            borderRadius: 'var(--ds-radius-sm)',
            fontFamily: 'inherit',
          }}
        />
        <button type="button" onClick={onSelectAll} className="scanner-grid-button">
          Select all
        </button>
        <button type="button" onClick={onDeselectAll} className="scanner-grid-button">
          Clear
        </button>
        <span className="panel__toolbar-count">
          <em>{selectedScanners.length}</em> of {scanners.length} selected
        </span>
      </div>

      <div className="scanner-grid-cards">
        {filtered.map((scanner) => (
          <ScannerCard
            key={scanner.name}
            name={scanner.name}
            description={scanner.description || `Security scanner: ${scanner.name}`}
            categories={scanner.categories || ['Security']}
            icon={scanner.icon || '🔧'}
            priority={scanner.priority}
            enabled={scanner.enabled}
            selected={selectedScanners.includes(scanner.name)}
            requiresCondition={scanner.requires_condition}
            onToggle={onToggle}
          />
        ))}
      </div>

      {selectedScanners.length === 0 && (
        <div className="scanner-grid-warning">Select at least one scanner to start the scan.</div>
      )}
    </div>
  )
}
