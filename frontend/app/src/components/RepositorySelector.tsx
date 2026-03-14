import { useState, useMemo } from 'react'

export interface Repository {
  name: string
  full_name: string
  url: string
  clone_url: string
  private: boolean
  size_mb: number
  language: string | null
  description: string | null
  default_branch: string
  updated_at: string
  stargazers_count: number
  forks_count: number
}

interface RepositorySelectorProps {
  repositories: Repository[]
  selectedRepos: Set<string>
  onSelectionChange: (selected: Set<string>) => void
}

export default function RepositorySelector({
  repositories,
  selectedRepos,
  onSelectionChange
}: RepositorySelectorProps) {
  const [filter, setFilter] = useState<'all' | 'small' | 'medium' | 'large'>('all')
  const [languageFilter, setLanguageFilter] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')

  const languages = useMemo(() => {
    const langs = new Set<string>()
    repositories.forEach(repo => {
      if (repo.language) langs.add(repo.language)
    })
    return Array.from(langs).sort()
  }, [repositories])

  const filteredRepos = useMemo(() => {
    return repositories.filter(repo => {
      // Size filter
      if (filter === 'small' && repo.size_mb >= 5) return false
      if (filter === 'medium' && (repo.size_mb < 5 || repo.size_mb >= 50)) return false
      if (filter === 'large' && repo.size_mb < 50) return false

      // Language filter
      if (languageFilter !== 'all' && repo.language !== languageFilter) return false

      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        if (!repo.name.toLowerCase().includes(query) &&
            !repo.full_name.toLowerCase().includes(query) &&
            !(repo.description?.toLowerCase().includes(query))) {
          return false
        }
      }

      return true
    })
  }, [repositories, filter, languageFilter, searchQuery])

  const handleSelectAll = () => {
    const newSelection = new Set(filteredRepos.map(r => r.clone_url))
    onSelectionChange(newSelection)
  }

  const handleDeselectAll = () => {
    const newSelection = new Set<string>()
    onSelectionChange(newSelection)
  }

  const handleToggleRepo = (repoUrl: string) => {
    const newSelection = new Set(selectedRepos)
    if (newSelection.has(repoUrl)) {
      newSelection.delete(repoUrl)
    } else {
      newSelection.add(repoUrl)
    }
    onSelectionChange(newSelection)
  }

  return (
    <div>
      {/* Filters */}
      <div style={{
        display: 'flex',
        gap: '1rem',
        marginBottom: '1rem',
        flexWrap: 'wrap',
        alignItems: 'center'
      }}>
        <div style={{ flex: 1, minWidth: '200px' }}>
          <input
            type="text"
            placeholder="Search repositories..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '0.5rem',
              borderRadius: '4px',
              border: '1px solid #ced4da',
              fontSize: '0.875rem'
            }}
          />
        </div>

        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value as any)}
          style={{
            padding: '0.5rem',
            borderRadius: '4px',
            border: '1px solid #ced4da',
            fontSize: '0.875rem'
          }}
        >
          <option value="all">All Sizes</option>
          <option value="small">Small (&lt;5MB)</option>
          <option value="medium">Medium (5-50MB)</option>
          <option value="large">Large (&gt;50MB)</option>
        </select>

        <select
          value={languageFilter}
          onChange={(e) => setLanguageFilter(e.target.value)}
          style={{
            padding: '0.5rem',
            borderRadius: '4px',
            border: '1px solid #ced4da',
            fontSize: '0.875rem'
          }}
        >
          <option value="all">All Languages</option>
          {languages.map(lang => (
            <option key={lang} value={lang}>{lang}</option>
          ))}
        </select>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            type="button"
            onClick={handleSelectAll}
            style={{
              padding: '0.5rem 1rem',
              fontSize: '0.875rem',
              border: '1px solid #ced4da',
              borderRadius: '4px',
              background: '#fff',
              cursor: 'pointer'
            }}
          >
            Select All
          </button>
          <button
            type="button"
            onClick={handleDeselectAll}
            style={{
              padding: '0.5rem 1rem',
              fontSize: '0.875rem',
              border: '1px solid #ced4da',
              borderRadius: '4px',
              background: '#fff',
              cursor: 'pointer'
            }}
          >
            Deselect All
          </button>
        </div>
      </div>

      {/* Repository List */}
      <div style={{
        maxHeight: '400px',
        overflowY: 'auto',
        border: '1px solid #ced4da',
        borderRadius: '6px',
        padding: '0.5rem'
      }}>
        {filteredRepos.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#6c757d' }}>
            No repositories found matching filters
          </div>
        ) : (
          filteredRepos.map(repo => {
            const isSelected = selectedRepos.has(repo.clone_url)
            const isLarge = repo.size_mb >= 50

            return (
              <div
                key={repo.clone_url}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '0.75rem',
                  borderBottom: '1px solid #e9ecef',
                  cursor: 'pointer',
                  background: isSelected ? 'rgba(40, 167, 69, 0.1)' : 'transparent',
                  transition: 'background 0.2s'
                }}
                onClick={() => handleToggleRepo(repo.clone_url)}
              >
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => handleToggleRepo(repo.clone_url)}
                  onClick={(e) => e.stopPropagation()}
                  style={{ marginRight: '0.75rem' }}
                />
                
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                    <span style={{ fontWeight: 'bold', fontSize: '0.9rem' }}>{repo.name}</span>
                    {repo.private && (
                      <span style={{ fontSize: '0.75rem', color: '#6c757d' }}>🔒 Private</span>
                    )}
                    {isLarge && (
                      <span style={{ fontSize: '0.75rem', color: '#ffc107' }}>⚠️ Large</span>
                    )}
                  </div>
                  
                  <div style={{ fontSize: '0.75rem', color: '#6c757d', marginBottom: '0.25rem' }}>
                    {repo.full_name}
                  </div>
                  
                  {repo.description && (
                    <div style={{ fontSize: '0.75rem', color: '#6c757d', marginBottom: '0.25rem' }}>
                      {repo.description}
                    </div>
                  )}
                  
                  <div style={{ display: 'flex', gap: '1rem', fontSize: '0.75rem', color: '#6c757d' }}>
                    {repo.language && <span>📝 {repo.language}</span>}
                    <span>📦 {repo.size_mb.toFixed(1)} MB</span>
                    <span>⭐ {repo.stargazers_count}</span>
                    <span>🍴 {repo.forks_count}</span>
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>

      {/* Selection Summary */}
      <div style={{
        marginTop: '1rem',
        padding: '0.75rem',
        background: 'rgba(40, 167, 69, 0.1)',
        borderRadius: '6px',
        fontSize: '0.875rem',
        textAlign: 'center'
      }}>
        <strong>{selectedRepos.size}</strong> of <strong>{filteredRepos.length}</strong> repositories selected
        {filteredRepos.length < repositories.length && (
          <span style={{ color: '#6c757d' }}> (filtered from {repositories.length} total)</span>
        )}
      </div>
    </div>
  )
}
