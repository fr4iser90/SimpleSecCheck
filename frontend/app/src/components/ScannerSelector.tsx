import { useState, useEffect } from 'react'

interface Scanner {
  name: string
  scan_types: string[]
  priority: number
  requires_condition: string | null
  enabled: boolean
}

interface ScannerSelectorProps {
  scanType: string  // Backend-driven, can be any scan type from config
  selectedScanners: string[]
  onSelectionChange: (scanners: string[]) => void
}

export default function ScannerSelector({ 
  scanType, 
  selectedScanners, 
  onSelectionChange 
}: ScannerSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [scanners, setScanners] = useState<Scanner[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Load scanners dynamically from backend
  useEffect(() => {
    const loadScanners = async () => {
      setLoading(true)
      setError(null)
      try {
        const response = await fetch(`/api/scanners?scan_type=${scanType}`)
        if (!response.ok) {
          throw new Error('Failed to load scanners')
        }
        const data = await response.json()
        const loadedScanners = data.scanners || []
        setScanners(loadedScanners)
        
        // Auto-select all enabled scanners by default (only if nothing selected yet)
        if (selectedScanners.length === 0 && loadedScanners.length > 0) {
          const enabledScanners = loadedScanners
            .filter((s: Scanner) => s.enabled)
            .map((s: Scanner) => s.name)
          onSelectionChange(enabledScanners)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load scanners')
        console.error('Error loading scanners:', err)
      } finally {
        setLoading(false)
      }
    }
    
    if (scanType) {
      loadScanners()
    } else {
      setScanners([])
      onSelectionChange([])
    }
  }, [scanType]) // Reload when scan type changes
  
  const handleToggle = (scanner: string) => {
    if (selectedScanners.includes(scanner)) {
      onSelectionChange(selectedScanners.filter(s => s !== scanner))
    } else {
      onSelectionChange([...selectedScanners, scanner])
    }
  }
  
  const handleSelectAll = () => {
    const enabledScanners = scanners
      .filter(s => s.enabled)
      .map(s => s.name)
    onSelectionChange(enabledScanners)
  }
  
  const handleDeselectAll = () => {
    onSelectionChange([])
  }
  
  // Sort scanners by priority
  const sortedScanners = [...scanners].sort((a, b) => a.priority - b.priority)
  
  return (
    <div className="form-group">
      <label>Scanner Selection</label>
      <details 
        open={isOpen}
        onToggle={(e) => setIsOpen((e.target as HTMLDetailsElement).open)}
        style={{ 
          border: '1px solid #ced4da', 
          borderRadius: '8px', 
          padding: '1rem',
          marginBottom: '1rem'
        }}
      >
        <summary style={{ 
          cursor: 'pointer', 
          userSelect: 'none',
          listStyle: 'none'
        }}>
          🔧 Select which scanners to run. At least one scanner must be selected.
        </summary>
        
        <div style={{ marginTop: '1rem' }}>
          {loading && (
            <div style={{ padding: '1rem', textAlign: 'center', color: '#6c757d' }}>
              🔄 Loading scanners...
            </div>
          )}
          
          {error && (
            <div style={{ 
              padding: '0.75rem', 
              background: 'rgba(220, 53, 69, 0.1)', 
              borderRadius: '4px',
              color: '#dc3545',
              fontSize: '0.875rem',
              marginBottom: '1rem'
            }}>
              ⚠️ {error}
            </div>
          )}
          
          {!loading && !error && (
            <>
              {/* Select All / Deselect All buttons */}
              <div style={{ 
                display: 'flex', 
                gap: '0.5rem', 
                marginBottom: '1rem' 
              }}>
                <button
                  type="button"
                  onClick={handleSelectAll}
                  style={{
                    padding: '0.25rem 0.75rem',
                    fontSize: '0.875rem',
                    border: '1px solid #ced4da',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Select All
                </button>
                <button
                  type="button"
                  onClick={handleDeselectAll}
                  style={{
                    padding: '0.25rem 0.75rem',
                    fontSize: '0.875rem',
                    border: '1px solid #ced4da',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Deselect All
                </button>
              </div>
              
              {/* Scanner checkboxes */}
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
                gap: '0.75rem',
                maxHeight: '300px',
                overflowY: 'auto',
                padding: '0.5rem',
                border: '1px solid #e9ecef',
                borderRadius: '4px'
              }}>
                {sortedScanners.map(scanner => (
                  <label 
                    key={scanner.name}
                    style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      gap: '0.5rem',
                      fontSize: '0.875rem',
                      cursor: scanner.enabled ? 'pointer' : 'not-allowed',
                      padding: '0.25rem 0',
                      userSelect: 'none',
                      opacity: scanner.enabled ? 1 : 0.5
                    }}
                  >
                    <input 
                      type="checkbox" 
                      checked={selectedScanners.includes(scanner.name)}
                      onChange={() => handleToggle(scanner.name)}
                      disabled={!scanner.enabled}
                    />
                    <span>
                      {scanner.name}
                      {scanner.requires_condition && (
                        <small style={{ fontSize: '0.75rem', color: '#6c757d', marginLeft: '0.25rem' }}>
                          ({scanner.requires_condition})
                        </small>
                      )}
                    </span>
                  </label>
                ))}
              </div>
              
              {selectedScanners.length > 0 ? (
                <div style={{ 
                  marginTop: '0.75rem',
                  padding: '0.5rem',
                  background: 'rgba(40, 167, 69, 0.1)',
                  border: '1px solid #28a745',
                  borderRadius: '4px',
                  fontSize: '0.875rem',
                  color: '#155724'
                }}>
                  ✓ {selectedScanners.length} scanner(s) selected
                </div>
              ) : (
                <div style={{ 
                  marginTop: '0.75rem',
                  padding: '0.5rem',
                  background: 'rgba(220, 53, 69, 0.1)',
                  border: '1px solid #dc3545',
                  borderRadius: '4px',
                  fontSize: '0.875rem',
                  color: '#a71d2a'
                }}>
                  ⚠️ Bitte wähle mindestens einen Scanner aus, um den Scan zu starten.
                </div>
              )}
            </>
          )}
        </div>
      </details>
    </div>
  )
}
