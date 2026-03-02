import { useState, useEffect } from 'react'
import { FrontendConfig } from '../hooks/useConfig'

interface ScanStatusData {
  status: 'idle' | 'running' | 'done' | 'error'
  scan_id: string | null
  results_dir: string | null
  started_at: string | null
  error_code?: number | null
  error_message?: string | null
}

interface ScanFormProps {
  onScanStart: (scanStatus: ScanStatusData) => void
  config: FrontendConfig | null
}

// Git URL patterns for detection
const GIT_URL_PATTERNS = [
  /^https?:\/\/(www\.)?github\.com\/[\w\-\.]+\/[\w\-\.]+/,
  /^https?:\/\/(www\.)?gitlab\.com\/[\w\-\.]+\/[\w\-\.]+/,
  /^git@(github|gitlab)\.com:[\w\-\.]+\/[\w\-\.]+\.git$/,
]

function isGitUrl(url: string): boolean {
  if (!url || !url.trim()) return false
  return GIT_URL_PATTERNS.some(pattern => pattern.test(url.trim()))
}

export default function ScanForm({ onScanStart, config }: ScanFormProps) {
  // Get available scan types from config
  const availableScanTypes = config?.features.scan_types ?? { code: true, website: true, network: true }
  const gitOnly = config?.features.git_only ?? false
  const localPathsAllowed = config?.features.local_paths ?? true
  const metadataCollection = config?.features.metadata_collection ?? 'optional'
  
  // Default to 'code' if available, otherwise first available type
  const defaultScanType = availableScanTypes.code ? 'code' : 
    availableScanTypes.website ? 'website' : 
    availableScanTypes.network ? 'network' : 'code'
  
  const [scanType, setScanType] = useState<'code' | 'website' | 'network'>(defaultScanType)
  const [target, setTarget] = useState('')
  const [gitBranch, setGitBranch] = useState('')
  const [availableBranches, setAvailableBranches] = useState<string[]>([])
  const [loadingBranches, setLoadingBranches] = useState(false)
  const [branchError, setBranchError] = useState<string | null>(null)
  const [ciMode, setCiMode] = useState(false)
  const [findingPolicy, setFindingPolicy] = useState('')
  const [collectMetadata, setCollectMetadata] = useState(metadataCollection === 'always')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Detect if target is a Git URL
  const isGitRepo = scanType === 'code' && isGitUrl(target)
  
  // In production (git_only), only allow Git URLs
  const isLocalPath = scanType === 'code' && target.trim() && !isGitUrl(target) && target.trim().startsWith('/')
  
  // Fetch branches when Git URL is detected
  useEffect(() => {
    if (isGitRepo && target.trim()) {
      setLoadingBranches(true)
      setBranchError(null)
      setAvailableBranches([])
      setGitBranch('') // Reset branch selection
      
      fetch(`/api/git/branches?url=${encodeURIComponent(target.trim())}`)
        .then(async (res) => {
          if (!res.ok) {
            const errorData = await res.json().catch(() => ({ detail: 'Failed to fetch branches' }))
            throw new Error(errorData.detail || 'Failed to fetch branches')
          }
          return res.json()
        })
        .then((data) => {
          const branches = data.branches || []
          const defaultBranch = data.default
          
          setAvailableBranches(branches)
          
          // Auto-select default branch if available (user can change it if needed)
          if (defaultBranch && !gitBranch) {
            setGitBranch(defaultBranch)
          }
          setLoadingBranches(false)
        })
        .catch((err) => {
          console.warn('Failed to fetch branches:', err)
          setBranchError(err.message || 'Could not fetch branches. You can still enter a branch name manually.')
          setLoadingBranches(false)
          // Don't show error to user - they can still enter branch manually
        })
    } else {
      // Reset when not a Git repo
      setAvailableBranches([])
      setBranchError(null)
      setGitBranch('')
    }
  }, [isGitRepo, target])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      // Clean whitespace from target and finding policy
      const cleanTarget = target.trim()
      const cleanGitBranch = gitBranch.trim() || null
      const cleanFindingPolicy = findingPolicy.trim() || null
      
      // Validate: In production (git_only), only Git URLs are allowed
      if (gitOnly && scanType === 'code' && !isGitUrl(cleanTarget)) {
        throw new Error('Production Mode: Only Git repository URLs (GitHub/GitLab) are allowed. Local paths are not permitted.')
      }
      
      // Validate: Local paths not allowed if disabled
      if (!localPathsAllowed && scanType === 'code' && isLocalPath) {
        throw new Error('Local paths are not allowed. Please use a Git repository URL.')
      }

      const response = await fetch('/api/scan/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          type: scanType,
          target: scanType === 'network' ? 'network' : cleanTarget,
          git_branch: cleanGitBranch,
          ci_mode: ciMode,
          finding_policy: cleanFindingPolicy,
          collect_metadata: collectMetadata,
        }),
      })

      // Check if response is JSON
      const contentType = response.headers.get('content-type')
      if (!contentType || !contentType.includes('application/json')) {
        const text = await response.text()
        throw new Error(`Server error: ${text.substring(0, 200)}`)
      }

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to start scan')
      }

      // Parse the response to get the status
      const scanStatus = await response.json()
      
      // Navigate to scan view with the status
      onScanStart(scanStatus)
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
          {availableScanTypes.code && (
            <label>
              <input
                type="radio"
                value="code"
                checked={scanType === 'code'}
                onChange={(e) => setScanType(e.target.value as 'code')}
              />
              Code
            </label>
          )}
          {availableScanTypes.website && (
            <label>
              <input
                type="radio"
                value="website"
                checked={scanType === 'website'}
                onChange={(e) => setScanType(e.target.value as 'website')}
              />
              Website
            </label>
          )}
          {availableScanTypes.network && (
            <label>
              <input
                type="radio"
                value="network"
                checked={scanType === 'network'}
                onChange={(e) => setScanType(e.target.value as 'network')}
              />
              Network
            </label>
          )}
        </div>
        {gitOnly && (
          <small style={{ display: 'block', marginTop: '0.5rem', color: '#856404', fontSize: '0.875rem' }}>
            ⚠️ Production Mode: Only Git repository scans are allowed (GitHub/GitLab URLs)
          </small>
        )}
      </div>

      {scanType === 'code' && !isGitRepo && isLocalPath && (
        <div className="form-group">
          <label>
            <input
              type="checkbox"
              checked={ciMode}
              onChange={(e) => setCiMode(e.target.checked)}
            />
            CI Mode (scan only tracked files)
          </label>
          <small style={{ display: 'block', marginTop: '0.5rem', color: '#6c757d', fontSize: '0.875rem' }}>
            Scans only files tracked by Git (ignores untracked files). Only available for local Git repositories.
          </small>
        </div>
      )}

      {scanType !== 'network' && (
        <div className="form-group">
          <label htmlFor="target">
            Target {scanType === 'code' ? (gitOnly ? '(Git URL only)' : '(Path oder Git URL)') : '(URL)'}
          </label>
          <input
            id="target"
            type="text"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            onBlur={(e) => setTarget(e.target.value.trim())} // Auto-trim on blur
            placeholder={scanType === 'code' ? (gitOnly ? 'https://github.com/user/repo' : '/path/to/project oder https://github.com/user/repo') : 'https://example.com'}
            required
            style={{
              borderColor: isGitRepo ? '#28a745' : isLocalPath && !localPathsAllowed ? '#dc3545' : undefined,
            }}
          />
          {isLocalPath && !localPathsAllowed && (
            <small style={{ display: 'block', marginTop: '0.5rem', color: '#dc3545', fontSize: '0.875rem' }}>
              ❌ Local paths are not allowed in Production Mode. Please use a Git repository URL (GitHub/GitLab).
            </small>
          )}
          {isGitRepo && (
            <>
              <div style={{
                marginTop: '0.75rem',
                padding: '0.75rem',
                background: 'rgba(40, 167, 69, 0.1)',
                border: '1px solid #28a745',
                borderRadius: '6px',
                fontSize: '0.875rem',
                color: '#155724'
              }}>
                <div style={{ fontWeight: 'bold', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span>🔗</span>
                  <span>Git Repository erkannt</span>
                </div>
                <ul style={{ margin: 0, paddingLeft: '1.25rem', lineHeight: '1.6' }}>
                  <li>Repository wird automatisch geklont</li>
                  <li>Scan wird auf geklontem Projekt ausgeführt</li>
                  <li>Temporäres Projekt wird nach Scan automatisch gelöscht</li>
                </ul>
              </div>
              <div className="form-group" style={{ marginTop: '0.75rem' }}>
                <label htmlFor="git-branch">
                  Git Branch {availableBranches.length > 0 ? '(automatisch erkannt)' : '(optional)'}
                </label>
                {loadingBranches ? (
                  <div style={{ 
                    padding: '0.5rem', 
                    color: '#6c757d', 
                    fontSize: '0.875rem',
                    fontStyle: 'italic'
                  }}>
                    🔄 Branches werden geladen...
                  </div>
                ) : availableBranches.length > 0 ? (
                  <select
                    id="git-branch"
                    value={gitBranch}
                    onChange={(e) => setGitBranch(e.target.value)}
                    style={{
                      fontSize: '0.875rem',
                      width: '100%',
                      padding: '0.5rem',
                      borderRadius: '4px',
                      border: '1px solid #ced4da'
                    }}
                  >
                    {availableBranches.map((branch) => (
                      <option key={branch} value={branch}>
                        {branch}
                      </option>
                    ))}
                  </select>
                ) : (
                  <>
                    <input
                      id="git-branch"
                      type="text"
                      value={gitBranch}
                      onChange={(e) => setGitBranch(e.target.value)}
                      onBlur={(e) => setGitBranch(e.target.value.trim())}
                      placeholder="main, master, develop, etc. (leer = Standard-Branch)"
                      style={{
                        fontSize: '0.875rem'
                      }}
                    />
                    {branchError && (
                      <small style={{ display: 'block', marginTop: '0.5rem', color: '#856404', fontSize: '0.875rem' }}>
                        ⚠️ {branchError}
                      </small>
                    )}
                  </>
                )}
                <small style={{ display: 'block', marginTop: '0.5rem', color: '#6c757d', fontSize: '0.875rem' }}>
                  {availableBranches.length > 0 
                    ? 'Standard-Branch ist automatisch ausgewählt. Du kannst einen anderen Branch wählen.'
                    : 'Leer lassen für Standard-Branch (meistens "main" oder "master")'}
                </small>
              </div>
            </>
          )}
        </div>
      )}

      <div className="form-group">
        <label htmlFor="finding-policy">Finding Policy (optional)</label>
        <input
          id="finding-policy"
          type="text"
          value={findingPolicy}
          onChange={(e) => setFindingPolicy(e.target.value)}
          onBlur={(e) => setFindingPolicy(e.target.value.trim())} // Auto-trim on blur
          placeholder="config/finding-policy.json"
        />
      </div>

      {metadataCollection === 'optional' && (
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
      )}
      {metadataCollection === 'always' && (
        <div style={{
          marginBottom: '1rem',
          padding: '0.75rem',
          background: 'rgba(40, 167, 69, 0.1)',
          border: '1px solid #28a745',
          borderRadius: '6px',
          fontSize: '0.875rem',
          color: '#155724'
        }}>
          ℹ️ Metadata collection is always enabled in Production Mode for scan deduplication.
        </div>
      )}

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

      <button type="submit" className="primary" disabled={loading}>
        {loading ? 'Starting...' : ' Start Scan'}
      </button>
    </form>
  )
}
