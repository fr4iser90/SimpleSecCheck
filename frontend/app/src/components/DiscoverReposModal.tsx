import Modal from './Modal'

interface DiscoverReposModalProps {
  isOpen: boolean
  onClose: () => void
  discoverUsername: string
  onDiscoverUsernameChange: (username: string) => void
  onDiscover: () => void
  discovering: boolean
  discoveredRepos: any[]
  selectedRepos: Set<string>
  onToggleRepoSelection: (repoFullName: string) => void
  onSelectAll: () => void
  onDeselectAll: () => void
  onAddSelected: () => void
  loading: boolean
}

export default function DiscoverReposModal({
  isOpen,
  onClose,
  discoverUsername,
  onDiscoverUsernameChange,
  onDiscover,
  discovering,
  discoveredRepos,
  selectedRepos,
  onToggleRepoSelection,
  onSelectAll,
  onDeselectAll,
  onAddSelected,
  loading
}: DiscoverReposModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="🔍 Discover GitHub Repositories" size="lg">
      <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
          Enter a GitHub username or organization name to find all their repositories.
        </p>
        
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
          <input
            type="text"
            placeholder="e.g. fr4iser90 or microsoft"
            value={discoverUsername}
            onChange={(e) => onDiscoverUsernameChange(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                onDiscover()
              }
            }}
            style={{ flex: 1 }}
          />
          <button 
            className="primary" 
            onClick={onDiscover}
            disabled={discovering || !discoverUsername.trim()}
          >
            {discovering ? 'Searching...' : 'Search'}
          </button>
        </div>

        {discoveredRepos.length > 0 && (
          <>
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              marginBottom: '1rem',
              paddingBottom: '1rem',
              borderBottom: '1px solid var(--glass-border-main)'
            }}>
              <div>
                <strong>Found {discoveredRepos.length} repositories</strong>
                {selectedRepos.size > 0 && (
                  <span style={{ marginLeft: '1rem', color: 'var(--color-pass)' }}>
                    {selectedRepos.size} selected
                  </span>
                )}
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  onClick={() => {
                    if (selectedRepos.size === discoveredRepos.length) {
                      onDeselectAll()
                    } else {
                      onSelectAll()
                    }
                  }}
                  style={{ fontSize: '0.85rem', padding: '0.5rem 1rem' }}
                >
                  {selectedRepos.size === discoveredRepos.length ? 'Deselect All' : 'Select All'}
                </button>
                <button
                  className="primary"
                  onClick={onAddSelected}
                  disabled={selectedRepos.size === 0 || loading}
                  style={{ fontSize: '0.85rem', padding: '0.5rem 1rem' }}
                >
                  Add Selected ({selectedRepos.size})
                </button>
              </div>
            </div>
            
            <div style={{ 
              maxHeight: '400px', 
              overflowY: 'auto',
              display: 'grid',
              gap: '0.5rem'
            }}>
              {discoveredRepos.map((repo) => (
                <label
                  key={repo.full_name}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '1rem',
                    padding: '1rem',
                    background: selectedRepos.has(repo.full_name) ? 'rgba(102, 126, 234, 0.2)' : 'rgba(0, 0, 0, 0.2)',
                    border: `1px solid ${selectedRepos.has(repo.full_name) ? 'var(--accent)' : 'var(--glass-border-main)'}`,
                    borderRadius: '6px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease'
                  }}
                >
                  <input
                    type="checkbox"
                    checked={selectedRepos.has(repo.full_name)}
                    onChange={() => onToggleRepoSelection(repo.full_name)}
                    style={{ width: '1.2rem', height: '1.2rem', cursor: 'pointer' }}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 'bold', marginBottom: '0.25rem' }}>
                      {repo.full_name}
                    </div>
                    {repo.description && (
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
                        {repo.description}
                      </div>
                    )}
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'flex', gap: '1rem' }}>
                      <span>⭐ {repo.stargazers_count || 0}</span>
                      <span>🍴 {repo.forks_count || 0}</span>
                      <span>🌿 {repo.default_branch || 'main'}</span>
                      <span>{repo.private ? '🔒 Private' : '🌐 Public'}</span>
                    </div>
                  </div>
                </label>
              ))}
            </div>
          </>
        )}

      <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', marginTop: '1.5rem' }}>
        <button type="button" onClick={onClose}>
          Close
        </button>
      </div>
    </Modal>
  )
}
