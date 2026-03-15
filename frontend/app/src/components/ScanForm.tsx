import { useState, useEffect } from 'react'
import { FrontendConfig } from '../hooks/useConfig'
import ScannerSelector from './ScannerSelector'

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

const CONTAINER_REGISTRY_PATTERN = /^(?:[a-zA-Z0-9.-]+(?::\d+)?\/)?[a-z0-9]+(?:[._-][a-z0-9]+)*(?:\/[a-z0-9]+(?:[._-][a-z0-9]+)*)*(?::[\w][\w.-]{0,127})?(?:@sha256:[a-f0-9]{64})?$/

const isContainerRegistry = (value: string): boolean => {
  if (!value || value.startsWith('/') || value.startsWith('./') || value.startsWith('../')) return false
  if (value.startsWith('http://') || value.startsWith('https://')) return false
  return CONTAINER_REGISTRY_PATTERN.test(value.trim())
}

const isDockerHubImage = (value: string): boolean => {
  const trimmed = value.trim()
  if (!trimmed.includes('/')) return true  // Unqualified = Docker Hub
  const first = trimmed.split('/')[0]
  const hasRegistry = first.includes('.') || first.includes(':')
  if (!hasRegistry) return true  // Unqualified = Docker Hub
  return first === 'docker.io'  // Explicit docker.io = Docker Hub
}

function isGitUrl(url: string): boolean {
  if (!url || !url.trim()) return false
  return GIT_URL_PATTERNS.some(pattern => pattern.test(url.trim()))
}

