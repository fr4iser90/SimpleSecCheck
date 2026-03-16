import { useState } from 'react'
import RepoCard from '../components/RepoCard'
import AddRepoModal from '../components/AddRepoModal'
import EditRepoModal from '../components/EditRepoModal'
import DiscoverReposModal from '../components/DiscoverReposModal'
import BulkScannerConfigModal from '../components/BulkScannerConfigModal'
import RepoStats from '../components/RepoStats'
import RepoFilters from '../components/RepoFilters'
import MessageBanner from '../components/MessageBanner'
import { useRepos } from '../hooks/useRepos'
import { useScanners } from '../hooks/useScanners'
import { useRepoFilters } from '../hooks/useRepoFilters'
import {
  GitHubRepo,
  FilterType,
  SortType,
  getRepoStatus,
  calculateStats
} from '../utils/repoUtils'
import {
  addRepo,
  updateRepo,
  removeRepo,
  triggerScan,
  bulkUpdateScanners,
  discoverRepos,
  addSelectedRepos
} from '../utils/repoHandlers'

export default function MyReposPage() {
  const { repos, scanStatuses, loading, loadRepos } = useRepos()
  const { scanners: availableScanners } = useScanners('code')
  
  const [showAddModal, setShowAddModal] = useState(false)
  const [showDiscoverModal, setShowDiscoverModal] = useState(false)
  const [editingRepo, setEditingRepo] = useState<GitHubRepo | null>(null)
  const [discoverUsername, setDiscoverUsername] = useState('')
  const [discoveredRepos, setDiscoveredRepos] = useState<any[]>([])
  const [discovering, setDiscovering] = useState(false)
  const [selectedRepos, setSelectedRepos] = useState<Set<string>>(new Set())
  const [filter, setFilter] = useState<FilterType>('all')
  const [sortBy, setSortBy] = useState<SortType>('name')
  const [searchQuery, setSearchQuery] = useState('')
  const [formData, setFormData] = useState({
    repo_url: '',
    repo_owner: '',
    repo_name: '',
    branch: 'main',
    auto_scan_enabled: true,
    scan_on_push: true,
    scan_frequency: 'on_push'
  })
  const [editFormData, setEditFormData] = useState({
    branch: 'main',
    auto_scan_enabled: true,
    scan_on_push: true,
    scan_frequency: 'on_push',
    scanners: [] as string[]
  })
  const [showBulkScannerConfig, setShowBulkScannerConfig] = useState(false)
  const [bulkScanners, setBulkScanners] = useState<string[]>([])
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  const displayedRepos = useRepoFilters(repos, scanStatuses, filter, sortBy, searchQuery)
  const stats = calculateStats(repos, (repo) => getRepoStatus(repo, scanStatuses[repo.id]))

  const showMessage = (type: 'success' | 'error', text: string, duration = 3000) => {
    setMessage({ type, text })
    setTimeout(() => setMessage(null), duration)
  }

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    const result = await addRepo(formData)
    if (result.success) {
      setShowAddModal(false)
      setFormData({ repo_url: '', repo_owner: '', repo_name: '', branch: 'main', auto_scan_enabled: true, scan_on_push: true, scan_frequency: 'on_push' })
      showMessage('success', 'Repository added successfully')
      loadRepos()
    } else {
      showMessage('error', result.error || 'Failed to add repository')
    }
  }

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingRepo) return

    const result = await updateRepo(editingRepo.id, editFormData)
    if (result.success) {
      setEditingRepo(null)
      setEditFormData({ branch: 'main', auto_scan_enabled: true, scan_on_push: true, scan_frequency: 'on_push', scanners: [] })
      showMessage('success', 'Repository updated successfully')
      loadRepos()
    } else {
      showMessage('error', result.error || 'Failed to update repository')
    }
  }

  const handleBulkApplyScanners = async () => {
    if (bulkScanners.length === 0) {
      showMessage('error', 'Please select at least one scanner')
      return
    }

    const { successCount, errorCount } = await bulkUpdateScanners(repos, bulkScanners)
    setShowBulkScannerConfig(false)
    setBulkScanners([])
    const message = `Applied scanners to ${successCount} repos${errorCount > 0 ? ` (${errorCount} failed)` : ''}`
    showMessage(
      successCount > 0 ? 'success' : 'error',
      message,
      5000
    )
    loadRepos()
  }

  const handleRemove = async (repoId: string, repoName: string) => {
    if (!confirm(`Are you sure you want to remove "${repoName}"?`)) return

    const result = await removeRepo(repoId)
    if (result.success) {
      showMessage('success', 'Repository removed successfully')
      loadRepos()
    } else {
      showMessage('error', result.error || 'Failed to remove repository')
    }
  }

  const handleScanNow = async (repoId: string) => {
    const result = await triggerScan(repoId)
    if (result.success) {
      showMessage('success', 'Scan triggered successfully')
      loadRepos()
    } else {
      showMessage('error', result.error || 'Failed to trigger scan')
    }
  }

  const handleEdit = (repo: GitHubRepo) => {
    setEditingRepo(repo)
    setEditFormData({
      branch: repo.branch,
      auto_scan_enabled: repo.auto_scan_enabled,
      scan_on_push: repo.scan_on_push,
      scan_frequency: repo.scan_frequency,
      scanners: repo.scanners || []
    })
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
      setDiscoveredRepos(result.repos || [])
      setSelectedRepos(new Set())
    } else {
      showMessage('error', result.error || 'Failed to discover repositories')
    }
    setDiscovering(false)
  }

  const handleAddSelectedRepos = async () => {
    if (selectedRepos.size === 0) {
      showMessage('error', 'Please select at least one repository')
      return
    }

    const { successCount } = await addSelectedRepos(discoveredRepos, selectedRepos)
    if (successCount > 0) {
      showMessage('success', `Successfully added ${successCount} repository${successCount > 1 ? 'ies' : ''}`)
      setShowDiscoverModal(false)
      setDiscoverUsername('')
      setDiscoveredRepos([])
      setSelectedRepos(new Set())
      loadRepos()
    } else {
      showMessage('error', 'Failed to add repositories')
    }
  }

  const toggleRepoSelection = (repoFullName: string) => {
    const newSelected = new Set(selectedRepos)
    if (newSelected.has(repoFullName)) {
      newSelected.delete(repoFullName)
    } else {
      newSelected.add(repoFullName)
    }
    setSelectedRepos(newSelected)
  }

  const selectAllRepos = () => {
    const allRepoNames = new Set(discoveredRepos.map(repo => repo.full_name))
    setSelectedRepos(allRepoNames)
  }

  const deselectAllRepos = () => {
    setSelectedRepos(new Set())
  }

  return (
    <div className="container" style={{ padding: '2rem' }}>
      <div style={{ marginBottom: '2rem' }}>
        <div>
          <h1>My GitHub Repos</h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            Manage your GitHub repositories with automatic scanning
          </p>
        </div>
      </div>

      {message && <MessageBanner type={message.type} text={message.text} />}

      {!loading && repos.length > 0 && (
        <>
          <RepoStats
            total={stats.total}
            scanned={stats.scanned}
            needsAttention={stats.needsAttention}
            critical={stats.critical}
          />
          <RepoFilters
            filter={filter}
            sortBy={sortBy}
            searchQuery={searchQuery}
            onFilterChange={setFilter}
            onSortChange={setSortBy}
            onSearchChange={setSearchQuery}
            onDiscoverClick={() => setShowDiscoverModal(true)}
            onAddClick={() => setShowAddModal(true)}
            onConfigureScannersClick={() => {
              setBulkScanners([])
              setShowBulkScannerConfig(true)
            }}
          />
        </>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '2rem' }}>Loading...</div>
      ) : repos.length === 0 ? (
        <div style={{
          background: 'var(--glass-bg-dark)',
          padding: '3rem',
          borderRadius: '8px',
          textAlign: 'center',
          border: '1px solid var(--glass-border-dark)'
        }}>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            No repositories added yet. Add your first repository to get started!
          </p>
          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
            <button onClick={() => setShowDiscoverModal(true)}>
              🔍 Discover Repos
            </button>
            <button className="primary" onClick={() => setShowAddModal(true)}>
              + Add Your First Repo
            </button>
          </div>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '1rem' }}>
          {displayedRepos.map((repo) => (
            <RepoCard
              key={repo.id}
              repo={repo}
              scanStatus={scanStatuses[repo.id]}
              onScanNow={handleScanNow}
              onEdit={handleEdit}
              onRemove={handleRemove}
            />
          ))}
        </div>
      )}

      <AddRepoModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSubmit={handleAdd}
        formData={formData}
        onFormDataChange={setFormData}
      />

      <EditRepoModal
        isOpen={editingRepo !== null}
        repo={editingRepo}
        onClose={() => setEditingRepo(null)}
        onSubmit={handleUpdate}
        formData={editFormData}
        onFormDataChange={setEditFormData}
        availableScanners={availableScanners}
      />

      <BulkScannerConfigModal
        isOpen={showBulkScannerConfig}
        reposCount={repos.length}
        availableScanners={availableScanners}
        selectedScanners={bulkScanners}
        onSelectionChange={setBulkScanners}
        onApply={handleBulkApplyScanners}
        onClose={() => {
          setShowBulkScannerConfig(false)
          setBulkScanners([])
        }}
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
        loading={loading}
      />
    </div>
  )
}
