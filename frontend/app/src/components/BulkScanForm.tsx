import { useState, useEffect } from 'react'
import { useConfig } from '../hooks/useConfig'
import RateLimitIndicator from './RateLimitIndicator'
import RepositorySelector, { Repository } from './RepositorySelector'

interface BulkScanFormProps {
  onBatchStart: (batchId: string) => void
}

type InputMethod = 'github' | 'urls'

export default function BulkScanForm({ onBatchStart }: BulkScanFormProps) {
  const { config } = useConfig()
  const defaultFindingPolicyPath = config?.scan_defaults?.default_finding_policy_path ?? '.scanning/finding-policy.json'
  const applyFindingPolicyByDefault = config?.scan_defaults?.finding_policy_apply_by_default ?? true

  const [scanType, setScanType] = useState<'code' | 'image' | 'website' | 'network'>('code')
  const [inputMethod, setInputMethod] = useState<InputMethod>('github')
  const [githubUsername, setGithubUsername] = useState('')
  const [includePrivate, setIncludePrivate] = useState(false)
  const [loadingRepos, setLoadingRepos] = useState(false)
  const [repositories, setRepositories] = useState<Repository[]>([])
  const [selectedRepos, setSelectedRepos] = useState<Set<string>>(new Set())
  const [urlsText, setUrlsText] = useState('')
  const [gitBranch, setGitBranch] = useState('')
  const [findingPolicy, setFindingPolicy] = useState(applyFindingPolicyByDefault ? defaultFindingPolicyPath : '')
  const [collectMetadata, setCollectMetadata] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load repositories when GitHub username changes
  useEffect(() => {
    if (inputMethod === 'github' && githubUsername.trim() && scanType === 'code') {
      loadRepositories()
    } else {
      setRepositories([])
      setSelectedRepos(new Set())
    }
  }, [githubUsername, inputMethod, scanType, includePrivate])

  const loadRepositories = async () => {
    setLoadingRepos(true)
    setError(null)
    setRepositories([])
    setSelectedRepos(new Set())

    try {
      const params = new URLSearchParams({
        username: githubUsername.trim(),
        include_private: includePrivate.toString(),
        max_repos: '100'
      })

      const response = await fetch(`/api/github/repos?${params}`)
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to load repositories')
      }

      const data = await response.json()
      setRepositories(data.repositories || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load repositories')
      setRepositories([])
    } finally {
      setLoadingRepos(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Collect repository URLs
    let repoUrls: string[] = []
    
    if (inputMethod === 'github') {
      if (selectedRepos.size === 0) {
        setError('Please select at least one repository')
        return
      }
      repoUrls = Array.from(selectedRepos)
    } else {
      // Parse URLs from textarea
      const urls = urlsText
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0)
      
      if (urls.length === 0) {
        setError('Please enter at least one repository URL')
        return
      }
      repoUrls = urls
    }

    setLoading(true)

    try {
      const response = await fetch('/api/bulk/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          scan_type: scanType,
          repositories: repoUrls,
          git_branch: gitBranch.trim() || null,
          finding_policy: findingPolicy.trim() || null,
          collect_metadata: collectMetadata,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to start batch scan')
      }

      const batchProgress = await response.json()
      onBatchStart(batchProgress.batch_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="form-group">
        <label>Scan Type</label>
        <div className="radio-group">
          <label>
            <input
              type="radio"
              value="code"
              checked={scanType === 'code'}
              onChange={(e) => setScanType(e.target.value as 'code')}
            />
            Code
          </label>
          <label>
            <input
              type="radio"
              value="image"
              checked={scanType === 'image'}
              onChange={(e) => setScanType(e.target.value as 'image')}
            />
            Image
          </label>
          <label>
            <input
              type="radio"
              value="website"
              checked={scanType === 'website'}
              onChange={(e) => setScanType(e.target.value as 'website')}
            />
            Website
          </label>
          <label>
            <input
              type="radio"
              value="network"
              checked={scanType === 'network'}
              onChange={(e) => setScanType(e.target.value as 'network')}
            />
            Network
          </label>
        </div>
      </div>

      {scanType === 'code' && (
        <>
          <div className="form-group">
            <label>⚙️ Input Method</label>
            <div className="radio-group">
              <label>
                <input
                  type="radio"
                  value="github"
                  checked={inputMethod === 'github'}
                  onChange={() => setInputMethod('github')}
                />
                GitHub User/Org
              </label>
              <label>
                <input
                  type="radio"
                  value="urls"
                  checked={inputMethod === 'urls'}
                  onChange={() => setInputMethod('urls')}
                />
                Multiple URLs (paste)
              </label>
            </div>
          </div>

          {inputMethod === 'github' && (
            <>
              <RateLimitIndicator />

              <div className="form-group">
                <label htmlFor="github-username">GitHub Username/Organization</label>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <input
                    id="github-username"
                    type="text"
                    value={githubUsername}
                    onChange={(e) => setGithubUsername(e.target.value)}
                    placeholder="username or organization"
                    style={{ flex: 1 }}
                  />
                  <button
                    type="button"
                    onClick={loadRepositories}
                    disabled={loadingRepos || !githubUsername.trim()}
                    style={{
                      padding: '0.5rem 1rem',
                      border: '1px solid #ced4da',
                      borderRadius: '4px',
                      background: '#fff',
                      cursor: loadingRepos ? 'not-allowed' : 'pointer'
                    }}
                  >
                    {loadingRepos ? 'Loading...' : '🔍 Load'}
                  </button>
                </div>
              </div>

              {scanType === 'code' && (
                <div className="form-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={includePrivate}
                      onChange={(e) => setIncludePrivate(e.target.checked)}
                    />
                    Include Private Repositories (requires GitHub token)
                  </label>
                </div>
              )}

              {loadingRepos && (
                <div style={{ padding: '1rem', textAlign: 'center', color: '#6c757d' }}>
                  🔄 Loading repositories...
                </div>
              )}

              {repositories.length > 0 && (
                <div className="form-group">
                  <RepositorySelector
                    repositories={repositories}
                    selectedRepos={selectedRepos}
                    onSelectionChange={setSelectedRepos}
                  />
                </div>
              )}
            </>
          )}

          {inputMethod === 'urls' && (
            <div className="form-group">
              <label htmlFor="urls-text">Repository URLs (one per line)</label>
              <textarea
                id="urls-text"
                value={urlsText}
                onChange={(e) => setUrlsText(e.target.value)}
                placeholder="https://github.com/user/repo1&#10;https://github.com/user/repo2&#10;https://gitlab.com/user/repo3"
                rows={8}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '4px',
                  border: '1px solid #ced4da',
                  fontFamily: 'monospace',
                  fontSize: '0.875rem'
                }}
              />
              <small style={{ display: 'block', marginTop: '0.5rem', color: '#6c757d', fontSize: '0.875rem' }}>
                Enter one repository URL per line. Supports GitHub and GitLab URLs.
              </small>
            </div>
          )}

          <div className="form-group">
            <label htmlFor="git-branch">Git Branch (optional)</label>
            <input
              id="git-branch"
              type="text"
              value={gitBranch}
              onChange={(e) => setGitBranch(e.target.value)}
              placeholder="main, master, develop, etc."
            />
            <small style={{ display: 'block', marginTop: '0.5rem', color: '#6c757d', fontSize: '0.875rem' }}>
              Leave empty to use default branch for each repository
            </small>
          </div>

        </>
      )}

      <div className="form-group">
        <label htmlFor="finding-policy">Finding Policy (optional)</label>
        <input
          id="finding-policy"
          type="text"
          value={findingPolicy}
          onChange={(e) => setFindingPolicy(e.target.value)}
          placeholder={defaultFindingPolicyPath}
        />
        <small style={{ display: 'block', marginTop: '0.5rem', color: '#6c757d', fontSize: '0.875rem' }}>
          Path to finding policy file (relative to each repository root)
        </small>
      </div>

      <div className="form-group">
        <label>
          <input
            type="checkbox"
            checked={collectMetadata}
            onChange={(e) => setCollectMetadata(e.target.checked)}
          />
          Collect Metadata (optional - includes Git info, project path, etc.)
        </label>
        <small style={{ display: 'block', marginTop: '0.5rem', color: '#6c757d', fontSize: '0.875rem' }}>
          By default, no metadata is collected for privacy. Enable this to include project information in the scan report.
        </small>
      </div>

      {error && (
        <div style={{
          background: 'rgba(220, 53, 69, 0.2)',
          border: '1px solid #dc3545',
          borderRadius: '8px',
          padding: '1rem',
          marginBottom: '1rem',
          color: '#dc3545'
        }}>
          {error}
        </div>
      )}

      <button type="submit" className="primary" disabled={loading || (inputMethod === 'github' && selectedRepos.size === 0) || (inputMethod === 'urls' && !urlsText.trim())}>
        {loading ? 'Starting...' : `Start Batch Scan${inputMethod === 'github' && selectedRepos.size > 0 ? ` (${selectedRepos.size} repos)` : inputMethod === 'urls' && urlsText.trim() ? ` (${urlsText.split('\n').filter(l => l.trim()).length} repos)` : ''}`}
      </button>
    </form>
  )
}
