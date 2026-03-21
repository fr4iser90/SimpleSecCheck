import Modal from './Modal'
import type { AddTargetPayload } from '../utils/targetDuplicate'
import type { ScanTargetItem } from '../hooks/useTargets'

interface DuplicateTargetModalProps {
  isOpen: boolean
  onClose: () => void
  payload: AddTargetPayload | null
  existing: ScanTargetItem | null
  onEdit: () => void
  onReplace: () => void
}

export default function DuplicateTargetModal({
  isOpen,
  onClose,
  payload,
  existing,
  onEdit,
  onReplace,
}: DuplicateTargetModalProps) {
  if (!payload) return null

  const label = existing?.display_name || existing?.source || payload.source

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Target already exists">
      <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
        This URL or source is already saved as a target. You can open the existing target to edit it, replace it
        with what you just entered (removes the old entry and adds the new one), or cancel.
      </p>
      <div
        style={{
          padding: '0.75rem 1rem',
          borderRadius: '8px',
          background: 'var(--glass-border-main)',
          marginBottom: '1.25rem',
          fontSize: '0.9rem',
          wordBreak: 'break-all',
        }}
      >
        <strong>{label}</strong>
        <div style={{ color: 'var(--text-secondary)', marginTop: '0.35rem' }}>{payload.source}</div>
      </div>
      <p style={{ fontSize: '0.85rem', color: 'var(--color-warning, #fd7e14)', marginBottom: '1rem' }}>
        Replace deletes the existing target and creates a new one with your form data (scan history for the old
        target id is not migrated).
      </p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', justifyContent: 'flex-end' }}>
        <button type="button" onClick={onClose}>
          Cancel
        </button>
        {existing && (
          <button type="button" onClick={onEdit}>
            Edit existing
          </button>
        )}
        <button type="button" className="primary" onClick={onReplace} disabled={!existing}>
          Replace target
        </button>
      </div>
    </Modal>
  )
}
