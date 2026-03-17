import { useState, useEffect } from 'react'
import { FrontendConfig } from '../hooks/useConfig'
import { useAuth } from '../hooks/useAuth'
import ScanStep from './ScanStep'
import ScannerCardGrid from './ScannerCardGrid'

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

/** True if container image reference is local (local Docker or local registry). Must match backend is_local_container_reference. */
function isLocalContainerReference(targetUrl: string): boolean {
  if (!targetUrl || !targetUrl.trim()) return false
  const s = targetUrl.trim().toLowerCase()
  if (s.startsWith('local/')) return true
  if (s.startsWith('localhost/') || s.startsWith('localhost:')) return true
  if (s.startsWith('127.0.0.1/') || s.startsWith('127.0.0.1:')) return true
  return false
}

function isGitUrl(url: string): boolean {
  if (!url || !url.trim()) return false
  return GIT_URL_PATTERNS.some(pattern => pattern.test(url.trim()))
}

export default function ScanForm({ onScanStart, config }: ScanFormProps) {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'

  // Get available scan types from config (backend-driven!)
  const scanTypesConfig = config?.features.scan_types ?? {}
  const gitOnly = config?.features.git_only ?? false
  const localPathsAllowed = config?.features.local_paths ?? true
  const metadataCollection = config?.features.metadata_collection ?? 'optional'
  const dangerousTargets = config?.features.dangerous_targets ?? []
  const allowLocalContainers = config?.features.allow_local_containers ?? true

  // No default scan type - will be auto-detected from target
  const [scanType, setScanType] = useState<string>('')
  const [target, setTarget] = useState('')
  const [scanTypeDetected, setScanTypeDetected] = useState(false) // Track if scan type was auto-detected
  const [showScanTypeSelection, setShowScanTypeSelection] = useState(false) // Only show if detection failed or user wants to override
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
  const [scanners, setScanners] = useState<any[]>([])
  const [loadingScanners, setLoadingScanners] = useState(false)
  const [scannerError, setScannerError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Auto-detect scan type and target type from target input
  useEffect(() => {
    if (target.trim()) {
      setLoadingTargetType(true)
      const detectScanAndTargetType = async () => {
        try {
          const { apiFetch } = await import('../utils/apiClient')
          // First, detect scan type from target
          const scanTypeRes = await apiFetch(`/api/v1/scans/detect-scan-type?target_url=${encodeURIComponent(target.trim())}`)
          if (scanTypeRes.ok) {
            const scanTypeData = await scanTypeRes.json()
            const suggestedScanType = scanTypeData.suggested_scan_type
            
            // Auto-set scan type if not already set or if different
            if (!scanType || scanType !== suggestedScanType) {
              setScanType(suggestedScanType)
              setScanTypeDetected(true)
            }
            
            // Use target type info from the response
            setTargetTypeInfo({
              target_type: scanTypeData.target_type,
              display_name: scanTypeData.display_name,
              icon: scanTypeData.icon,
              action: scanTypeData.action,
              cleanup: scanTypeData.cleanup,
              target_url: scanTypeData.target_url
            })
          } else {
            // If detection fails, show scan type selection
            setShowScanTypeSelection(true)
            setTargetTypeInfo(null)
          }
        } catch (err) {
          console.warn('Failed to detect scan/target type:', err)
          setShowScanTypeSelection(true)
          setTargetTypeInfo(null)
        } finally {
          setLoadingTargetType(false)
        }
      }
      
      // Debounce: wait 500ms after user stops typing
      const timeoutId = setTimeout(detectScanAndTargetType, 500)
      return () => clearTimeout(timeoutId)
    } else {
      // Reset when target is empty
      setTargetTypeInfo(null)
      setLoadingTargetType(false)
      setScanType('')
      setScanTypeDetected(false)
      setShowScanTypeSelection(false)
    }
  }, [target])
  
  // Detect target type when scanType changes (if user manually changed it)
  useEffect(() => {
    if (target.trim() && scanType && !scanTypeDetected) {
      setLoadingTargetType(true)
      const detectTargetType = async () => {
        try {
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
      
      const timeoutId = setTimeout(detectTargetType, 300)
      return () => clearTimeout(timeoutId)
    }
  }, [scanType, scanTypeDetected])

  // Use targetTypeInfo from backend instead of local detection
  const isGitRepo = targetTypeInfo?.target_type === 'git_repo'
  const isImageTarget = targetTypeInfo?.target_type === 'container_registry'
  const isLocalPath = targetTypeInfo?.target_type === 'local_mount'
  const isLocalPathRestrictedByRole = isLocalPath && localPathsAllowed && !isAdmin && dangerousTargets.includes('local_mount')
  const isLocalContainerRestrictedByRole = isImageTarget && isLocalContainerReference(target) && allowLocalContainers && !isAdmin
  const isScanDisabled = loading || selectedScanners.length === 0 || isLocalPathRestrictedByRole || isLocalContainerRestrictedByRole
  const scanDisabledReason = isLocalPathRestrictedByRole
    ? 'Local path scanning requires admin privileges.'
    : isLocalContainerRestrictedByRole
    ? 'Local container scanning (localhost / local registry) requires admin privileges.'
    : selectedScanners.length === 0
    ? 'Bitte wähle mindestens einen Scanner aus.'
    : undefined

  // Load scanners when scan type changes
  useEffect(() => {
    if (!scanType) {
      setScanners([])
      setSelectedScanners([])
      return
    }

    setLoadingScanners(true)
    setScannerError(null)
    
    const loadScanners = async () => {
      try {
        const response = await fetch(`/api/scanners?scan_type=${scanType}`)
        if (!response.ok) {
          throw new Error('Failed to load scanners')
        }
        const data = await response.json()
        const loadedScanners = data.scanners || []
        setScanners(loadedScanners)
        
        // Auto-select all enabled scanners by default (only if nothing selected yet)
        if (selectedScanners.length === 0 && loadedScanners.length > 0) {
          const enabledScanners = loadedScanners
            .filter((s: any) => s.enabled)
            .map((s: any) => s.name)
          setSelectedScanners(enabledScanners)
        }
      } catch (err) {
        setScannerError(err instanceof Error ? err.message : 'Failed to load scanners')
        console.error('Error loading scanners:', err)
      } finally {
        setLoadingScanners(false)
      }
    }
    
    loadScanners()
  }, [scanType])

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

  const handleScannerToggle = (scannerName: string) => {
    if (selectedScanners.includes(scannerName)) {
      setSelectedScanners(selectedScanners.filter(s => s !== scannerName))
    } else {
      setSelectedScanners([...selectedScanners, scannerName])
    }
  }

  const handleSelectAllScanners = () => {
    const enabledScanners = scanners
      .filter(s => s.enabled)
      .map(s => s.name)
    setSelectedScanners(enabledScanners)
  }

  const handleDeselectAllScanners = () => {
    setSelectedScanners([])
  }

  return (
    <form onSubmit={handleSubmit} className="scan-form">
      {/* Step 1: Target (FIRST - most important!) */}
      <ScanStep
        id="step-1"
        title="Target"
        trigger={targetTypeInfo ? targetTypeInfo.target_type : target}
        autoScroll={false}
        expanded={true}
        completed={!!targetTypeInfo && target.trim().length > 0}
        required={true}
      >
        <div className="form-group">
          <label htmlFor="target">
            Target (Git URL, Container Image, Local Path, Website URL, or Network Host)
          </label>
          <input
            id="target"
            type="text"
            value={target}
            onChange={(e) => {
              setTarget(e.target.value)
              setScanTypeDetected(false) // Reset detection flag when user types
            }}
            onBlur={(e) => setTarget(e.target.value.trim())}
            placeholder="https://github.com/user/repo, nginx:latest, /path/to/project, https://example.com, or 192.168.1.1"
            required
            style={{ fontSize: '1.1rem', padding: '1rem' }}
            className={isGitRepo || isImageTarget ? 'input-border-success' : (isLocalPath && !localPathsAllowed) || isLocalPathRestrictedByRole || isLocalContainerRestrictedByRole ? 'input-border-error' : ''}
          />
          {loadingTargetType && target.trim() && (
            <div className="glass form-info-box loading" style={{ marginTop: '0.75rem' }}>
              <div className="form-info-box-header">
                <span>🔄</span>
                <span>Analyzing target...</span>
              </div>
            </div>
          )}
          {targetTypeInfo && !loadingTargetType && (
            <div className="glass form-info-box success" style={{ marginTop: '0.75rem' }}>
              <div className="form-info-box-header">
                <span>{targetTypeInfo.icon}</span>
                <span>Target detected: {targetTypeInfo.display_name}</span>
                {scanTypeDetected && (
                  <span style={{ marginLeft: 'auto', fontSize: '0.875rem', color: 'var(--color-info)' }}>
                    Scan Type: {scanType}
                  </span>
                )}
              </div>
              <div className="form-target-url">
                {targetTypeInfo.target_url}
              </div>
              <ul className="form-info-box-list">
                <li>Type: {targetTypeInfo.target_type}</li>
                <li>Action: {targetTypeInfo.action}</li>
                {targetTypeInfo.cleanup && (
                  <li>Cleanup: {targetTypeInfo.cleanup}</li>
                )}
              </ul>
            </div>
          )}
        </div>

        {/* Scan Type Selection - Only show if detection failed or user wants to override */}
        {(showScanTypeSelection || (!scanTypeDetected && target.trim())) && (
          <div className="form-group" style={{ marginTop: '1.5rem' }}>
            <label>
              Scan Type {scanTypeDetected ? '(auto-detected, can override)' : '(required)'}
            </label>
            <div className="radio-group">
              {Object.entries(scanTypesConfig)
                .filter(([_, typeConfig]) => typeConfig.enabled)
                .map(([frontendValue, typeConfig]) => (
                  <label key={frontendValue} className="scan-form-label">
                    <input
                      type="radio"
                      value={frontendValue}
                      checked={scanType === frontendValue}
                      onChange={(e) => {
                        setScanType(e.target.value)
                        setScanTypeDetected(false)
                      }}
                    />
                    {typeConfig.label}
                  </label>
                ))}
            </div>
            {gitOnly && (
              <small className="form-help-text warning">
                ⚠️ Production Mode: Only Git repositories or Docker Hub container images are allowed
              </small>
            )}
          </div>
        )}

        {scanType === 'code' && isLocalPath && (
          <div className="form-group" style={{ marginTop: '1rem' }}>
            <label>
              <input
                type="checkbox"
                checked={ciMode}
                onChange={(e) => setCiMode(e.target.checked)}
              />
              CI Mode (scan only tracked files)
            </label>
            <small className="form-help-text info">
              Scans only files tracked by Git (ignores untracked files). Only available for local Git repositories.
            </small>
          </div>
        )}

        {isLocalPath && !localPathsAllowed && (
          <small className="form-help-text error">
            ❌ Local paths are not allowed in Production Mode. Please use a Git repository URL (GitHub/GitLab) or a container registry image.
          </small>
        )}
        {isLocalPathRestrictedByRole && (
          <small className="form-help-text error">
            ⚠️ Local path scanning requires admin privileges. Please log in as an administrator or use a Git repository URL / container image.
          </small>
        )}
        {isLocalContainerRestrictedByRole && (
          <small className="form-help-text error">
            ⚠️ Local container scanning (localhost, 127.0.0.1, local/…) requires admin privileges. Use a remote image (e.g. Docker Hub) or log in as administrator.
          </small>
        )}
        {isImageTarget && gitOnly && !isDockerHubImage(target) && (
          <small className="form-help-text error">
            ❌ Production Mode: Only Docker Hub images are allowed (docker.io/... or unqualified image names).
          </small>
        )}

        {isGitRepo && (
          <>
            <div className="form-group" style={{ marginTop: '0.75rem' }}>
              <label htmlFor="git-branch">
                Git Branch {availableBranches.length > 0 ? '(auto-detected)' : '(optional)'}
              </label>
              {loadingBranches ? (
                <div className="form-loading-text">
                  🔄 Loading branches...
                </div>
              ) : availableBranches.length > 0 ? (
                <select
                  id="git-branch"
                  value={gitBranch}
                  onChange={(e) => setGitBranch(e.target.value)}
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
                  />
                  {branchError && (
                    <small className="form-help-text warning">
                      ⚠️ {branchError}
                    </small>
                  )}
                </>
              )}
              <small className="form-help-text info">
                {availableBranches.length > 0 
                  ? 'Default branch is automatically selected. You can choose a different branch.'
                  : 'Leave empty for default branch (usually "main" or "master")'}
              </small>
            </div>
          </>
        )}
      </ScanStep>

      {/* Step 2: Scanner Selection */}
      {scanType && (
        <ScanStep
          id="step-2"
          title="Scanner Selection"
          trigger={targetTypeInfo ? targetTypeInfo.target_type : undefined}
          autoScroll={!!targetTypeInfo && target.trim().length > 0}
          expanded={true}
          completed={selectedScanners.length > 0}
          required={true}
        >
          <ScannerCardGrid
            scanners={scanners}
            selectedScanners={selectedScanners}
            onToggle={handleScannerToggle}
            onSelectAll={handleSelectAllScanners}
            onDeselectAll={handleDeselectAllScanners}
            loading={loadingScanners}
            error={scannerError}
          />
        </ScanStep>
      )}

      {/* Step 3: Advanced Options */}
      <ScanStep
        id="step-3"
        title="Advanced Options"
        trigger={undefined}
        autoScroll={false}
        expanded={false}
        completed={false}
        required={false}
      >
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
          <small className="form-help-text info">
            By default, no metadata is collected for privacy. Enable this to include project information in the scan report.
          </small>
        </div>
      )}
      {metadataCollection === 'always' && (
        <div className="glass form-info-box success">
          ℹ️ Metadata collection is always enabled in Production Mode for scan deduplication.
        </div>
        )}
      </ScanStep>

      {/* Error Display */}
      {error && (
        <div className="glass form-info-box error">
          {error}
        </div>
      )}

      {/* Fixed Action Bar */}
      <div className="glass action-bar">
        <span title={scanDisabledReason} className="scan-form-submit-wrapper">
          <button 
            type="submit" 
            className="primary scan-form-submit-button" 
            disabled={isScanDisabled}
          >
            {loading ? '🔄 Starting Scan...' : '🚀 Start Scan'}
          </button>
        </span>
      </div>
    </form>
  )
}
