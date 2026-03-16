interface Scanner {
  name: string
  description?: string
  scan_types?: string[]
}

interface ScannerSelectionProps {
  availableScanners: Scanner[]
  selectedScanners: string[]
  onSelectionChange: (scanners: string[]) => void
  maxHeight?: string
}

export default function ScannerSelection({ 
  availableScanners, 
  selectedScanners, 
  onSelectionChange,
  maxHeight = '200px'
}: ScannerSelectionProps) {
  return (
    <>
      <label style={{ display: 'block', marginBottom: '0.5rem' }}>
        Scanners ({selectedScanners.length} selected)
      </label>
      <div style={{ 
        maxHeight, 
        overflowY: 'auto', 
        border: '1px solid var(--glass-border-dark)',
        borderRadius: '4px',
        padding: '0.5rem',
        background: 'rgba(0, 0, 0, 0.2)'
      }}>
        {availableScanners.map(scanner => (
          <label key={scanner.name} style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '0.5rem', 
            cursor: 'pointer',
            padding: '0.25rem 0'
          }}>
            <input
              type="checkbox"
              checked={selectedScanners.includes(scanner.name)}
              onChange={(e) => {
                if (e.target.checked) {
                  onSelectionChange([...selectedScanners, scanner.name])
                } else {
                  onSelectionChange(selectedScanners.filter(s => s !== scanner.name))
                }
              }}
            />
            <span>{scanner.name}</span>
          </label>
        ))}
      </div>
      <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.5rem' }}>
        <button 
          type="button" 
          onClick={() => onSelectionChange(availableScanners.map(s => s.name))}
          style={{ fontSize: '0.875rem', padding: '0.25rem 0.5rem' }}
        >
          Select All
        </button>
        <button 
          type="button" 
          onClick={() => onSelectionChange([])}
          style={{ fontSize: '0.875rem', padding: '0.25rem 0.5rem' }}
        >
          Clear
        </button>
      </div>
    </>
  )
}
