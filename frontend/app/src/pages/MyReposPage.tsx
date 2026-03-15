import { useState, useEffect } from 'react'
import { apiFetch } from '../utils/apiClient'
import { Link } from 'react-router-dom'

interface GitHubRepo {
  id: string
  repo_url: string
  repo_name: string
  branch: string
  auto_scan_enabled: boolean
  scan_on_push: boolean
  scan_frequency: string
  created_at: string
  updated_at: string
  last_scan: {
    scan_id: string | null
    score: number
    vulnerabilities: { critical: number, high: number, medium: number, low: number }
    created_at: string
  } | null
  score: number | null
  vulnerabilities: { critical: number, high: number, medium: number, low: number } | null
}

export default function MyReposPage() {
  const [repos, setRepos] = useState<GitHubRepo[]>([])
  const [loading, setLoading] = useState(true)
  const [showAddModal, setShowAddModal] = useState(false)
  const [editingRepo, setEditingRepo] = useState<GitHubRepo | null>(null)
  const [formData, setFormData] = useState({
    repo_url: '',
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
    const interval = setInterval(loadRepos, 30000) // Refresh every 30 seconds
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
        setFormData({ repo_url: '', branch: 'main', auto_scan_enabled: true, scan_on_push: true, scan_frequency: 'on_push' })
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
        body: JSON.stringify({
          branch: formData.branch,
          auto_scan_enabled: formData.auto_scan_enabled,
          scan_on_push: formData.scan_on_push,
          scan_frequency: formData.scan_frequency
        })
      })
      
      if (response.ok) {
        setEditingRepo(null)
        setFormData({ repo_url: '', branch: 'main', auto_scan_enabled: true, scan_on_push: true, scan_frequency: 'on_push' })
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

  const getScoreColor = (score: number | null): string => {
    if (!score) return 'var(--text-secondary)'
    if (score >= 80) return 'var(--color-pass)'
    if (score >= 60) return 'var(--color-medium)'
    return 'var(--color-critical)'
  }

  const getVulnCount = (repo: GitHubRepo): number => {
    if (!repo.vulnerabilities) return 0
    return (repo.vulnerabilities.critical || 0) + 
           (repo.vulnerabilities.high || 0) + 
           (repo.vulnerabilities.medium || 0) + 
           (repo.vulnerabilities.low || 0)
  }

  return (
    <div className="container" style={{ padding: '2rem' }}>
      <div style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>My GitHub Repos</h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            Manage your GitHub repositories with automatic scanning
          </p>
        </div>
        <button className="primary" onClick={() => setShowAddModal(true)}>
          + Add Repo
        </button>
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
          <button className="primary" onClick={() => setShowAddModal(true)}>
            + Add Your First Repo
          </button>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '1rem' }}>
          {repos.map((repo) => (
            <div
              key={repo.id}
              style={{
                background: 'var(--glass-bg-dark)',
                padding: '1.5rem',
                borderRadius: '8px',
                border: '1px solid var(--glass-border-dark)'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                <div style={{ flex: 1 }}>
                  <h3 style={{ margin: 0, marginBottom: '0.5rem' }}>
                    📦 {repo.repo_name}
                  </h3>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '0.5rem' }}>
                    {repo.repo_url}
                  </div>
                  <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    <span>Branch: <strong>{repo.branch}</strong></span>
                    <span>Auto-scan: <strong>{repo.auto_scan_enabled ? 'ON' : 'OFF'}</strong></span>
                    {repo.auto_scan_enabled && (
                      <span>Scan on push: <strong>{repo.scan_on_push ? 'ON' : 'OFF'}</strong></span>
                    )}
                    {repo.last_scan && (
                      <span>Last scan: <strong>{new Date(repo.last_scan.created_at).toLocaleString()}</strong></span>
                    )}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  {repo.score !== null && (
                    <div style={{
                      padding: '0.5rem 1rem',
                      borderRadius: '8px',
                      background: 'rgba(0, 0, 0, 0.3)',
                      textAlign: 'center'
                    }}>
                      <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: getScoreColor(repo.score) }}>
                        {repo.score}/100
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Score</div>
                    </div>
                  )}
                </div>
              </div>

              {repo.vulnerabilities && (
                <div style={{
                  display: 'flex',
                  gap: '0.5rem',
                  marginBottom: '1rem',
                  padding: '0.75rem',
                  background: 'rgba(0, 0, 0, 0.2)',
                  borderRadius: '6px',
                  fontSize: '0.85rem'
                }}>
                  <span style={{ color: 'var(--color-critical)' }}>
                    Critical: {repo.vulnerabilities.critical || 0}
                  </span>
                  <span style={{ color: 'var(--color-high)' }}>
                    High: {repo.vulnerabilities.high || 0}
                  </span>
                  <span style={{ color: 'var(--color-medium)' }}>
                    Medium: {repo.vulnerabilities.medium || 0}
                  </span>
                  <span style={{ color: 'var(--color-low)' }}>
                    Low: {repo.vulnerabilities.low || 0}
                  </span>
                  <span style={{ marginLeft: 'auto', fontWeight: 'bold' }}>
                    Total: {getVulnCount(repo)}
                  </span>
                </div>
              )}

              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {repo.last_scan?.scan_id && (
                  <Link
                    to={`/scan?scan_id=${repo.last_scan.scan_id}`}
                    style={{
                      padding: '0.5rem 1rem',
                      background: 'var(--glass-bg-dark)',
                      border: '1px solid var(--glass-border-dark)',
                      borderRadius: '6px',
                      textDecoration: 'none',
                      color: 'var(--text-dark)',
                      fontSize: '0.9rem'
                    }}
                  >
                    View Results
                  </Link>
                )}
                <button
                  onClick={() => handleScanNow(repo.id)}
                  style={{ fontSize: '0.9rem', padding: '0.5rem 1rem' }}
                >
                  Scan Now
                </button>
                <button
                  onClick={() => {
                    setEditingRepo(repo)
                    setFormData({
                      repo_url: repo.repo_url,
                      branch: repo.branch,
                      auto_scan_enabled: repo.auto_scan_enabled,
                      scan_on_push: repo.scan_on_push,
                      scan_frequency: repo.scan_frequency
                    })
                  }}
                  style={{ fontSize: '0.9rem', padding: '0.5rem 1rem' }}
                >
                  Settings
                </button>
                <button
                  onClick={() => handleRemove(repo.id, repo.repo_name)}
                  style={{ fontSize: '0.9rem', padding: '0.5rem 1rem', background: 'var(--color-critical)' }}
                >
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Modal */}
      {showAddModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.7)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            background: 'var(--glass-bg-dark)',
            padding: '2rem',
            borderRadius: '8px',
            width: '90%',
            maxWidth: '500px',
            border: '1px solid var(--glass-border-dark)'
          }}>
            <h2 style={{ marginTop: 0 }}>Add GitHub Repository</h2>
            <form onSubmit={handleAdd}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem' }}>Repository URL</label>
                <input
                  type="text"
                  required
                  placeholder="https://github.com/user/repo"
                  value={formData.repo_url}
                  onChange={(e) => setFormData({ ...formData, repo_url: e.target.value })}
                  style={{ width: '100%' }}
                />
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem' }}>Branch</label>
                <input
                  type="text"
                  required
                  value={formData.branch}
                  onChange={(e) => setFormData({ ...formData, branch: e.target.value })}
                  style={{ width: '100%' }}
                />
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={formData.auto_scan_enabled}
                    onChange={(e) => setFormData({ ...formData, auto_scan_enabled: e.target.checked })}
                  />
                  <span>Enable Auto-Scan</span>
                </label>
              </div>
              {formData.auto_scan_enabled && (
                <>
                  <div style={{ marginBottom: '1rem' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={formData.scan_on_push}
                        onChange={(e) => setFormData({ ...formData, scan_on_push: e.target.checked })}
                      />
                      <span>Scan on Push</span>
                    </label>
                  </div>
                  <div style={{ marginBottom: '1rem' }}>
                    <label style={{ display: 'block', marginBottom: '0.5rem' }}>Scan Frequency</label>
                    <select
                      value={formData.scan_frequency}
                      onChange={(e) => setFormData({ ...formData, scan_frequency: e.target.value })}
                      style={{ width: '100%' }}
                    >
                      <option value="on_push">On Push</option>
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                      <option value="manual">Manual Only</option>
                    </select>
                  </div>
                </>
              )}
              <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                <button type="button" onClick={() => setShowAddModal(false)}>Cancel</button>
                <button type="submit" className="primary">Add Repository</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editingRepo && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.7)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            background: 'var(--glass-bg-dark)',
            padding: '2rem',
            borderRadius: '8px',
            width: '90%',
            maxWidth: '500px',
            border: '1px solid var(--glass-border-dark)'
          }}>
            <h2 style={{ marginTop: 0 }}>Repository Settings</h2>
            <form onSubmit={handleUpdate}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem' }}>Branch</label>
                <input
                  type="text"
                  required
                  value={formData.branch}
                  onChange={(e) => setFormData({ ...formData, branch: e.target.value })}
                  style={{ width: '100%' }}
                />
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={formData.auto_scan_enabled}
                    onChange={(e) => setFormData({ ...formData, auto_scan_enabled: e.target.checked })}
                  />
                  <span>Enable Auto-Scan</span>
                </label>
              </div>
              {formData.auto_scan_enabled && (
                <>
                  <div style={{ marginBottom: '1rem' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={formData.scan_on_push}
                        onChange={(e) => setFormData({ ...formData, scan_on_push: e.target.checked })}
                      />
                      <span>Scan on Push</span>
                    </label>
                  </div>
                  <div style={{ marginBottom: '1rem' }}>
                    <label style={{ display: 'block', marginBottom: '0.5rem' }}>Scan Frequency</label>
                    <select
                      value={formData.scan_frequency}
                      onChange={(e) => setFormData({ ...formData, scan_frequency: e.target.value })}
                      style={{ width: '100%' }}
                    >
                      <option value="on_push">On Push</option>
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                      <option value="manual">Manual Only</option>
                    </select>
                  </div>
                </>
              )}
              <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                <button type="button" onClick={() => setEditingRepo(null)}>Cancel</button>
                <button type="submit" className="primary">Update</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
