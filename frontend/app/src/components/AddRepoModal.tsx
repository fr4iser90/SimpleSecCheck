interface RepoFormData {
  repo_url: string
  repo_owner: string
  repo_name: string
  branch: string
  auto_scan_enabled: boolean
  scan_on_push: boolean
  scan_frequency: string
}

interface AddRepoModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (e: React.FormEvent) => void
  formData: RepoFormData
  onFormDataChange: (data: RepoFormData) => void
}

export default function AddRepoModal({ isOpen, onClose, onSubmit, formData, onFormDataChange }: AddRepoModalProps) {
  if (!isOpen) return null

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0, 0, 0, 0.85)',
      backdropFilter: 'blur(8px)',
      WebkitBackdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div style={{
        background: 'rgba(20, 20, 30, 0.95)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        padding: '2rem',
        borderRadius: '8px',
        width: '90%',
        maxWidth: '500px',
        border: '1px solid var(--glass-border-dark)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)'
      }}>
        <h2 style={{ marginTop: 0 }}>Add GitHub Repository</h2>
        <form onSubmit={onSubmit}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem' }}>Repository URL *</label>
            <input
              type="text"
              required
              placeholder="https://github.com/user/repo"
              value={formData.repo_url}
              onChange={(e) => {
                const url = e.target.value
                const match = url.match(/github\.com\/([^\/]+)\/([^\/\s\.]+)/)
                if (match) {
                  const owner = match[1]
                  const repoName = match[2].replace('.git', '')
                  onFormDataChange({ ...formData, repo_url: url, repo_owner: owner, repo_name: repoName })
                } else {
                  onFormDataChange({ ...formData, repo_url: url })
                }
              }}
              style={{ width: '100%' }}
            />
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem' }}>
              Repository Owner (Optional)
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginLeft: '0.5rem', display: 'block', marginTop: '0.25rem' }}>
                GitHub username/organization (z.B. "fr4iser90") - wird automatisch aus URL extrahiert
              </span>
            </label>
            <input
              type="text"
              placeholder="owner (wird automatisch ausgefüllt)"
              value={formData.repo_owner}
              onChange={(e) => onFormDataChange({ ...formData, repo_owner: e.target.value })}
              style={{ width: '100%' }}
              disabled={formData.repo_url.includes('github.com')}
            />
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem' }}>
              Repository Name (Optional)
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginLeft: '0.5rem', display: 'block', marginTop: '0.25rem' }}>
                Nur der Repo-Name (z.B. "my-repo"), NICHT "owner/repo" - wird automatisch aus URL extrahiert
              </span>
            </label>
            <input
              type="text"
              placeholder="repo-name (wird automatisch ausgefüllt)"
              value={formData.repo_name}
              onChange={(e) => onFormDataChange({ ...formData, repo_name: e.target.value })}
              style={{ width: '100%' }}
              disabled={formData.repo_url.includes('github.com')}
            />
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem' }}>Branch</label>
            <input
              type="text"
              required
              value={formData.branch}
              onChange={(e) => onFormDataChange({ ...formData, branch: e.target.value })}
              style={{ width: '100%' }}
            />
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={formData.auto_scan_enabled}
                onChange={(e) => onFormDataChange({ ...formData, auto_scan_enabled: e.target.checked })}
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
                    onChange={(e) => onFormDataChange({ ...formData, scan_on_push: e.target.checked })}
                  />
                  <span>Scan on Push</span>
                </label>
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem' }}>Scan Frequency</label>
                <select
                  value={formData.scan_frequency}
                  onChange={(e) => onFormDataChange({ ...formData, scan_frequency: e.target.value })}
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
            <button type="button" onClick={onClose}>Cancel</button>
            <button type="submit" className="primary">Add Repository</button>
          </div>
        </form>
      </div>
    </div>
  )
}
