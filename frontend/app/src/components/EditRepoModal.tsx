import { GitHubRepo } from '../utils/repoUtils'
import ScannerSelection from './ScannerSelection'

interface EditRepoFormData {
  branch: string
  auto_scan_enabled: boolean
  scan_on_push: boolean
  scan_frequency: string
  scanners: string[]
}

interface EditRepoModalProps {
  isOpen: boolean
  repo: GitHubRepo | null
  onClose: () => void
  onSubmit: (e: React.FormEvent) => void
  formData: EditRepoFormData
  onFormDataChange: (data: EditRepoFormData) => void
  availableScanners: any[]
}

export default function EditRepoModal({ isOpen, repo, onClose, onSubmit, formData, onFormDataChange, availableScanners }: EditRepoModalProps) {
  if (!isOpen || !repo) return null

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
        maxWidth: '500px',
        border: '1px solid var(--glass-border-main)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)'
      }}>
        <h2 style={{ marginTop: 0 }}>Repository Settings</h2>
        <form onSubmit={onSubmit}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem' }}>Branch</label>
            <input
              type="text"
              required
              value={formData.branch}
              onChange={(e) => onFormDataChange({ ...formData, branch: e.target.value })}
              style={{ width: '100%' }}
            />
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={formData.auto_scan_enabled}
                onChange={(e) => onFormDataChange({ ...formData, auto_scan_enabled: e.target.checked })}
              />
              <span>Enable Auto-Scan</span>
            </label>
          </div>
          {formData.auto_scan_enabled && (
            <>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={formData.scan_on_push}
                    onChange={(e) => onFormDataChange({ ...formData, scan_on_push: e.target.checked })}
                  />
                  <span>Scan on Push</span>
                </label>
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem' }}>Scan Frequency</label>
                <select
                  value={formData.scan_frequency}
                  onChange={(e) => onFormDataChange({ ...formData, scan_frequency: e.target.value })}
                  style={{ width: '100%' }}
                >
                  <option value="on_push">On Push</option>
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="manual">Manual Only</option>
                </select>
              </div>
            </>
          )}
          <div style={{ marginBottom: '1rem' }}>
            <ScannerSelection
              availableScanners={availableScanners}
              selectedScanners={formData.scanners}
              onSelectionChange={(scanners) => onFormDataChange({ ...formData, scanners })}
            />
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
            <button type="button" onClick={onClose}>Cancel</button>
            <button type="submit" className="primary">Update</button>
          </div>
        </form>
      </div>
    </div>
  )
}
