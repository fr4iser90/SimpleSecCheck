/**
 * Shared modal wrapper: one consistent, readable style for all modals.
 * Overlay (dark + blur) + content box (opaque dark, good contrast).
 */
import type { ReactNode } from 'react'

const OVERLAY_STYLE: React.CSSProperties = {
  position: 'fixed',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  background: 'var(--modal-overlay-bg)',
  backdropFilter: 'blur(8px)',
  WebkitBackdropFilter: 'blur(8px)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 1000,
}

const CONTENT_BASE: React.CSSProperties = {
  background: 'var(--modal-content-bg)',
  backdropFilter: 'blur(20px)',
  WebkitBackdropFilter: 'blur(20px)',
  padding: '2rem',
  borderRadius: '8px',
  maxHeight: '90vh',
  overflow: 'auto',
  border: '1px solid var(--glass-border-main)',
  boxShadow: 'var(--shadow-main)',
}

export interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  /** 'sm' = 480px (forms), 'lg' = 800px (lists) */
  size?: 'sm' | 'lg'
  children: ReactNode
}

export default function Modal({ isOpen, onClose, title, size = 'sm', children }: ModalProps) {
  if (!isOpen) return null

  const maxWidth = size === 'lg' ? '800px' : '480px'

  return (
    <div
      style={OVERLAY_STYLE}
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? 'modal-title' : undefined}
    >
      <div
        style={{
          ...CONTENT_BASE,
          width: '90%',
          maxWidth,
          margin: '1rem',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {title != null && (
          <h2 id="modal-title" style={{ marginTop: 0, marginBottom: '1rem' }}>
            {title}
          </h2>
        )}
        {children}
      </div>
    </div>
  )
}