export default function ScanForm({ onScanStart, config }: ScanFormProps) {
  // Get available scan types from config (backend-driven!)
  const scanTypesConfig = config?.features.scan_types ?? {}
  const gitOnly = config?.features.git_only ?? false
  const localPathsAllowed = config?.features.local_paths ?? true
  const metadataCollection = config?.features.metadata_collection ?? 'optional'
  
  // Get enabled scan types
  const enabledScanTypes = Object.entries(scanTypesConfig)
    .filter(([_, config]) => config.enabled)
    .map(([key, _]) => key)
  
  // Default to first available type
  const defaultScanType = enabledScanTypes[0] || 'code'
  
  const [scanType, setScanType] = useState<string>(defaultScanType)
  const [target, setTarget] = useState('')
  const [gitBranch, setGitBranch] = useState('')
  const [availableBranches, setAvailableBranches] = useState<string[]>([])
  const [loadingBranches, setLoadingBranches] = useState(false)
  const [branchError, setBranchError] = useState<string | null>(null)
  const [targetTypeInfo, setTargetTypeInfo] = useState<{
    target_type: string
    display_name: string
    icon: string
    action: string
    cleanup?: string
    target_url: string
  } | null>(null)
  const [loadingTargetType, setLoadingTargetType] = useState(false)
  const [ciMode, setCiMode] = useState(false)
  const [findingPolicy, setFindingPolicy] = useState('')
  const [collectMetadata, setCollectMetadata] = useState(metadataCollection === 'always')
  const [selectedScanners, setSelectedScanners] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const isScanDisabled = loading || selectedScanners.length === 0
  const scanDisabledReason = selectedScanners.length === 0
    ? 'Bitte wähle mindestens einen Scanner aus.'
    : undefined
  
  // Detect target type when target or scanType changes (Backend determines target type)
  useEffect(() => {
    if (target.trim() && scanType) {
      setLoadingTargetType(true)
      const detectTargetType = async () => {
        try {
          // Use backend scan_type for detect-target-type endpoint
          const scanTypeConfig = scanTypesConfig[scanType]
          const backendScanType = scanTypeConfig?.backend_value || 'repository'
          const { apiFetch } = await import('../utils/apiClient')
          const res = await apiFetch(`/api/v1/scans/detect-target-type?scan_type=${encodeURIComponent(backendScanType)}&target_url=${encodeURIComponent(target.trim())}`)
          if (res.ok) {
            const data = await res.json()
            setTargetTypeInfo(data)
          } else {
            setTargetTypeInfo(null)
          }
        } catch (err) {
          console.warn('Failed to detect target type:', err)
          setTargetTypeInfo(null)
        } finally {
          setLoadingTargetType(false)
        }
      }
      
      // Debounce: wait 300ms after user stops typing
      const timeoutId = setTimeout(detectTargetType, 300)
      return () => clearTimeout(timeoutId)
    } else {
      setTargetTypeInfo(null)
      setLoadingTargetType(false)
    }
  }, [target, scanType])

  // Use targetTypeInfo from backend instead of local detection
  const isGitRepo = targetTypeInfo?.target_type === 'git_repo'
  const isImageTarget = targetTypeInfo?.target_type === 'container_registry'
  const isLocalPath = targetTypeInfo?.target_type === 'local_mount'

  // Fetch branches when Git URL is detected
  useEffect(() => {
    if (isGitRepo && target.trim()) {
      setLoadingBranches(true)
      setBranchError(null)
      setAvailableBranches([])
      setGitBranch('') // Reset branch selection
      
      const fetchBranches = async () => {
        try {
          const { apiFetch } = await import('../utils/apiClient')
          const res = await apiFetch(`/api/git/branches?url=${encodeURIComponent(target.trim())}`)
          if (!res.ok) {
            const errorData = await res.json().catch(() => ({ detail: 'Failed to fetch branches' }))
            throw new Error(errorData.detail || 'Failed to fetch branches')
          }
          const data = await res.json()
          const branches = data.branches || []
          const defaultBranch = data.default
          
          setAvailableBranches(branches)
          
          // Auto-select default branch if available (user can change it if needed)
          if (defaultBranch) {
            setGitBranch(defaultBranch)
          }
          setLoadingBranches(false)
        } catch (err: any) {
          console.warn('Failed to fetch branches:', err)
          setBranchError(err.message || 'Could not fetch branches. You can still enter a branch name manually.')
          setLoadingBranches(false)
          // Don't show error to user - they can still enter branch manually
        }
      }
      
      fetchBranches()
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
      if (gitOnly && scanType === 'code' && !isGitUrl(cleanTarget) && !isContainerRegistry(cleanTarget)) {
        throw new Error('Production Mode: Only Git repository URLs or Docker Hub images are allowed. Local paths are not permitted.')
      }

      if (gitOnly && (scanType === 'code' || scanType === 'image') && isContainerRegistry(cleanTarget) && !isDockerHubImage(cleanTarget)) {
        throw new Error('Production Mode: Only Docker Hub images are allowed (use docker.io/... or unqualified image names).')
      }
      
      // Validate: Local paths not allowed if disabled
      if (!localPathsAllowed && targetTypeInfo?.target_type === 'local_mount') {
        throw new Error('Local paths are not allowed. Please use a Git repository URL or container registry image.')
      }

      // Generate scan name from target
      const scanName = scanType === 'network' 
        ? `Network Scan - ${cleanTarget || 'network'}`
        : isGitUrl(cleanTarget)
        ? cleanTarget.split('/').pop()?.replace('.git', '') || 'Git Repository Scan'
        : cleanTarget.split('/').pop() || 'Security Scan'

      // Build config object
      const scanConfig: any = {}
      if (cleanGitBranch) {
        scanConfig.git_branch = cleanGitBranch
      }
      if (cleanFindingPolicy) {
        scanConfig.finding_policy = cleanFindingPolicy
      }
      if (collectMetadata) {
        scanConfig.collect_metadata = collectMetadata
      }
      if (ciMode) {
        scanConfig.ci_mode = ciMode
      }

      // Get backend scan_type from config (backend-driven!)
      const scanTypeConfig = scanTypesConfig[scanType]
      const backendScanType = scanTypeConfig?.backend_value || 'repository'

      const { apiFetch } = await import('../utils/apiClient')
      const response = await apiFetch('/api/v1/scans/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: scanName,
          description: `Security scan for ${scanTypeConfig?.label || scanType} target`,
          scan_type: backendScanType,
          target_url: scanType === 'network' ? 'network' : cleanTarget,
          // target_type wird automatisch vom Backend bestimmt - NICHT hardcoden!
          config: Object.keys(scanConfig).length > 0 ? scanConfig : undefined,
          scanners: selectedScanners.length > 0 ? selectedScanners : [],
          tags: [],
          metadata: collectMetadata ? { collect_metadata: true } : {},
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

      // Parse the response to get the scan data
      const scanData = await response.json()
      
      // Convert new API format to old format for compatibility
      const scanStatus: ScanStatusData = {
        status: scanData.status === 'pending' ? 'idle' : 
                scanData.status === 'running' ? 'running' :
                scanData.status === 'completed' ? 'done' :
                scanData.status === 'failed' ? 'error' : 'idle',
        scan_id: scanData.id,
        results_dir: null, // Will be set when scan completes
        started_at: scanData.started_at || null,
        error_code: scanData.status === 'failed' ? 1 : null,
        error_message: scanData.status === 'failed' ? 'Scan failed' : null,
      }
      
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
          {Object.entries(scanTypesConfig)
            .filter(([_, typeConfig]) => typeConfig.enabled)
            .map(([frontendValue, typeConfig]) => (
              <label key={frontendValue}>
                <input
                  type="radio"
                  value={frontendValue}
                  checked={scanType === frontendValue}
                  onChange={(e) => setScanType(e.target.value)}
                />
                {typeConfig.label}
              </label>
            ))}
        </div>
        {gitOnly && (
          <small style={{ display: 'block', marginTop: '0.5rem', color: '#856404', fontSize: '0.875rem' }}>
            ⚠️ Production Mode: Only Git repositories or Docker Hub container images are allowed
          </small>
        )}
      </div>

      {scanType === 'code' && isLocalPath && (
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
            Target {scanType === 'code' ? (gitOnly ? '(Git URL oder Container Registry)' : '(Path, Git URL oder Container Registry)') : scanType === 'image' ? '(Container Registry)' : '(URL)'}
          </label>
          <input
            id="target"
            type="text"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            onBlur={(e) => setTarget(e.target.value.trim())} // Auto-trim on blur
            placeholder={scanType === 'code' ? (gitOnly ? 'https://github.com/user/repo oder nginx:latest' : '/path/to/project, https://github.com/user/repo oder nginx:latest') : scanType === 'image' ? 'nginx:latest oder ghcr.io/org/image:tag' : 'https://example.com'}
            required
            style={{
              borderColor: isGitRepo || isImageTarget ? '#28a745' : isLocalPath && !localPathsAllowed ? '#dc3545' : undefined,
            }}
          />
          {isLocalPath && !localPathsAllowed && (
            <small style={{ display: 'block', marginTop: '0.5rem', color: '#dc3545', fontSize: '0.875rem' }}>
              ❌ Local paths are not allowed in Production Mode. Please use a Git repository URL (GitHub/GitLab) or a container registry image.
            </small>
          )}
          {isImageTarget && gitOnly && !isDockerHubImage(target) && (
            <small style={{ display: 'block', marginTop: '0.5rem', color: '#dc3545', fontSize: '0.875rem' }}>
              ❌ Production Mode: Only Docker Hub images are allowed (docker.io/... or unqualified image names).
            </small>
          )}
          {loadingTargetType && target.trim() && (
            <div style={{
              marginTop: '0.75rem',
              padding: '0.75rem',
              background: 'rgba(108, 117, 125, 0.1)',
              border: '1px solid #6c757d',
              borderRadius: '6px',
              fontSize: '0.875rem',
              color: '#495057'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span>🔄</span>
                <span>Analyzing target...</span>
              </div>
            </div>
          )}
          {targetTypeInfo && !loadingTargetType && (
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
                <span>{targetTypeInfo.icon}</span>
                <span>Target detected: {targetTypeInfo.display_name}</span>
              </div>
              <div style={{
                marginBottom: '0.5rem',
                padding: '0.5rem',
                background: 'rgba(255, 255, 255, 0.3)',
                borderRadius: '4px',
                fontFamily: 'monospace',
                fontSize: '0.8rem',
                wordBreak: 'break-all'
              }}>
                {targetTypeInfo.target_url}
              </div>
              <ul style={{ margin: 0, paddingLeft: '1.25rem', lineHeight: '1.6' }}>
                <li>Type: {targetTypeInfo.target_type}</li>
                <li>Action: {targetTypeInfo.action}</li>
                {targetTypeInfo.cleanup && (
                  <li>Cleanup: {targetTypeInfo.cleanup}</li>
                )}
              </ul>
            </div>
          )}
          {isGitRepo && (
            <>
              <div className="form-group" style={{ marginTop: '0.75rem' }}>
                <label htmlFor="git-branch">
                  Git Branch {availableBranches.length > 0 ? '(auto-detected)' : '(optional)'}
                </label>
                {loadingBranches ? (
                  <div style={{ 
                    padding: '0.5rem', 
                    color: '#6c757d', 
                    fontSize: '0.875rem',
                    fontStyle: 'italic'
                  }}>
                    🔄 Loading branches...
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
                    ? 'Default branch is automatically selected. You can choose a different branch.'
                    : 'Leave empty for default branch (usually "main" or "master")'}
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

      <ScannerSelector
        scanType={scanType}
        selectedScanners={selectedScanners}
        onSelectionChange={setSelectedScanners}
      />

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

      <span title={scanDisabledReason} style={{ display: 'inline-block' }}>
        <button type="submit" className="primary" disabled={isScanDisabled}>
          {loading ? 'Starting...' : ' Start Scan'}
        </button>
      </span>
    </form>
  )
}
