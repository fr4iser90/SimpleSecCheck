import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { apiFetch } from '../utils/apiClient'

interface QueueOverviewItem {
  position?: number
  scan_id: string
  name: string
  target: string
  priority: number
  created_at?: string
  started_at?: string
  estimated_time_seconds?: number | null
}

interface QueueOverview {
  pending_count: number
  running_count: number
  redis_queue_length: number
  running: QueueOverviewItem[]
  next_pending: QueueOverviewItem[]
}

interface QueueConfig {
  queue_strategy: string
  priority_admin: number
  priority_user: number
  priority_guest: number
}

const STRATEGIES = [
  { value: 'fifo', label: 'FIFO', description: 'First in, first out. Simple and predictable.' },
  {
    value: 'priority',
    label: 'Priority',
    description: 'Higher priority scans first (admin > user > guest by default).',
  },
  {
    value: 'round_robin',
    label: 'Round Robin',
    description: 'Fair share: alternate between users so no one hogs the queue.',
  },
] as const

export default function ExecutionSettingsPage() {
  const { isAuthenticated, user } = useAuth()
  const isAdmin = user?.role === 'admin'

  const [maxConcurrentJobs, setMaxConcurrentJobs] = useState(3)
  const [jobsLoading, setJobsLoading] = useState(true)
  const [jobsSaving, setJobsSaving] = useState(false)
  const [jobsSuccess, setJobsSuccess] = useState<string | null>(null)

  const [queueConfig, setQueueConfig] = useState<QueueConfig>({
    queue_strategy: 'fifo',
    priority_admin: 10,
    priority_user: 5,
    priority_guest: 1,
  })
  const [queueLoading, setQueueLoading] = useState(true)
  const [queueSaving, setQueueSaving] = useState(false)
  const [queueSuccess, setQueueSuccess] = useState<string | null>(null)

  const [error, setError] = useState<string | null>(null)
  const [overview, setOverview] = useState<QueueOverview | null>(null)
  const [overviewError, setOverviewError] = useState<string | null>(null)

  const [enforceLoading, setEnforceLoading] = useState(true)
  const [enforceSaving, setEnforceSaving] = useState(false)
  const [enforceSuccess, setEnforceSuccess] = useState<string | null>(null)
  const [enforceForm, setEnforceForm] = useState({
    max_scans_per_hour_global: '',
    max_scans_per_hour_per_user: '',
    max_scans_per_hour_per_guest_session: '',
    max_concurrent_scans_per_user: '',
    max_concurrent_scans_per_guest: '',
    max_scan_duration_seconds: '3600',
    initial_scan_delay_seconds: '300',
    rate_limit_admins: false,
  })

  const [scanDefaultsLoading, setScanDefaultsLoading] = useState(true)
  const [scanDefaultsSaving, setScanDefaultsSaving] = useState(false)
  const [scanDefaultsSuccess, setScanDefaultsSuccess] = useState<string | null>(null)
  const [scanDefaultsForm, setScanDefaultsForm] = useState({
    default_finding_policy_path: '.scanning/finding-policy.json',
    finding_policy_apply_by_default: true,
  })

  const loadOverview = useCallback(async () => {
    try {
      setOverviewError(null)
      const r = await apiFetch('/api/admin/execution/queue-overview')
      if (!r.ok) throw new Error('Queue overview failed')
      setOverview(await r.json())
    } catch (e: unknown) {
      setOverviewError(e instanceof Error ? e.message : 'Overview failed')
    }
  }, [])

  const loadEnforcement = async () => {
    try {
      setEnforceLoading(true)
      const r = await apiFetch('/api/admin/config/scan-enforcement')
      if (!r.ok) throw new Error('Failed to load scan limits')
      const data = await r.json()
      const el = data.execution_limits || {}
      const numOrEmpty = (v: unknown) =>
        v != null && v !== '' && Number.isFinite(Number(v)) ? String(v) : ''
      setEnforceForm({
        max_scans_per_hour_global: numOrEmpty(el.max_scans_per_hour_global),
        max_scans_per_hour_per_user: numOrEmpty(el.max_scans_per_hour_per_user),
        max_scans_per_hour_per_guest_session: numOrEmpty(el.max_scans_per_hour_per_guest_session),
        max_concurrent_scans_per_user: numOrEmpty(el.max_concurrent_scans_per_user),
        max_concurrent_scans_per_guest: numOrEmpty(el.max_concurrent_scans_per_guest),
        max_scan_duration_seconds: String(
          Number.isFinite(Number(el.max_scan_duration_seconds))
            ? el.max_scan_duration_seconds
            : 3600,
        ),
        initial_scan_delay_seconds: numOrEmpty(el.initial_scan_delay_seconds) || '300',
        rate_limit_admins: Boolean(el.rate_limit_admins),
      })
    } catch {
      /* non-fatal */
    } finally {
      setEnforceLoading(false)
    }
  }

  const loadScanDefaults = async () => {
    try {
      setScanDefaultsLoading(true)
      const r = await apiFetch('/api/admin/config/scan-defaults')
      if (!r.ok) throw new Error('Failed to load scan defaults')
      const data = await r.json()
      setScanDefaultsForm({
        default_finding_policy_path: data.default_finding_policy_path ?? '.scanning/finding-policy.json',
        finding_policy_apply_by_default: data.finding_policy_apply_by_default ?? true,
      })
    } catch {
      /* non-fatal */
    } finally {
      setScanDefaultsLoading(false)
    }
  }

  useEffect(() => {
    if (!isAuthenticated) return
    void loadJobs()
    void loadQueue()
    void loadEnforcement()
    void loadScanDefaults()
  }, [isAuthenticated])

  useEffect(() => {
    if (!isAuthenticated || !isAdmin) return
    void loadOverview()
    const t = setInterval(loadOverview, 10000)
    return () => clearInterval(t)
  }, [isAuthenticated, isAdmin, loadOverview])

  const loadJobs = async () => {
    try {
      setJobsLoading(true)
      setError(null)
      const response = await apiFetch('/api/admin/config')
      if (!response.ok) throw new Error('Failed to load execution config')
      const data = await response.json()
      const n = Number(data.max_concurrent_jobs)
      setMaxConcurrentJobs(Number.isFinite(n) ? Math.min(50, Math.max(1, n)) : 3)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load parallel scan limit')
    } finally {
      setJobsLoading(false)
    }
  }

  const loadQueue = async () => {
    try {
      setQueueLoading(true)
      setError(null)
      const response = await apiFetch('/api/admin/config/queue')
      if (!response.ok) throw new Error('Failed to load queue configuration')
      const data = await response.json()
      setQueueConfig(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load queue configuration')
    } finally {
      setQueueLoading(false)
    }
  }

  const saveJobs = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setJobsSuccess(null)
    setJobsSaving(true)
    try {
      const response = await apiFetch('/api/admin/config/worker-jobs', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ max_concurrent_jobs: maxConcurrentJobs }),
      })
      if (!response.ok) {
        const err = await response.json().catch(() => ({}))
        throw new Error(err.detail || 'Failed to save')
      }
      setJobsSuccess(
        'Saved. Restart the worker container for this to take effect unless MAX_CONCURRENT_JOBS is set in the environment (env overrides DB).',
      )
      await loadJobs()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setJobsSaving(false)
    }
  }

  const saveQueue = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setQueueSuccess(null)
    setQueueSaving(true)
    try {
      const response = await apiFetch('/api/admin/config/queue', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(queueConfig),
      })
      if (!response.ok) {
        const err = await response.json().catch(() => ({}))
        throw new Error(err.detail || 'Failed to save queue configuration')
      }
      setQueueSuccess('Queue settings saved. Worker uses the new strategy on next dequeue.')
      await loadQueue()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setQueueSaving(false)
    }
  }

  const parseLimit = (s: string): number | null => {
    const t = s.trim()
    if (!t) return null
    const n = parseInt(t, 10)
    return Number.isFinite(n) && n > 0 ? n : null
  }

  const saveEnforcement = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setEnforceSuccess(null)
    setEnforceSaving(true)
    try {
      const maxWall = parseInt(enforceForm.max_scan_duration_seconds, 10)
      if (!Number.isFinite(maxWall) || maxWall < 300 || maxWall > 86400) {
        throw new Error('Max scan duration must be 300–86400 seconds')
      }
      const delaySec = parseInt(enforceForm.initial_scan_delay_seconds, 10)
      if (!Number.isFinite(delaySec) || delaySec < 0 || delaySec > 86400) {
        throw new Error('Initial scan delay must be 0–86400 seconds (0 = as soon as scheduler runs)')
      }
      const execution_limits = {
        max_scans_per_hour_global: parseLimit(enforceForm.max_scans_per_hour_global),
        max_scans_per_hour_per_user: parseLimit(enforceForm.max_scans_per_hour_per_user),
        max_scans_per_hour_per_guest_session: parseLimit(
          enforceForm.max_scans_per_hour_per_guest_session,
        ),
        max_concurrent_scans_per_user: parseLimit(enforceForm.max_concurrent_scans_per_user),
        max_concurrent_scans_per_guest: parseLimit(enforceForm.max_concurrent_scans_per_guest),
        max_scan_duration_seconds: maxWall,
        initial_scan_delay_seconds: delaySec,
        rate_limit_admins: enforceForm.rate_limit_admins,
      }
      const response = await apiFetch('/api/admin/config/scan-enforcement', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ execution_limits }),
      })
      if (!response.ok) {
        const err = await response.json().catch(() => ({}))
        throw new Error((err as { detail?: string }).detail || 'Failed to save')
      }
      setEnforceSuccess(
        'Saved. Rate limits apply on new scan submissions. Max duration applies to new queue jobs (worker wall-clock wait).',
      )
      await loadEnforcement()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setEnforceSaving(false)
    }
  }

  const saveScanDefaults = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setScanDefaultsSuccess(null)
    setScanDefaultsSaving(true)
    try {
      const r = await apiFetch('/api/admin/config/scan-defaults', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(scanDefaultsForm),
      })
      if (!r.ok) {
        const err = await r.json().catch(() => ({}))
        throw new Error((err as { detail?: string }).detail || 'Failed to save')
      }
      setScanDefaultsSuccess('Saved. New scans will use this default for the Finding Policy field.')
      await loadScanDefaults()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save scan defaults')
    } finally {
      setScanDefaultsSaving(false)
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

  const loading = jobsLoading || queueLoading

  if (loading) {
    return (
      <div className="admin-settings-page">
        <div className="admin-settings-container">
          <div className="loading">Loading execution settings…</div>
        </div>
      </div>
    )
  }

  return (
    <div className="admin-settings-page">
      <div className="admin-settings-container">
        <h2>Execution</h2>
        <p className="section-description" style={{ marginBottom: '1rem' }}>
          Control <strong>how many scans run at once</strong> and <strong>how the queue is ordered</strong>.
          Per-tool timeouts: <Link to="/admin/tool-settings">Tool settings</Link>. Workers &amp; assets:{' '}
          <Link to="/admin/scanner">Scan Engine</Link>.
        </p>

        <div
          className="settings-section"
          style={{
            marginBottom: '2rem',
            padding: '1.25rem',
            border: '1px solid var(--glass-border-main)',
            borderRadius: 12,
            background: 'var(--glass-bg-main)',
          }}
        >
          <h3 style={{ marginTop: 0 }}>Live queue</h3>
          <p className="section-description" style={{ marginBottom: '0.75rem' }}>
            Running jobs, next pending (by priority → created time). Redis length = worker job queue. Updates
            every 10s.
          </p>
          {overviewError && <div className="error-message" style={{ marginBottom: '0.5rem' }}>{overviewError}</div>}
          {overview && (
            <>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem' }}>
                <span>
                  <strong>Pending (DB)</strong>: {overview.pending_count}
                </span>
                <span>
                  <strong>Running</strong>: {overview.running_count}
                </span>
                <span>
                  <strong>Redis jobs</strong>: {overview.redis_queue_length}
                </span>
              </div>
              <h4 style={{ margin: '1rem 0 0.5rem', fontSize: '1rem' }}>Running now</h4>
              {overview.running.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>None</p>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', fontSize: '0.85rem', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--glass-border-main)' }}>
                        <th style={{ padding: '0.35rem' }}>Scan</th>
                        <th style={{ padding: '0.35rem' }}>Target</th>
                        <th style={{ padding: '0.35rem' }}>Pri</th>
                        <th style={{ padding: '0.35rem' }}>Started</th>
                      </tr>
                    </thead>
                    <tbody>
                      {overview.running.map((row) => (
                        <tr key={row.scan_id} style={{ borderBottom: '1px solid var(--glass-border-main)' }}>
                          <td style={{ padding: '0.35rem' }}>
                            <Link to="/scan" state={{ scan_id: row.scan_id }}>
                              {row.name || row.scan_id.slice(0, 8)}
                            </Link>
                          </td>
                          <td style={{ padding: '0.35rem', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {row.target || '—'}
                          </td>
                          <td style={{ padding: '0.35rem' }}>{row.priority}</td>
                          <td style={{ padding: '0.35rem', whiteSpace: 'nowrap' }}>
                            {row.started_at ? new Date(row.started_at).toLocaleString() : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <h4 style={{ margin: '1rem 0 0.5rem', fontSize: '1rem' }}>Next in queue (pending)</h4>
              {overview.next_pending.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Queue empty</p>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', fontSize: '0.85rem', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--glass-border-main)' }}>
                        <th style={{ padding: '0.35rem' }}>#</th>
                        <th style={{ padding: '0.35rem' }}>Scan</th>
                        <th style={{ padding: '0.35rem' }}>Target</th>
                        <th style={{ padding: '0.35rem' }}>Pri</th>
                        <th style={{ padding: '0.35rem' }}>Est.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {overview.next_pending.map((row) => (
                        <tr key={row.scan_id} style={{ borderBottom: '1px solid var(--glass-border-main)' }}>
                          <td style={{ padding: '0.35rem' }}>{row.position}</td>
                          <td style={{ padding: '0.35rem' }}>
                            <Link to="/scan" state={{ scan_id: row.scan_id }}>
                              {row.name || row.scan_id.slice(0, 8)}
                            </Link>
                          </td>
                          <td style={{ padding: '0.35rem', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {row.target || '—'}
                          </td>
                          <td style={{ padding: '0.35rem' }}>{row.priority}</td>
                          <td style={{ padding: '0.35rem', whiteSpace: 'nowrap' }}>
                            {row.estimated_time_seconds != null
                              ? `${Math.round(row.estimated_time_seconds / 60)}m`
                              : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <button type="button" className="btn-secondary" style={{ marginTop: '0.75rem' }} onClick={() => void loadOverview()}>
                Refresh queue
              </button>
            </>
          )}
        </div>

        {error && (
          <div className="error-message" role="alert">
            {error}
          </div>
        )}

        <form onSubmit={saveJobs} className="settings-form" style={{ marginBottom: '2.5rem' }}>
          <div className="settings-section">
            <h3>Parallel scans</h3>
            <p className="section-description">
              Maximum number of <strong>complete</strong> scan jobs the worker runs at the same time. Additional
              scans wait in the queue.
            </p>
            <div className="form-group">
              <label htmlFor="max_concurrent_jobs">Max concurrent scan jobs</label>
              <input
                id="max_concurrent_jobs"
                type="number"
                min={1}
                max={50}
                value={maxConcurrentJobs}
                onChange={(e) => setMaxConcurrentJobs(parseInt(e.target.value, 10) || 1)}
              />
              <small style={{ display: 'block', marginTop: '0.35rem', color: 'var(--text-secondary)' }}>
                Range 1–50. Same value as in setup wizard; change here anytime.
              </small>
            </div>
            {jobsSuccess && (
              <div className="success-message" role="status" style={{ marginTop: '0.75rem' }}>
                {jobsSuccess}
              </div>
            )}
            <div style={{ marginTop: '1rem' }}>
              <button type="submit" className="btn-primary" disabled={jobsSaving}>
                {jobsSaving ? 'Saving…' : 'Save parallel scans'}
              </button>
            </div>
          </div>
        </form>

        <form onSubmit={saveQueue} className="settings-form">
          <div className="settings-section">
            <h3>Queue &amp; scan order</h3>
            <p className="section-description">
              How the worker picks the next job when a slot frees up.
            </p>
            <div className="form-group">
              <label htmlFor="queue_strategy">Strategy</label>
              <select
                id="queue_strategy"
                name="queue_strategy"
                value={queueConfig.queue_strategy}
                onChange={(e) =>
                  setQueueConfig((prev) => ({ ...prev, queue_strategy: e.target.value }))
                }
              >
                {STRATEGIES.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
              <small style={{ display: 'block', marginTop: '0.35rem', color: 'var(--text-secondary)' }}>
                {STRATEGIES.find((s) => s.value === queueConfig.queue_strategy)?.description}
              </small>
            </div>
          </div>
          <div className="settings-section">
            <h3>Priority by role</h3>
            <p className="section-description" style={{ marginBottom: '0.75rem' }}>
              Used when strategy is <strong>Priority</strong>. Higher number = earlier in queue.
            </p>
            <div className="form-group">
              <label htmlFor="priority_admin">Admin priority</label>
              <input
                id="priority_admin"
                type="number"
                min={0}
                max={1000}
                value={queueConfig.priority_admin}
                onChange={(e) =>
                  setQueueConfig((prev) => ({
                    ...prev,
                    priority_admin: parseInt(e.target.value, 10) || 0,
                  }))
                }
              />
            </div>
            <div className="form-group">
              <label htmlFor="priority_user">User priority</label>
              <input
                id="priority_user"
                type="number"
                min={0}
                max={1000}
                value={queueConfig.priority_user}
                onChange={(e) =>
                  setQueueConfig((prev) => ({
                    ...prev,
                    priority_user: parseInt(e.target.value, 10) || 0,
                  }))
                }
              />
            </div>
            <div className="form-group">
              <label htmlFor="priority_guest">Guest priority</label>
              <input
                id="priority_guest"
                type="number"
                min={0}
                max={1000}
                value={queueConfig.priority_guest}
                onChange={(e) =>
                  setQueueConfig((prev) => ({
                    ...prev,
                    priority_guest: parseInt(e.target.value, 10) || 0,
                  }))
                }
              />
            </div>
            {queueSuccess && (
              <div className="success-message" role="status" style={{ marginTop: '0.75rem' }}>
                {queueSuccess}
              </div>
            )}
            <div style={{ marginTop: '1rem' }}>
              <button type="submit" className="btn-primary" disabled={queueSaving}>
                {queueSaving ? 'Saving…' : 'Save queue settings'}
              </button>
            </div>
          </div>
        </form>

        <div
          className="settings-section"
          style={{
            marginTop: '2rem',
            padding: '1.25rem',
            border: '1px solid var(--glass-border-main)',
            borderRadius: 12,
            background: 'var(--glass-bg-main)',
          }}
        >
          <h3 style={{ marginTop: 0 }}>Enforced limits</h3>
          <p className="section-description" style={{ marginBottom: '1rem' }}>
            Hard limits on <strong>new</strong> scans (API). Empty = no limit. Admins are exempt from rate limits
            unless &quot;Rate-limit admins&quot; is checked. Target blocking lives under{' '}
            <Link to="/admin/policies">Security policies</Link>.
          </p>
          {enforceLoading ? (
            <p style={{ color: 'var(--text-secondary)' }}>Loading…</p>
          ) : (
            <form onSubmit={saveEnforcement} className="settings-form">
              <div className="form-group">
                <label>Max scans / hour (global)</label>
                <input
                  type="number"
                  min={1}
                  placeholder="unlimited"
                  value={enforceForm.max_scans_per_hour_global}
                  onChange={(e) =>
                    setEnforceForm((p) => ({ ...p, max_scans_per_hour_global: e.target.value }))
                  }
                />
              </div>
              <div className="form-group">
                <label>Max scans / hour (per logged-in user)</label>
                <input
                  type="number"
                  min={1}
                  placeholder="unlimited"
                  value={enforceForm.max_scans_per_hour_per_user}
                  onChange={(e) =>
                    setEnforceForm((p) => ({ ...p, max_scans_per_hour_per_user: e.target.value }))
                  }
                />
              </div>
              <div className="form-group">
                <label>Max scans / hour (per guest session)</label>
                <input
                  type="number"
                  min={1}
                  placeholder="unlimited"
                  value={enforceForm.max_scans_per_hour_per_guest_session}
                  onChange={(e) =>
                    setEnforceForm((p) => ({
                      ...p,
                      max_scans_per_hour_per_guest_session: e.target.value,
                    }))
                  }
                />
              </div>
              <div className="form-group">
                <label>Max concurrent scans (per user)</label>
                <input
                  type="number"
                  min={1}
                  placeholder="unlimited"
                  value={enforceForm.max_concurrent_scans_per_user}
                  onChange={(e) =>
                    setEnforceForm((p) => ({ ...p, max_concurrent_scans_per_user: e.target.value }))
                  }
                />
              </div>
              <div className="form-group">
                <label>Max concurrent scans (per guest session)</label>
                <input
                  type="number"
                  min={1}
                  placeholder="unlimited"
                  value={enforceForm.max_concurrent_scans_per_guest}
                  onChange={(e) =>
                    setEnforceForm((p) => ({ ...p, max_concurrent_scans_per_guest: e.target.value }))
                  }
                />
              </div>
              <div className="form-group">
                <label>Max scan wall time (seconds)</label>
                <input
                  type="number"
                  min={300}
                  max={86400}
                  value={enforceForm.max_scan_duration_seconds}
                  onChange={(e) =>
                    setEnforceForm((p) => ({ ...p, max_scan_duration_seconds: e.target.value }))
                  }
                />
                <small style={{ display: 'block', marginTop: '0.35rem', color: 'var(--text-secondary)' }}>
                  Worker stops the scanner container after this many seconds (300–86400). New jobs only.
                </small>
              </div>
              <div className="form-group">
                <label>Initial scan delay (seconds)</label>
                <input
                  type="number"
                  min={0}
                  max={86400}
                  value={enforceForm.initial_scan_delay_seconds}
                  onChange={(e) =>
                    setEnforceForm((p) => ({ ...p, initial_scan_delay_seconds: e.target.value }))
                  }
                />
                <small style={{ display: 'block', marginTop: '0.35rem', color: 'var(--text-secondary)' }}>
                  Delay before the first scan is auto-queued for new targets (0–86400). Default 300 (5 min). Users can pause per target.
                </small>
              </div>
              <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input
                  id="rate_limit_admins"
                  type="checkbox"
                  checked={enforceForm.rate_limit_admins}
                  onChange={(e) =>
                    setEnforceForm((p) => ({ ...p, rate_limit_admins: e.target.checked }))
                  }
                />
                <label htmlFor="rate_limit_admins" style={{ margin: 0 }}>
                  Apply hourly / concurrent limits to admins too
                </label>
              </div>
              {enforceSuccess && (
                <div className="success-message" role="status" style={{ marginTop: '0.75rem' }}>
                  {enforceSuccess}
                </div>
              )}
              <div style={{ marginTop: '1rem' }}>
                <button type="submit" className="btn-primary" disabled={enforceSaving}>
                  {enforceSaving ? 'Saving…' : 'Save enforcement limits'}
                </button>
              </div>
            </form>
          )}
        </div>

        <div
          className="settings-section"
          style={{
            marginTop: '2rem',
            padding: '1.25rem',
            border: '1px solid var(--glass-border-main)',
            borderRadius: 12,
            background: 'var(--glass-bg-main)',
          }}
        >
          <h3 style={{ marginTop: 0 }}>Scan form defaults (Finding Policy)</h3>
          <p className="section-description" style={{ marginBottom: '1rem' }}>
            When users start a scan, the &quot;Finding Policy (optional)&quot; field can be pre-filled so the policy
            is applied automatically. Set the default path and whether to apply it by default.
          </p>
          {scanDefaultsLoading ? (
            <p style={{ color: 'var(--text-secondary)' }}>Loading…</p>
          ) : (
            <form onSubmit={saveScanDefaults} className="settings-form">
              <div className="form-group">
                <label htmlFor="default_finding_policy_path">Default finding policy path</label>
                <input
                  id="default_finding_policy_path"
                  type="text"
                  value={scanDefaultsForm.default_finding_policy_path}
                  onChange={(e) =>
                    setScanDefaultsForm((p) => ({
                      ...p,
                      default_finding_policy_path: e.target.value,
                    }))
                  }
                  placeholder=".scanning/finding-policy.json"
                />
                <small style={{ display: 'block', marginTop: '0.35rem', color: 'var(--text-secondary)' }}>
                  Relative path in the repo (e.g. .scanning/finding-policy.json). Used when &quot;Apply by default&quot; is on.
                </small>
              </div>
              <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input
                  id="finding_policy_apply_by_default"
                  type="checkbox"
                  checked={scanDefaultsForm.finding_policy_apply_by_default}
                  onChange={(e) =>
                    setScanDefaultsForm((p) => ({
                      ...p,
                      finding_policy_apply_by_default: e.target.checked,
                    }))
                  }
                />
                <label htmlFor="finding_policy_apply_by_default" style={{ margin: 0 }}>
                  Apply finding policy by default (pre-fill and send path in new scans)
                </label>
              </div>
              {scanDefaultsSuccess && (
                <div className="success-message" role="status" style={{ marginTop: '0.75rem' }}>
                  {scanDefaultsSuccess}
                </div>
              )}
              <div style={{ marginTop: '1rem' }}>
                <button type="submit" className="btn-primary" disabled={scanDefaultsSaving}>
                  {scanDefaultsSaving ? 'Saving…' : 'Save scan form defaults'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
