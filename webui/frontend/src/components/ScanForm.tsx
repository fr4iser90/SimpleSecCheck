import { useState } from 'react'

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
}

export default function ScanForm({ onScanStart }: ScanFormProps) {
  const [scanType, setScanType] = useState<'code' | 'website' | 'network'>('code')
  const [target, setTarget] = useState('')
  const [ciMode, setCiMode] = useState(false)
  const [findingPolicy, setFindingPolicy] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      // Clean whitespace from target and finding policy
      const cleanTarget = target.trim()
      const cleanFindingPolicy = findingPolicy.trim() || null

      const response = await fetch('/api/scan/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          type: scanType,
          target: scanType === 'network' ? 'network' : cleanTarget,
          ci_mode: ciMode,
          finding_policy: cleanFindingPolicy,
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

      {scanType !== 'network' && (
        <div className="form-group">
          <label htmlFor="target">
            Target {scanType === 'code' ? '(Path)' : '(URL)'}
          </label>
          <input
            id="target"
            type="text"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            onBlur={(e) => setTarget(e.target.value.trim())} // Auto-trim on blur
            placeholder={scanType === 'code' ? '/path/to/project' : 'https://example.com'}
            required
          />
        </div>
      )}

      <div className="form-group">
        <label>
          <input
            type="checkbox"
            checked={ciMode}
            onChange={(e) => setCiMode(e.target.checked)}
          />
          CI Mode (scan only tracked files)
        </label>
      </div>

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
