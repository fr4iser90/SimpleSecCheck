import { useEffect, useMemo, useState } from 'react'
import { useConfig } from '../hooks/useConfig'
import { useAuth } from '../hooks/useAuth'

interface UpdateStatus {
  status: 'idle' | 'running' | 'done' | 'error'
  started_at: string | null
  finished_at: string | null
  error_message?: string | null
  exit_code?: number | null
}

interface ScannerAssetItem {
  scanner: string
  asset: {
    id: string
    type: string
    description?: string | null
    mount: {
      host_subpath: string
      container_path: string
    }
    update?: {
      enabled: boolean
      command: string[]
    } | null
  }
  last_updated?: {
    updated_at?: string | null
    age_seconds?: number | null
    age_human?: string | null
  } | null
}

export default function ScannerDataUpdate() {
  const { config } = useConfig()
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [status, setStatus] = useState<UpdateStatus>({
    status: 'idle',
    started_at: null,
    finished_at: null,
  })
  const [assets, setAssets] = useState<ScannerAssetItem[]>([])
  const [selectedAssetKey, setSelectedAssetKey] = useState<string>('')
  const [isUpdating, setIsUpdating] = useState(false)
  
  // Only admins may see and trigger scanner updates; show manual button when global auto-update is disabled
  const shouldShowButton = isAdmin && !config?.features?.scanner_assets_auto_update_enabled

  // Fetch assets list (admin only)
  useEffect(() => {
    if (!isAdmin) return
    const fetchAssets = async () => {
      try {
        const response = await fetch('/api/scanners/assets')
        if (!response.ok) {
          console.error('[ScannerDataUpdate] Failed to fetch assets:', response.status)
          return
        }
        const data = await response.json()
        const assetItems = Array.isArray(data.assets) ? data.assets : []
        setAssets(assetItems)
        if (!selectedAssetKey && assetItems.length > 0) {
          const first = assetItems.find((item: ScannerAssetItem) => item.asset?.update?.enabled)
          if (first) {
            setSelectedAssetKey(`${first.scanner}:${first.asset.id}`)
          }
        }
      } catch (err) {
        console.error('[ScannerDataUpdate] Error fetching assets:', err)
      }
    }

    fetchAssets()
  }, [isAdmin, selectedAssetKey])

  const selectedAsset = useMemo(() => {
    if (!selectedAssetKey) {
      return null
    }
    const [scanner, assetId] = selectedAssetKey.split(':')
    return assets.find(item => item.scanner === scanner && item.asset.id === assetId) || null
  }, [assets, selectedAssetKey])

  const selectedAssetAge = useMemo(() => {
    if (!selectedAsset?.last_updated) {
      return null
    }
    return {
      updatedAt: selectedAsset.last_updated.updated_at,
      ageHuman: selectedAsset.last_updated.age_human,
    }
  }, [selectedAsset])

  // Poll for status (admin only)
  useEffect(() => {
    if (!isAdmin) return
    let pollInterval: number | null = null

    const fetchStatus = async () => {
      try {
        const response = await fetch('/api/scanners/assets/update/status')
        if (!response.ok) {
          console.error('[ScannerDataUpdate] Failed to fetch status:', response.status)
          return
        }
        const data = await response.json()
        setStatus(data)
        setIsUpdating(data.status === 'running')
      } catch (err) {
        console.error('[ScannerDataUpdate] Error fetching status:', err)
      }
    }

    fetchStatus()
    pollInterval = window.setInterval(() => { fetchStatus() }, 500)

    return () => {
      if (pollInterval) clearInterval(pollInterval)
    }
  }, [isAdmin, isUpdating])

  const handleStartUpdate = async () => {
    if (!selectedAssetKey) {
      alert('Please select a scanner asset to update.')
      return
    }
    
    // Handle "All" option for batch updates
    if (selectedAssetKey === 'all') {
      const updatePromises = updatableAssets.map(async (item) => {
        try {
          const response = await fetch(`/api/scanners/${item.scanner}/assets/${item.asset.id}/update`, {
            method: 'POST',
          })
          if (!response.ok) {
            const error = await response.json()
            console.error(`Failed to update ${item.scanner}/${item.asset.id}: ${error.detail || 'Unknown error'}`)
            return { success: false, scanner: item.scanner, asset: item.asset.id, error: error.detail }
          }
          return { success: true, scanner: item.scanner, asset: item.asset.id }
        } catch (err) {
          console.error(`[ScannerDataUpdate] Error updating ${item.scanner}/${item.asset.id}:`, err)
          return { success: false, scanner: item.scanner, asset: item.asset.id, error: String(err) }
        }
      })
      
      setIsUpdating(true)
      const results = await Promise.all(updatePromises)
      const successCount = results.filter(r => r.success).length
      const failCount = results.filter(r => !r.success).length
      
      if (failCount === 0) {
        alert(`✅ All ${successCount} asset updates started successfully!`)
      } else {
        alert(`⚠️ Started ${successCount} updates, ${failCount} failed. Check console for details.`)
      }
      return
    }
    
    // Single asset update
    const [scannerName, assetId] = selectedAssetKey.split(':')
    try {
      const response = await fetch(`/api/scanners/${scannerName}/assets/${assetId}/update`, {
        method: 'POST',
      })
      if (!response.ok) {
        const error = await response.json()
        alert(`Failed to start update: ${error.detail || 'Unknown error'}`)
        return
      }
      const data = await response.json()
      setStatus(data)
      setIsUpdating(true)
    } catch (err) {
      console.error('[ScannerDataUpdate] Error starting update:', err)
      alert('Failed to start update. Check console for details.')
    }
  }

  const handleStopUpdate = async () => {
    setIsUpdating(false)
  }

  const getStatusColor = () => {
    switch (status.status) {
      case 'running':
        return '#007bff'
      case 'done':
        return '#28a745'
      case 'error':
        return '#dc3545'
      default:
        return '#6c757d'
    }
  }

  const getStatusText = () => {
    switch (status.status) {
      case 'running':
        return '🔄 Updating...'
      case 'done':
        return '✅ Update completed'
      case 'error':
        return '❌ Update failed'
      default:
        return '⏸️ Idle'
    }
  }

  // Only admins see this card; guests and users see nothing
  if (!isAdmin) {
    return null
  }

  const updatableAssets = assets.filter(item => item.asset?.update?.enabled)

  return (
    <div>
      <div style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h3 style={{ margin: 0, marginBottom: '0.5rem' }}>Scanner Asset Updates</h3>
          <p style={{ margin: 0, opacity: 0.8, fontSize: '0.9rem' }}>
            Update scanner data assets (e.g. vulnerability databases) from their manifests.
          </p>
        </div>
        {shouldShowButton && (
          <div>
            {status.status === 'idle' && (
              <button
                onClick={handleStartUpdate}
                style={{
                  padding: '0.75rem 1.5rem',
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: 'bold',
                  fontSize: '1rem',
                }}
              >
                🔄 Update Asset
              </button>
            )}
            {status.status === 'running' && (
              <button
                onClick={handleStopUpdate}
                style={{
                  padding: '0.75rem 1.5rem',
                  background: '#dc3545',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: 'bold',
                  fontSize: '1rem',
                }}
              >
                ⏹️ Stop Update
              </button>
            )}
            {(status.status === 'done' || status.status === 'error') && (
              <button
                onClick={handleStartUpdate}
                style={{
                  padding: '0.75rem 1.5rem',
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: 'bold',
                  fontSize: '1rem',
                }}
              >
                🔄 Update Again
              </button>
            )}
          </div>
        )}
        {!shouldShowButton && (
          <div style={{ opacity: 0.7, fontSize: '0.9rem' }}>
            Auto-update enabled
          </div>
        )}
      </div>

      <div style={{ marginBottom: '1rem', padding: '1rem', background: 'rgba(0, 0, 0, 0.2)', borderRadius: '4px', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
        <div style={{ marginBottom: '0.75rem' }}>
          <label style={{ display: 'block', fontSize: '0.85rem', opacity: 0.8, marginBottom: '0.25rem' }}>
            Select Asset
          </label>
          <select
            value={selectedAssetKey}
            onChange={(event) => setSelectedAssetKey(event.target.value)}
            style={{
              width: '100%',
              padding: '0.5rem 0.75rem',
              borderRadius: '4px',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              background: 'rgba(0, 0, 0, 0.4)',
              color: 'var(--text-main, #f8f9fa)',
            }}
          >
            <option value="" disabled>
              {updatableAssets.length === 0 ? 'No updatable assets available' : 'Choose an asset'}
            </option>
            {updatableAssets.length > 1 && (
              <option value="all">
                🔄 All Assets ({updatableAssets.length} assets)
              </option>
            )}
            {updatableAssets.map(item => (
              <option key={`${item.scanner}:${item.asset.id}`} value={`${item.scanner}:${item.asset.id}`}>
                {item.scanner.toUpperCase()} · {item.asset.id}
              </option>
            ))}
          </select>
          {selectedAsset && (
            <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', opacity: 0.8 }}>
              {selectedAsset.asset.description || 'No description provided.'}
            </div>
          )}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <span style={{ color: getStatusColor(), fontWeight: 'bold' }}>{getStatusText()}</span>
            {status.started_at && (
              <span style={{ fontSize: '0.9rem', opacity: 0.7, color: 'var(--text-main, #f8f9fa)' }}>
                Started: {new Date(status.started_at).toLocaleString()}
              </span>
            )}
            {status.finished_at && (
              <span style={{ fontSize: '0.9rem', opacity: 0.7, color: 'var(--text-main, #f8f9fa)' }}>
                Finished: {new Date(status.finished_at).toLocaleString()}
              </span>
            )}
          </div>
          {selectedAssetAge?.ageHuman && (
            <div style={{ fontSize: '0.85rem', opacity: 0.8 }}>
              Last updated: {selectedAssetAge.ageHuman}
              {selectedAssetAge.updatedAt && (
                <span style={{ marginLeft: '0.5rem', opacity: 0.7 }}>
                  ({new Date(selectedAssetAge.updatedAt).toLocaleString()})
                </span>
              )}
            </div>
          )}
          {!selectedAssetAge && selectedAsset && (
            <div style={{ fontSize: '0.85rem', opacity: 0.7 }}>
              No local cache data found yet.
            </div>
          )}

          {/* Database age information */}
          {status.error_message && (
            <div style={{ marginTop: '0.5rem', color: '#dc3545' }}>
              Error: {status.error_message}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
