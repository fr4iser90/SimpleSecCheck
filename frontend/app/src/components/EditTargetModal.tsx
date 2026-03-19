import { useState, useEffect } from 'react'
import Modal from './Modal'
import type { ScanTargetItem, AutoScanConfig } from '../hooks/useTargets'

interface EditTargetModalProps {
  isOpen: boolean
  target: ScanTargetItem | null
  onClose: () => void
  onSubmit: (targetId: string, payload: {
    display_name?: string
    config?: Record<string, unknown>
    auto_scan?: AutoScanConfig
  }) => Promise<void>
}

export default function EditTargetModal({
  isOpen,
  target,
  onClose,
  onSubmit,
}: EditTargetModalProps) {
  const [displayName, setDisplayName] = useState('')
  const [branch, setBranch] = useState('main')
  const [tag, setTag] = useState('latest')
  const [autoScanEnabled, setAutoScanEnabled] = useState(false)
  const [intervalSeconds, setIntervalSeconds] = useState('21600')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (target && isOpen) {
      setDisplayName(target.display_name ?? '')
      setBranch(target.type === 'git_repo' ? String(target.config?.branch ?? 'main') : 'main')
      setTag(target.type === 'container_registry' ? String(target.config?.tag ?? 'latest') : 'latest')
      setAutoScanEnabled(target.auto_scan?.enabled ?? false)
      setIntervalSeconds(String(target.auto_scan?.interval_seconds ?? 21600))
    }
  }, [target, isOpen])

  if (!target) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSaving(true)
    try {
      const config: Record<string, unknown> = { ...target.config }
      if (target.type === 'git_repo') config.branch = branch
      if (target.type === 'container_registry') config.tag = tag
      await onSubmit(target.id, {
        display_name: displayName.trim() || undefined,
        config,
        auto_scan: {
          enabled: autoScanEnabled,
          mode: 'interval',
          interval_seconds: autoScanEnabled ? parseInt(intervalSeconds, 10) || 21600 : undefined,
          event: target.auto_scan?.event ?? null,
        },
      })
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Edit target">
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1rem' }}>
        {target.source}
      </p>
      {error && (
        <p style={{ color: 'var(--color-critical)', marginBottom: '1rem' }}>{error}</p>
      )}
      <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.35rem' }}>Display name</label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              style={{ width: '100%', padding: '0.5rem' }}
            />
          </div>
          {target.type === 'git_repo' && (
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.35rem' }}>Branch</label>
              <input
                type="text"
                value={branch}
                onChange={(e) => setBranch(e.target.value)}
                style={{ width: '100%', padding: '0.5rem' }}
              />
            </div>
          )}
          {target.type === 'container_registry' && (
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.35rem' }}>Tag</label>
              <input
                type="text"
                value={tag}
                onChange={(e) => setTag(e.target.value)}
                style={{ width: '100%', padding: '0.5rem' }}
              />
            </div>
          )}
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <input
                type="checkbox"
                checked={autoScanEnabled}
                onChange={(e) => setAutoScanEnabled(e.target.checked)}
              />
              Auto-scan (interval)
            </label>
          </div>
          {autoScanEnabled && (
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.35rem' }}>Interval (seconds)</label>
              <input
                type="number"
                value={intervalSeconds}
                onChange={(e) => setIntervalSeconds(e.target.value)}
                min={60}
                style={{ width: '100%', padding: '0.5rem' }}
              />
            </div>
          )}
          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
            <button type="button" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="primary" disabled={saving}>
              {saving ? 'Saving…' : 'Save'}
            </button>
          </div>
        </form>
    </Modal>
  )
}
