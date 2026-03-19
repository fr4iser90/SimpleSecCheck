import { useState } from 'react'
import Modal from './Modal'
import type { AutoScanConfig } from '../hooks/useTargets'

interface AddTargetModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (payload: {
    type: string
    source: string
    display_name?: string
    config: Record<string, unknown>
    auto_scan: AutoScanConfig
  }) => Promise<void>
  allowedTargets: Record<string, boolean> | null
}

const TARGET_OPTIONS: { value: string; label: string }[] = [
  { value: 'git_repo', label: 'Git repository' },
  { value: 'container_registry', label: 'Container image' },
  { value: 'local_mount', label: 'Local path' },
]

export default function AddTargetModal({
  isOpen,
  onClose,
  onSubmit,
  allowedTargets,
}: AddTargetModalProps) {
  const [type, setType] = useState('git_repo')
  const [source, setSource] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [branch, setBranch] = useState('main')
  const [tag, setTag] = useState('latest')
  const [autoScanEnabled, setAutoScanEnabled] = useState(false)
  const [intervalSeconds, setIntervalSeconds] = useState('21600')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const allowed = allowedTargets || {}
  const isAllowed = (apiKey: string) => {
    if (apiKey === 'git_repo') return allowed['git_repos'] !== false
    if (apiKey === 'local_mount') return allowed['local_paths'] !== false
    return allowed[apiKey] !== false
  }
  const options = TARGET_OPTIONS.filter((o) => isAllowed(o.value))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSaving(true)
    try {
      const config: Record<string, unknown> = {}
      if (type === 'git_repo') config.branch = branch
      if (type === 'container_registry') config.tag = tag

      await onSubmit({
        type,
        source: source.trim(),
        display_name: displayName.trim() || undefined,
        config,
        auto_scan: {
          enabled: autoScanEnabled,
          mode: 'interval',
          interval_seconds: autoScanEnabled ? parseInt(intervalSeconds, 10) || 21600 : undefined,
          event: null,
        },
      })
      setSource('')
      setDisplayName('')
      setBranch('main')
      setTag('latest')
      setAutoScanEnabled(false)
      setIntervalSeconds('21600')
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add target')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Add target">
      {error && (
        <p style={{ color: 'var(--color-critical)', marginBottom: '1rem' }}>{error}</p>
      )}
      <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.35rem' }}>Type</label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              style={{ width: '100%', padding: '0.5rem' }}
            >
              {options.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.35rem' }}>
              {type === 'git_repo' && 'Repository URL'}
              {type === 'container_registry' && 'Image (e.g. nginx:latest)'}
              {type === 'local_mount' && 'Absolute path'}
            </label>
            <input
              type="text"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder={
                type === 'git_repo'
                  ? 'https://github.com/user/repo'
                  : type === 'container_registry'
                    ? 'nginx:latest'
                    : '/path/to/project'
              }
              required
              style={{ width: '100%', padding: '0.5rem' }}
            />
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.35rem' }}>Display name (optional)</label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="My backend repo"
              style={{ width: '100%', padding: '0.5rem' }}
            />
          </div>
          {type === 'git_repo' && (
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
          {type === 'container_registry' && (
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
              <small style={{ color: 'var(--text-secondary)' }}>e.g. 21600 = 6 hours</small>
            </div>
          )}
          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
            <button type="button" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="primary" disabled={saving}>
              {saving ? 'Adding…' : 'Add target'}
            </button>
          </div>
        </form>
    </Modal>
  )
}
