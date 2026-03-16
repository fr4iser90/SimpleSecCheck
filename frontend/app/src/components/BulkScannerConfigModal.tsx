import ScannerSelection from './ScannerSelection'

interface Scanner {
  name: string
  description?: string
  scan_types?: string[]
}

interface BulkScannerConfigModalProps {
  isOpen: boolean
  reposCount: number
  availableScanners: Scanner[]
  selectedScanners: string[]
  onSelectionChange: (scanners: string[]) => void
  onApply: () => void
  onClose: () => void
}

export default function BulkScannerConfigModal({
  isOpen,
  reposCount,
  availableScanners,
  selectedScanners,
  onSelectionChange,
  onApply,
  onClose
}: BulkScannerConfigModalProps) {
  if (!isOpen) return null

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0, 0, 0, 0.85)',
      backdropFilter: 'blur(8px)',
      WebkitBackdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div style={{
        background: 'rgba(20, 20, 30, 0.95)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        padding: '2rem',
        borderRadius: '8px',
        width: '90%',
        maxWidth: '600px',
        border: '1px solid var(--glass-border-dark)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)'
      }}>
        <h2 style={{ marginTop: 0 }}>Apply Scanner Selection to All Repos</h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
          Select scanners to apply to all {reposCount} repositories
        </p>
        <div style={{ marginBottom: '1rem' }}>
          <ScannerSelection
            availableScanners={availableScanners}
            selectedScanners={selectedScanners}
            onSelectionChange={onSelectionChange}
            maxHeight="300px"
          />
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
          <button 
            type="button" 
            onClick={onClose}
          >
            Cancel
          </button>
          <button 
            type="button" 
            className="primary" 
            onClick={onApply}
            disabled={selectedScanners.length === 0}
          >
            Apply to All ({reposCount} repos)
          </button>
        </div>
      </div>
    </div>
  )
}
