import { useState, useEffect } from 'react'
import { useAuth } from '../hooks/useAuth'
import { apiFetch } from '../utils/apiClient'

interface QueueConfig {
  queue_strategy: string
  priority_admin: number
  priority_user: number
  priority_guest: number
}

const STRATEGIES = [
  { value: 'fifo', label: 'FIFO', description: 'First in, first out. Simple and predictable.' },
  { value: 'priority', label: 'Priority', description: 'Higher priority scans first (admin > user > guest by default).' },
  { value: 'round_robin', label: 'Round Robin', description: 'Fair share: alternate between users so no one hogs the queue.' },
] as const

export default function QueueSettingsPage() {
  const { isAuthenticated, user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [config, setConfig] = useState<QueueConfig>({
    queue_strategy: 'fifo',
    priority_admin: 10,
    priority_user: 5,
    priority_guest: 1,
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    if (!isAuthenticated) return
    loadConfig()
  }, [isAuthenticated])

  const loadConfig = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await apiFetch('/api/admin/config/queue')
      if (!response.ok) throw new Error('Failed to load queue configuration')
      const data = await response.json()
      setConfig(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load queue configuration')
    } finally {
      setLoading(false)
    }
  }

  const handleStrategyChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setConfig((prev) => ({ ...prev, queue_strategy: e.target.value }))
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    setSaving(true)
    try {
      const response = await apiFetch('/api/admin/config/queue', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })
      if (!response.ok) {
        const err = await response.json().catch(() => ({}))
        throw new Error(err.detail || 'Failed to save queue configuration')
      }
      setSuccess('Queue configuration saved. Worker will use the new strategy on next dequeue.')
      await loadConfig()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  if (!isAuthenticated || !isAdmin) {
    return (
      <div className="admin-settings-page">
        <div className="admin-settings-container">
          <h2>Access Denied</h2>
          <p>You must be logged in as an admin to access this page.</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="admin-settings-page">
        <div className="admin-settings-container">
          <div className="loading">Loading queue configuration...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="admin-settings-page">
      <div className="admin-settings-container">
        <h2>Queue &amp; Scan Order</h2>
        <p className="section-description" style={{ marginBottom: '1.5rem' }}>
          Choose how the worker picks the next scan from the queue. Default priorities (admin / user / guest) are used when strategy is Priority.
        </p>
        {error && <div className="error-message" role="alert">{error}</div>}
        {success && <div className="success-message" role="alert">{success}</div>}
        <form onSubmit={handleSave} className="settings-form">
          <div className="settings-section">
            <h3>Queue strategy</h3>
            <div className="form-group">
              <label htmlFor="queue_strategy">Strategy</label>
              <select
                id="queue_strategy"
                name="queue_strategy"
                value={config.queue_strategy}
                onChange={handleStrategyChange}
              >
                {STRATEGIES.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
              <small style={{ display: 'block', marginTop: '0.35rem', color: 'var(--text-secondary)' }}>
                {STRATEGIES.find((s) => s.value === config.queue_strategy)?.description}
              </small>
            </div>
          </div>
          <div className="settings-section">
            <h3>Default priority by role (used when strategy is Priority)</h3>
            <p className="section-description" style={{ marginBottom: '0.75rem' }}>
              Higher number = earlier in queue. Admin scans run before user scans, user before guest.
            </p>
            <div className="form-group">
              <label>Admin: {config.priority_admin} · User: {config.priority_user} · Guest: {config.priority_guest}</label>
              <small style={{ display: 'block', marginTop: '0.25rem', color: 'var(--text-secondary)' }}>
                To change these, use the API or add inputs here later.
              </small>
            </div>
          </div>
          <div style={{ marginTop: '1.5rem' }}>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Saving...' : 'Save queue configuration'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
