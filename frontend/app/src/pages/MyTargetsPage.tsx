import { useState } from 'react'
import MessageBanner from '../components/MessageBanner'
import TargetCard from '../components/TargetCard'
import AddTargetModal from '../components/AddTargetModal'
import EditTargetModal from '../components/EditTargetModal'
import DiscoverReposModal from '../components/DiscoverReposModal'
import { useTargets } from '../hooks/useTargets'
import { useConfig } from '../hooks/useConfig'
import { apiFetch } from '../utils/apiClient'
import { discoverRepos } from '../utils/repoHandlers'
import type { ScanTargetItem, AutoScanConfig } from '../hooks/useTargets'

export default function MyTargetsPage() {
  const { targets, loading, loadTargets, triggerScan } = useTargets()
  const { config } = useConfig()
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

  const showMessage = (type: 'success' | 'error', text: string, duration = 3000) => {
    setMessage({ type, text })
    setTimeout(() => setMessage(null), duration)
  }

  const handleAddTarget = async (payload: {
    type: string
    source: string
    display_name?: string
    config: Record<string, unknown>
    auto_scan: AutoScanConfig
  }) => {
    const res = await apiFetch('/api/user/targets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Failed to add target')
    }
    loadTargets()
  }

  const handleUpdateTarget = async (
    targetId: string,
    payload: {
      display_name?: string
      config?: Record<string, unknown>
      auto_scan?: AutoScanConfig
      scanners?: string[]
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
    loadTargets()
  }

  const handleRemoveTarget = async (targetId: string, label: string) => {
    if (!confirm(`Remove "${label}"?`)) return
    const res = await apiFetch(`/api/user/targets/${targetId}`, { method: 'DELETE' })
    if (res.ok) {
      showMessage('success', 'Target removed')
      loadTargets()
    } else {
      showMessage('error', 'Failed to remove target')
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
    } else {
      showMessage('error', result.error || 'Failed to start scan')
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
    let successCount = 0
    for (const repo of toAdd) {
      try {
        await handleAddTarget({
          type: 'git_repo',
          source: repo.html_url,
          display_name: repo.full_name,
          config: { branch: repo.default_branch || 'main' },
          auto_scan: { enabled: false, mode: 'interval', interval_seconds: undefined, event: null },
        })
        successCount++
      } catch {
        // continue with next
      }
    }
    setAddSelectedLoading(false)
    if (successCount > 0) {
      showMessage('success', `Added ${successCount} target${successCount !== 1 ? 's' : ''}`)
      setShowDiscoverModal(false)
      setDiscoverUsername('')
      setDiscoveredRepos([])
      setSelectedRepos(new Set())
      loadTargets()
    } else {
      showMessage('error', 'Failed to add targets')
    }
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
  const withLastScan = targets.filter((t) => t.last_scan).length
  const withFindings = targets.filter((t) => t.last_scan && t.last_scan.total_vulnerabilities > 0).length

  return (
    <div className="container" style={{ padding: '2rem' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h1>My Targets</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
          Manage your scan targets and automatic scanning. Add Git repos, container images, or local paths.
        </p>
        {!loading && targets.length > 0 && (
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginTop: '0.35rem' }}>
            <strong>{targets.length}</strong> target{targets.length !== 1 ? 's' : ''}
            {withLastScan > 0 && <> · <strong>{withLastScan}</strong> with last scan</>}
            {withFindings > 0 && <> · <strong>{withFindings}</strong> with findings</>}
          </p>
        )}
      </div>

      {message && <MessageBanner type={message.type} text={message.text} />}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Targets</h2>
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

      {loading ? (
        <div style={{ textAlign: 'center', padding: '2rem' }}>Loading…</div>
      ) : targets.length === 0 ? (
        <div
          style={{
            background: 'var(--glass-bg-dark)',
            padding: '3rem',
            borderRadius: '8px',
            textAlign: 'center',
            border: '1px solid var(--glass-border-dark)',
          }}
        >
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            No targets yet. Add your first target to get started.
          </p>
          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center', flexWrap: 'wrap' }}>
            <button type="button" onClick={() => setShowDiscoverModal(true)}>
              Discover Repos
            </button>
            <button type="button" className="primary" onClick={() => setShowAddModal(true)}>
              + Add your first target
            </button>
          </div>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '1rem' }}>
          {targets.map((t) => (
            <TargetCard
              key={t.id}
              target={t}
              onScanNow={handleScanNow}
              onEdit={setEditingTarget}
              onRemove={handleRemoveTarget}
              scanLoading={scanNowTargetId === t.id}
            />
          ))}
        </div>
      )}

      <AddTargetModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSubmit={handleAddTarget}
        allowedTargets={allowedTargets}
      />

      <EditTargetModal
        isOpen={editingTarget !== null}
        target={editingTarget}
        onClose={() => setEditingTarget(null)}
        onSubmit={handleUpdateTarget}
      />

      <DiscoverReposModal
        isOpen={showDiscoverModal}
        onClose={() => {
          setShowDiscoverModal(false)
          setDiscoverUsername('')
          setDiscoveredRepos([])
          setSelectedRepos(new Set())
        }}
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
      />
    </div>
  )
}
