import { useState, useEffect } from 'react'
import { apiFetch } from '../utils/apiClient'
import RepoCard from '../components/RepoCard'
import AddRepoModal from '../components/AddRepoModal'
import EditRepoModal from '../components/EditRepoModal'
import DiscoverReposModal from '../components/DiscoverReposModal'
import {
  GitHubRepo,
  RepoScanStatus,
  FilterType,
  SortType,
  getRepoStatus,
  calculateStats
} from '../utils/repoUtils'

export default function MyReposPage() {
  const [repos, setRepos] = useState<GitHubRepo[]>([])
  const [scanStatuses, setScanStatuses] = useState<Record<string, RepoScanStatus>>({})
  const [loading, setLoading] = useState(true)
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
    scan_frequency: 'on_push'
  })
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  const loadRepos = async () => {
    setLoading(true)
    try {
      const response = await apiFetch('/api/user/github/repos')
      if (response.ok) {
        const data = await response.json()
        setRepos(data)
        
        // Load scan statuses for all repos
        const statusPromises = data.map(async (repo: GitHubRepo) => {
          try {
            const statusResponse = await apiFetch(`/api/user/github/repos/${repo.id}/scan-status`)
            if (statusResponse.ok) {
              const statusData = await statusResponse.json()
              return { repoId: repo.id, status: statusData }
            }
          } catch (error) {
            console.error(`Failed to load scan status for repo ${repo.id}:`, error)
          }
          return { repoId: repo.id, status: { has_active_scan: false, status: null, scan_id: null, queue_position: null } }
        })
        
        const statusResults = await Promise.all(statusPromises)
        const statusMap: Record<string, RepoScanStatus> = {}
        statusResults.forEach(({ repoId, status }) => {
          statusMap[repoId] = status
        })
        setScanStatuses(statusMap)
      }
    } catch (error) {
      console.error('Failed to load repos:', error)
      setMessage({ type: 'error', text: 'Failed to load repositories' })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRepos()
    const interval = setInterval(loadRepos, 30000)
    return () => clearInterval(interval)
  }, [])

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const response = await apiFetch('/api/user/github/repos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })
      
      if (response.ok) {
        setShowAddModal(false)
        setFormData({ repo_url: '', repo_owner: '', repo_name: '', branch: 'main', auto_scan_enabled: true, scan_on_push: true, scan_frequency: 'on_push' })
        setMessage({ type: 'success', text: 'Repository added successfully' })
        setTimeout(() => setMessage(null), 3000)
        loadRepos()
      } else {
        const error = await response.json()
        setMessage({ type: 'error', text: error.detail || 'Failed to add repository' })
      }
    } catch (error) {
      console.error('Failed to add repo:', error)
      setMessage({ type: 'error', text: 'Failed to add repository' })
    }
  }

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingRepo) return

    try {
      const response = await apiFetch(`/api/user/github/repos/${editingRepo.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editFormData)
      })
      
      if (response.ok) {
        setEditingRepo(null)
        setEditFormData({ branch: 'main', auto_scan_enabled: true, scan_on_push: true, scan_frequency: 'on_push' })
        setMessage({ type: 'success', text: 'Repository updated successfully' })
        setTimeout(() => setMessage(null), 3000)
        loadRepos()
      } else {
        const error = await response.json()
        setMessage({ type: 'error', text: error.detail || 'Failed to update repository' })
      }
    } catch (error) {
      console.error('Failed to update repo:', error)
      setMessage({ type: 'error', text: 'Failed to update repository' })
    }
  }

  const handleRemove = async (repoId: string, repoName: string) => {
    if (!confirm(`Are you sure you want to remove "${repoName}"?`)) return

    try {
      const response = await apiFetch(`/api/user/github/repos/${repoId}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        setMessage({ type: 'success', text: 'Repository removed successfully' })
        setTimeout(() => setMessage(null), 3000)
        loadRepos()
      } else {
        const error = await response.json()
        setMessage({ type: 'error', text: error.detail || 'Failed to remove repository' })
      }
    } catch (error) {
      console.error('Failed to remove repo:', error)
      setMessage({ type: 'error', text: 'Failed to remove repository' })
    }
  }

  const handleScanNow = async (repoId: string) => {
    try {
      const response = await apiFetch(`/api/user/github/repos/${repoId}/scan`, {
        method: 'POST'
      })
      
      if (response.ok) {
        setMessage({ type: 'success', text: 'Scan triggered successfully' })
        setTimeout(() => setMessage(null), 3000)
        loadRepos()
      } else {
        const error = await response.json()
        setMessage({ type: 'error', text: error.detail || 'Failed to trigger scan' })
      }
    } catch (error) {
      console.error('Failed to trigger scan:', error)
      setMessage({ type: 'error', text: 'Failed to trigger scan' })
    }
  }

  const handleEdit = (repo: GitHubRepo) => {
    setEditingRepo(repo)
    setEditFormData({
      branch: repo.branch,
      auto_scan_enabled: repo.auto_scan_enabled,
      scan_on_push: repo.scan_on_push,
      scan_frequency: repo.scan_frequency
    })
  }

  const handleDiscoverRepos = async () => {
    if (!discoverUsername.trim()) {
      setMessage({ type: 'error', text: 'Please enter a GitHub username or organization' })
      return
    }

    setDiscovering(true)
    setMessage(null)
    try {
      const response = await apiFetch(`/api/git/repos?username=${encodeURIComponent(discoverUsername.trim())}`)
      if (response.ok) {
        const data = await response.json()
        setDiscoveredRepos(data.repos || [])
        setSelectedRepos(new Set())
      } else {
        const error = await response.json()
        setMessage({ type: 'error', text: error.detail || 'Failed to discover repositories' })
      }
    } catch (error) {
      console.error('Failed to discover repos:', error)
      setMessage({ type: 'error', text: 'Failed to discover repositories. Make sure the username/organization exists.' })
    } finally {
      setDiscovering(false)
    }
  }

  const handleAddSelectedRepos = async () => {
    if (selectedRepos.size === 0) {
      setMessage({ type: 'error', text: 'Please select at least one repository' })
      return
    }

    setLoading(true)
    try {
      const reposToAdd = discoveredRepos.filter(repo => selectedRepos.has(repo.full_name))
      let successCount = 0
      let errorCount = 0

      for (const repo of reposToAdd) {
        try {
          const response = await apiFetch('/api/user/github/repos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              repo_url: repo.html_url,
              repo_owner: repo.full_name.split('/')[0],
              repo_name: repo.full_name.split('/')[1] || repo.name,
              branch: repo.default_branch || 'main',
              auto_scan_enabled: true,
              scan_on_push: true,
              scan_frequency: 'on_push'
            })
          })
          
          if (response.ok) {
            successCount++
          } else {
            errorCount++
          }
        } catch (error) {
          errorCount++
        }
      }

      if (successCount > 0) {
        setMessage({ type: 'success', text: `Successfully added ${successCount} repository${successCount > 1 ? 'ies' : ''}` })
        setTimeout(() => setMessage(null), 3000)
        setShowDiscoverModal(false)
        setDiscoverUsername('')
        setDiscoveredRepos([])
        setSelectedRepos(new Set())
        loadRepos()
      } else {
        setMessage({ type: 'error', text: 'Failed to add repositories' })
      }
    } catch (error) {
      console.error('Failed to add repos:', error)
      setMessage({ type: 'error', text: 'Failed to add repositories' })
    } finally {
      setLoading(false)
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

  const filteredAndSortedRepos = () => {
    let filtered = repos.filter(repo => {
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        const fullName = `${repo.repo_owner || ''}/${repo.repo_name}`.toLowerCase()
        if (!fullName.includes(query) && !repo.repo_url.toLowerCase().includes(query)) {
          return false
        }
      }
      
      // Status filter
      if (filter !== 'all') {
        const status = getRepoStatus(repo, scanStatuses[repo.id])
        if (filter === 'healthy' && status.type !== 'healthy') return false
        if (filter === 'needs_attention' && status.type !== 'needs_attention') return false
        if (filter === 'critical' && status.type !== 'critical') return false
        if (filter === 'not_scanned' && status.type !== 'not_scanned') return false
      }
      
      return true
    })
    
    // Sort
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'score':
          const scoreA = a.score ?? 0
          const scoreB = b.score ?? 0
          return scoreB - scoreA
        case 'last_scan':
          const dateA = a.last_scan?.created_at ? new Date(a.last_scan.created_at).getTime() : 0
          const dateB = b.last_scan?.created_at ? new Date(b.last_scan.created_at).getTime() : 0
          return dateB - dateA
        case 'vulnerabilities':
          const vulnA = (a.vulnerabilities?.critical || 0) + (a.vulnerabilities?.high || 0) + (a.vulnerabilities?.medium || 0) + (a.vulnerabilities?.low || 0)
          const vulnB = (b.vulnerabilities?.critical || 0) + (b.vulnerabilities?.high || 0) + (b.vulnerabilities?.medium || 0) + (b.vulnerabilities?.low || 0)
          return vulnB - vulnA
        case 'name':
        default:
          const nameA = `${a.repo_owner || ''}/${a.repo_name}`.toLowerCase()
          const nameB = `${b.repo_owner || ''}/${b.repo_name}`.toLowerCase()
          return nameA.localeCompare(nameB)
      }
    })
    
    return filtered
  }

  const stats = calculateStats(repos, (repo) => getRepoStatus(repo, scanStatuses[repo.id]))
  const displayedRepos = filteredAndSortedRepos()

  return (
    <div className="container" style={{ padding: '2rem' }}>
      <div style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>My GitHub Repos</h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            Manage your GitHub repositories with automatic scanning
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button onClick={() => setShowDiscoverModal(true)}>
            🔍 Discover Repos
          </button>
          <button className="primary" onClick={() => setShowAddModal(true)}>
            + Add Repo
          </button>
        </div>
      </div>

      {message && (
        <div style={{
          padding: '1rem',
          marginBottom: '1.5rem',
          borderRadius: '8px',
          background: message.type === 'success' ? 'rgba(40, 167, 69, 0.2)' : 'rgba(220, 53, 69, 0.2)',
          border: `1px solid ${message.type === 'success' ? 'var(--color-pass)' : 'var(--color-critical)'}`,
          color: message.type === 'success' ? 'var(--color-pass)' : 'var(--color-critical)'
        }}>
          {message.text}
        </div>
      )}

      {!loading && repos.length > 0 && (
        <>
          {/* Quick Stats */}
          <div style={{
            background: 'var(--glass-bg-dark)',
            padding: '1rem 1.5rem',
            borderRadius: '8px',
            marginBottom: '1.5rem',
            border: '1px solid var(--glass-border-dark)',
            display: 'flex',
            gap: '2rem',
            flexWrap: 'wrap',
            fontSize: '0.9rem'
          }}>
            <div>
              <strong>📦 Total Repos:</strong> {stats.total}
            </div>
            <div>
              <strong>✅ Scanned:</strong> {stats.scanned}
            </div>
            <div style={{ color: stats.needsAttention > 0 ? 'var(--color-medium)' : 'inherit' }}>
              <strong>⚠️ Needs Attention:</strong> {stats.needsAttention}
            </div>
            <div style={{ color: stats.critical > 0 ? 'var(--color-critical)' : 'inherit' }}>
              <strong>🔴 Critical:</strong> {stats.critical}
            </div>
          </div>

          {/* Filters and Search */}
          <div style={{
            display: 'flex',
            gap: '1rem',
            marginBottom: '1.5rem',
            flexWrap: 'wrap',
            alignItems: 'center'
          }}>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <label style={{ fontSize: '0.9rem' }}>Filter:</label>
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value as FilterType)}
                style={{ padding: '0.5rem', borderRadius: '6px', background: 'var(--glass-bg-dark)', border: '1px solid var(--glass-border-dark)', color: 'var(--text-dark)' }}
              >
                <option value="all">All</option>
                <option value="healthy">🟢 Healthy</option>
                <option value="needs_attention">🟡 Needs Attention</option>
                <option value="critical">🔴 Critical</option>
                <option value="not_scanned">⚪ Not Scanned</option>
              </select>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <label style={{ fontSize: '0.9rem' }}>Sort:</label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortType)}
                style={{ padding: '0.5rem', borderRadius: '6px', background: 'var(--glass-bg-dark)', border: '1px solid var(--glass-border-dark)', color: 'var(--text-dark)' }}
              >
                <option value="name">Name</option>
                <option value="score">Score</option>
                <option value="last_scan">Last Scan</option>
                <option value="vulnerabilities">Vulnerabilities</option>
              </select>
            </div>
            <div style={{ flex: 1, minWidth: '200px' }}>
              <input
                type="text"
                placeholder="🔍 Search repositories..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: 'var(--glass-bg-dark)', border: '1px solid var(--glass-border-dark)', color: 'var(--text-dark)' }}
              />
            </div>
          </div>
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
        onAddSelected={handleAddSelectedRepos}
        loading={loading}
      />
    </div>
  )
}
