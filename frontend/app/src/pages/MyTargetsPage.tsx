import { useState, useEffect, useMemo } from 'react'
import MessageBanner from '../components/MessageBanner'
import TargetCard, { TARGET_TYPE_LABELS } from '../components/TargetCard'
import AddTargetModal from '../components/AddTargetModal'
import EditTargetModal from '../components/EditTargetModal'
import DiscoverReposModal from '../components/DiscoverReposModal'
import DuplicateTargetModal from '../components/DuplicateTargetModal'
import { useTargets } from '../hooks/useTargets'
import { useConfig } from '../hooks/useConfig'
import { useAuth } from '../hooks/useAuth'
import { apiFetch } from '../utils/apiClient'
import { discoverRepos } from '../utils/repoHandlers'
import {
  DuplicateTargetError,
  findDuplicateTarget,
  type AddTargetPayload,
} from '../utils/targetDuplicate'
import type { ScanTargetItem, AutoScanConfig } from '../hooks/useTargets'

/** Last scan row is "done" enough for coverage / findings (not queue placeholders). */
function isFinishedScanStatus(status: string | undefined | null): boolean {
  if (!status) return false
  const s = String(status).toLowerCase()
  return ['completed', 'failed', 'cancelled', 'interrupted'].includes(s)
}

export default function MyTargetsPage() {
  const { targets, loading, loadTargets, triggerScan } = useTargets()
  const { config } = useConfig()
  const { isAuthenticated } = useAuth()
  const [initialScanDelaySeconds, setInitialScanDelaySeconds] = useState<number>(300)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [showAddModal, setShowAddModal] = useState(false)
  const [showDiscoverModal, setShowDiscoverModal] = useState(false)
  const [editingTarget, setEditingTarget] = useState<ScanTargetItem | null>(null)
  const [scanNowTargetId, setScanNowTargetId] = useState<string | null>(null)
  const [discoverUsername, setDiscoverUsername] = useState('')
  const [discoveredRepos, setDiscoveredRepos] = useState<any[]>([])
  const [discovering, setDiscovering] = useState(false)
  const [selectedRepos, setSelectedRepos] = useState<Set<string>>(new Set())
  const [addSelectedLoading, setAddSelectedLoading] = useState(false)
  const [discoverAddProgress, setDiscoverAddProgress] = useState<{
    current: number
    total: number
  } | null>(null)
  const [discoverAddResults, setDiscoverAddResults] = useState<
    { full_name: string; ok: boolean; error?: string }[] | null
  >(null)

  const [typeFilter, setTypeFilter] = useState<string>('')
  const [selectedTargetIds, setSelectedTargetIds] = useState<Set<string>>(new Set())
  const [duplicateState, setDuplicateState] = useState<{
    payload: AddTargetPayload
    existing: ScanTargetItem | null
  } | null>(null)
  const [cancellingScanId, setCancellingScanId] = useState<string | null>(null)

  const showMessage = (type: 'success' | 'error', text: string, duration = 3000) => {
    setMessage({ type, text })
    setTimeout(() => setMessage(null), duration)
  }

  const handleAddTarget = async (payload: AddTargetPayload) => {
    const res = await apiFetch('/api/user/targets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (res.ok) {
      await loadTargets({ silent: true })
      return
    }
    const err = await res.json().catch(() => ({}))
    const detail = typeof err.detail === 'string' ? err.detail : 'Failed to add target'
    if (/already/i.test(detail)) {
      const listRes = await apiFetch('/api/user/targets')
      let list: ScanTargetItem[] = []
      if (listRes.ok) {
        const data = await listRes.json()
        list = Array.isArray(data) ? data : []
      }
      const existing = findDuplicateTarget(list, payload) ?? null
      throw new DuplicateTargetError(detail, payload, existing)
    }
    throw new Error(detail)
  }

  useEffect(() => {
    const load = async () => {
      try {
        const res = await apiFetch('/api/user/targets/initial-scan-config')
        if (res.ok) {
          const data = await res.json()
          setInitialScanDelaySeconds(Number(data.initial_scan_delay_seconds) || 300)
        }
      } catch {
        // keep default 300
      }
    }
    load()
  }, [])

  const handleUpdateTarget = async (
    targetId: string,
    payload: {
      display_name?: string
      config?: Record<string, unknown>
      auto_scan?: AutoScanConfig
      scanners?: string[]
      initial_scan_paused?: boolean
    }
  ) => {
    const res = await apiFetch(`/api/user/targets/${targetId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Failed to update target')
    }
    await loadTargets({ silent: true })
  }

  const handleRemoveTarget = async (targetId: string, label: string) => {
    if (!confirm(`Remove "${label}"?`)) return
    const res = await apiFetch(`/api/user/targets/${targetId}`, { method: 'DELETE' })
    if (res.ok) {
      showMessage('success', 'Target removed')
      setSelectedTargetIds((prev) => {
        const next = new Set(prev)
        next.delete(targetId)
        return next
      })
      await loadTargets({ silent: true })
    } else {
      showMessage('error', 'Failed to remove target')
    }
  }

  const handleBulkRemove = async () => {
    const ids = filteredTargets.filter((t) => selectedTargetIds.has(t.id)).map((t) => t.id)
    if (ids.length === 0) {
      showMessage('error', 'No targets selected in the current list')
      return
    }
    if (
      !confirm(
        `Remove ${ids.length} selected target(s)? This cannot be undone.`
      )
    )
      return
    let removed = 0
    for (const id of ids) {
      const res = await apiFetch(`/api/user/targets/${id}`, { method: 'DELETE' })
      if (res.ok) removed++
    }
    setSelectedTargetIds((prev) => {
      const next = new Set(prev)
      ids.forEach((id) => next.delete(id))
      return next
    })
    await loadTargets({ silent: true })
    showMessage('success', `Removed ${removed} target(s)`)
  }

  const toggleTargetSelect = (targetId: string) => {
    setSelectedTargetIds((prev) => {
      const next = new Set(prev)
      if (next.has(targetId)) next.delete(targetId)
      else next.add(targetId)
      return next
    })
  }

  const selectAllFiltered = () => {
    setSelectedTargetIds((prev) => {
      const next = new Set(prev)
      filteredTargets.forEach((t) => next.add(t.id))
      return next
    })
  }

  const clearSelection = () => setSelectedTargetIds(new Set())

  const handlePauseInitialScan = async (targetId: string) => {
    try {
      await handleUpdateTarget(targetId, { initial_scan_paused: true })
      showMessage('success', 'First scan paused. Edit scanners then click "Start first scan" when ready.')
    } catch {
      showMessage('error', 'Failed to pause')
    }
  }

  const handleScanNow = async (targetId: string) => {
    setScanNowTargetId(targetId)
    const result = await triggerScan(targetId)
    setScanNowTargetId(null)
    if (result.success) {
      showMessage(
        'success',
        result.scan_id ? `Scan started (${result.scan_id.slice(0, 8)}…)` : 'Scan started'
      )
      await loadTargets({ silent: true })
    } else {
      showMessage('error', result.error || 'Failed to start scan')
    }
  }

  const handleCancelActiveScan = async (scanId: string) => {
    if (!confirm('Cancel this scan? It will leave the queue or stop if running.')) return
    setCancellingScanId(scanId)
    try {
      const res = await apiFetch(`/api/v1/scans/${scanId}/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scan_id: scanId, force: false }),
      })
      if (!res.ok) {
        let msg = `Cancel failed (${res.status})`
        try {
          const j = await res.json()
          msg = typeof j.detail === 'string' ? j.detail : msg
        } catch {
          /* ignore */
        }
        showMessage('error', msg)
      } else {
        showMessage('success', 'Scan cancelled.')
        await loadTargets({ silent: true })
      }
    } catch {
      showMessage('error', 'Cancel failed')
    } finally {
      setCancellingScanId(null)
    }
  }

  const handleDiscoverRepos = async () => {
    if (!discoverUsername.trim()) {
      showMessage('error', 'Please enter a GitHub username or organization')
      return
    }
    setDiscovering(true)
    setMessage(null)
    const result = await discoverRepos(discoverUsername)
    if (result.success) {
      setDiscoveredRepos(result.repos ?? [])
      setSelectedRepos(new Set())
    } else {
      showMessage('error', result.error ?? 'Failed to discover repositories')
    }
    setDiscovering(false)
  }

  const handleAddSelectedRepos = async () => {
    if (selectedRepos.size === 0) {
      showMessage('error', 'Please select at least one repository')
      return
    }
    const toAdd = discoveredRepos.filter((r) => selectedRepos.has(r.full_name))
    setAddSelectedLoading(true)
    setDiscoverAddResults(null)
    setDiscoverAddProgress({ current: 0, total: toAdd.length })

    const results: { full_name: string; ok: boolean; error?: string }[] = []
    let successCount = 0

    for (let i = 0; i < toAdd.length; i++) {
      const repo = toAdd[i]
      setDiscoverAddProgress({ current: i, total: toAdd.length })
      const res = await apiFetch('/api/user/targets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'git_repo',
          source: repo.html_url,
          display_name: repo.full_name,
          config: { branch: repo.default_branch || 'main' },
          auto_scan: { enabled: false, mode: 'interval', interval_seconds: undefined, event: null },
        }),
      })
      if (res.ok) {
        successCount++
        results.push({ full_name: repo.full_name, ok: true })
      } else {
        const err = await res.json().catch(() => ({}))
        const detail = typeof err.detail === 'string' ? err.detail : `Failed (${res.status})`
        const dup = /already/i.test(detail)
        results.push({
          full_name: repo.full_name,
          ok: false,
          error: dup ? 'Already a target' : detail,
        })
      }
    }

    setDiscoverAddProgress({ current: toAdd.length, total: toAdd.length })
    setDiscoverAddResults(results)
    setAddSelectedLoading(false)
    await loadTargets({ silent: true })

    if (successCount > 0) {
      showMessage('success', `Added ${successCount} of ${toAdd.length} repository target(s)`)
    } else {
      showMessage('error', 'No new targets were added')
    }

    if (successCount === toAdd.length) {
      setShowDiscoverModal(false)
      setDiscoverUsername('')
      setDiscoveredRepos([])
      setSelectedRepos(new Set())
      setDiscoverAddResults(null)
      setDiscoverAddProgress(null)
    }
  }

  const handleDuplicateEdit = () => {
    if (!duplicateState?.existing) return
    const t =
      targets.find((x) => x.id === duplicateState.existing!.id) ?? duplicateState.existing
    setEditingTarget(t)
    setDuplicateState(null)
  }

  const handleDuplicateReplace = async () => {
    if (!duplicateState?.existing || !duplicateState.payload) return
    const { payload, existing } = duplicateState
    const del = await apiFetch(`/api/user/targets/${existing.id}`, { method: 'DELETE' })
    if (!del.ok) {
      showMessage('error', 'Could not remove the existing target')
      return
    }
    const res = await apiFetch('/api/user/targets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      showMessage('error', typeof err.detail === 'string' ? err.detail : 'Failed to add target')
      await loadTargets({ silent: true })
      setDuplicateState(null)
      return
    }
    setDuplicateState(null)
    showMessage('success', 'Target replaced')
    await loadTargets({ silent: true })
  }

  const toggleRepoSelection = (repoFullName: string) => {
    setSelectedRepos((prev) => {
      const next = new Set(prev)
      if (next.has(repoFullName)) next.delete(repoFullName)
      else next.add(repoFullName)
      return next
    })
  }
  const selectAllRepos = () => setSelectedRepos(new Set(discoveredRepos.map((r) => r.full_name)))
  const deselectAllRepos = () => setSelectedRepos(new Set())

  const allowedTargets = config?.allowed_targets ?? null
  const withFinishedScan = targets.filter(
    (t) => t.last_scan && isFinishedScanStatus(t.last_scan.status)
  ).length
  const withQueuedOrRunning = targets.filter(
    (t) => t.last_scan && !isFinishedScanStatus(t.last_scan.status)
  ).length
  const withFindings = targets.filter(
    (t) =>
      t.last_scan &&
      isFinishedScanStatus(t.last_scan.status) &&
      t.last_scan.total_vulnerabilities > 0
  ).length
  const scannedPct = targets.length ? Math.round((100 * withFinishedScan) / targets.length) : 0

  const filteredTargets = useMemo(() => {
    if (!typeFilter) return targets
    return targets.filter((t) => t.type === typeFilter)
  }, [targets, typeFilter])

  const uniqueTypes = useMemo(
    () => [...new Set(targets.map((t) => t.type))].sort(),
    [targets]
  )

  const selectedInView = filteredTargets.filter((t) => selectedTargetIds.has(t.id)).length

  const closeDiscoverModal = () => {
    setShowDiscoverModal(false)
    setDiscoverUsername('')
    setDiscoveredRepos([])
    setSelectedRepos(new Set())
    setDiscoverAddProgress(null)
    setDiscoverAddResults(null)
  }

  const allowedDisplay = config?.allowed_targets_display?.length
    ? config.allowed_targets_display.join(', ')
    : null

  return (
    <div className="container" style={{ padding: '2rem' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h1>My Targets</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
          Manage your scan targets and automatic scanning. Add Git repos, container images, or local paths.
        </p>
        {!loading && targets.length > 0 && (
          <>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginTop: '0.35rem' }}>
              <strong>{targets.length}</strong> target{targets.length !== 1 ? 's' : ''}
              {withFinishedScan > 0 && (
                <>
                  {' '}
                  · <strong>{withFinishedScan}</strong> with a finished scan
                </>
              )}
              {withQueuedOrRunning > 0 && (
                <>
                  {' '}
                  · <strong>{withQueuedOrRunning}</strong> with scan queued or running
                </>
              )}
              {withFindings > 0 && (
                <>
                  {' '}
                  · <strong>{withFindings}</strong> with findings (finished scans)
                </>
              )}
            </p>
            <div style={{ marginTop: '0.75rem', maxWidth: '420px' }}>
              <div
                style={{
                  fontSize: '0.8rem',
                  color: 'var(--text-secondary)',
                  marginBottom: '0.35rem',
                  display: 'flex',
                  justifyContent: 'space-between',
                }}
              >
                <span>Finished-scan coverage</span>
                <span>
                  {withFinishedScan} / {targets.length} ({scannedPct}%)
                </span>
              </div>
              <div
                style={{
                  height: '8px',
                  borderRadius: '4px',
                  background: 'var(--glass-border-main)',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    height: '100%',
                    width: `${scannedPct}%`,
                    background: 'var(--accent, #0d6efd)',
                    transition: 'width 0.25s ease',
                  }}
                />
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.35rem' }}>
                Only counts targets whose <strong>latest</strong> scan has finished (completed, failed, cancelled,
                or interrupted). Pending or running scans are shown above but do not increase this bar until they
                finish.
              </p>
            </div>
          </>
        )}
      </div>

      {message && <MessageBanner type={message.type} text={message.text} />}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Targets</h2>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
          {targets.length > 0 && (
            <>
              <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                Filter type
                <select
                  value={typeFilter}
                  onChange={(e) => setTypeFilter(e.target.value)}
                  style={{ padding: '0.35rem 0.5rem', borderRadius: '6px' }}
                >
                  <option value="">All types</option>
                  {uniqueTypes.map((ty) => (
                    <option key={ty} value={ty}>
                      {TARGET_TYPE_LABELS[ty] || ty}
                    </option>
                  ))}
                </select>
              </label>
            </>
          )}
          {targets.length > 0 && (
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button type="button" onClick={() => setShowDiscoverModal(true)}>
                Discover Repos
              </button>
              <button type="button" className="primary" onClick={() => setShowAddModal(true)}>
                + Add target
              </button>
            </div>
          )}
        </div>
      </div>

      {targets.length > 0 && (
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            gap: '0.5rem',
            marginBottom: '1rem',
            padding: '0.75rem 1rem',
            borderRadius: '8px',
            border: '1px solid var(--glass-border-main)',
            background: 'var(--glass-bg-main)',
          }}
        >
          <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
            Bulk: <strong>{selectedInView}</strong> selected
            {typeFilter ? ` (in filtered list)` : ''}
          </span>
          <button type="button" onClick={selectAllFiltered} disabled={filteredTargets.length === 0}>
            Select all
          </button>
          <button type="button" onClick={clearSelection} disabled={selectedTargetIds.size === 0}>
            Clear selection
          </button>
          <button
            type="button"
            onClick={handleBulkRemove}
            disabled={selectedInView === 0}
            style={{ color: 'var(--color-critical)' }}
          >
            Remove selected ({selectedInView})
          </button>
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '2rem' }}>Loading…</div>
      ) : targets.length === 0 ? (
        <div
          style={{
            background: 'var(--glass-bg-main)',
            padding: '3rem',
            borderRadius: '8px',
            textAlign: 'left',
            border: '1px solid var(--glass-border-main)',
            maxWidth: '640px',
          }}
        >
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            No targets yet. Here is what you need to use this page:
          </p>
          <ul style={{ color: 'var(--text-secondary)', marginBottom: '1.25rem', paddingLeft: '1.25rem' }}>
            <li style={{ marginBottom: '0.35rem' }}>
              <strong>Account:</strong> {isAuthenticated ? 'You are signed in.' : 'Sign in so targets are saved to your account.'}
            </li>
            <li style={{ marginBottom: '0.35rem' }}>
              <strong>Allowed target types:</strong>{' '}
              {allowedDisplay || 'Configured by your administrator (instance settings).'}
            </li>
            <li style={{ marginBottom: '0.35rem' }}>
              <strong>Discover Repos:</strong> needs GitHub discovery to be enabled on this instance and a valid
              username or organization to search.
            </li>
          </ul>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem', fontSize: '0.9rem' }}>
            Add a repository URL, container image, or allowed local path, then run a scan or wait for auto-scan.
          </p>
          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-start', flexWrap: 'wrap' }}>
            <button type="button" onClick={() => setShowDiscoverModal(true)}>
              Discover Repos
            </button>
            <button type="button" className="primary" onClick={() => setShowAddModal(true)}>
              + Add your first target
            </button>
          </div>
        </div>
      ) : filteredTargets.length === 0 ? (
        <p style={{ color: 'var(--text-secondary)' }}>No targets match this type filter.</p>
      ) : (
        <div style={{ display: 'grid', gap: '1rem' }}>
          {filteredTargets.map((t) => (
            <TargetCard
              key={t.id}
              target={t}
              initialScanDelaySeconds={initialScanDelaySeconds}
              onScanNow={handleScanNow}
              onPauseInitialScan={handlePauseInitialScan}
              onEdit={setEditingTarget}
              onRemove={handleRemoveTarget}
              scanLoading={scanNowTargetId === t.id}
              onCancelActiveScan={handleCancelActiveScan}
              cancelLoadingForScanId={cancellingScanId}
              selectable
              selected={selectedTargetIds.has(t.id)}
              onSelectToggle={toggleTargetSelect}
            />
          ))}
        </div>
      )}

      <AddTargetModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSubmit={handleAddTarget}
        onDuplicate={(err) => {
          setShowAddModal(false)
          setDuplicateState({ payload: err.payload, existing: err.existing })
        }}
        allowedTargets={allowedTargets}
      />

      <DuplicateTargetModal
        isOpen={duplicateState !== null}
        onClose={() => setDuplicateState(null)}
        payload={duplicateState?.payload ?? null}
        existing={duplicateState?.existing ?? null}
        onEdit={handleDuplicateEdit}
        onReplace={handleDuplicateReplace}
      />

      <EditTargetModal
        isOpen={editingTarget !== null}
        target={editingTarget}
        onClose={() => setEditingTarget(null)}
        onSubmit={handleUpdateTarget}
      />

      <DiscoverReposModal
        isOpen={showDiscoverModal}
        onClose={closeDiscoverModal}
        discoverUsername={discoverUsername}
        onDiscoverUsernameChange={setDiscoverUsername}
        onDiscover={handleDiscoverRepos}
        discovering={discovering}
        discoveredRepos={discoveredRepos}
        selectedRepos={selectedRepos}
        onToggleRepoSelection={toggleRepoSelection}
        onSelectAll={selectAllRepos}
        onDeselectAll={deselectAllRepos}
        onAddSelected={handleAddSelectedRepos}
        loading={addSelectedLoading}
        addProgress={discoverAddProgress}
        addResults={discoverAddResults}
      />
    </div>
  )
}
