import { useCallback, useEffect, useMemo, useState, type CSSProperties } from 'react'
import { useConfig } from '../hooks/useConfig'
import { useAuth } from '../hooks/useAuth'
import { useToast } from '../context/ToastContext'
import { resolveApiUrl } from '../utils/resolveApiUrl'

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
      env?: Record<string, string>
    } | null
  }
  last_updated?: {
    updated_at?: string | null
    age_seconds?: number | null
    age_human?: string | null
  } | null
}

function assetKey(scanner: string, assetId: string) {
  return `${scanner}:${assetId}`
}

/** FastAPI `detail` may be string, list of validation errors, or object. */
function formatApiDetail(body: unknown, fallback: string, status?: number): string {
  if (!body || typeof body !== 'object') {
    return status ? `${fallback} (HTTP ${status})` : fallback
  }
  const detail = (body as { detail?: unknown }).detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === 'string') return item
        if (item && typeof item === 'object' && 'msg' in item) {
          return String((item as { msg: unknown }).msg)
        }
        return JSON.stringify(item)
      })
      .filter(Boolean)
    if (parts.length) return parts.join('; ')
  }
  if (detail && typeof detail === 'object') {
    try {
      return JSON.stringify(detail)
    } catch {
      /* ignore */
    }
  }
  const message = (body as { message?: unknown }).message
  if (typeof message === 'string' && message.trim()) return message
  return status ? `${fallback} (HTTP ${status})` : fallback
}

const badgeBase: CSSProperties = {
  display: 'inline-block',
  fontSize: '0.7rem',
  fontWeight: 600,
  letterSpacing: '0.03em',
  textTransform: 'uppercase' as const,
  padding: '0.2rem 0.5rem',
  borderRadius: '999px',
  border: '1px solid rgba(255,255,255,0.2)',
}

export default function ScannerDataUpdate() {
  const toast = useToast()
  const { config } = useConfig()
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [status, setStatus] = useState<UpdateStatus>({
    status: 'idle',
    started_at: null,
    finished_at: null,
  })
  /** Optimistic lock so buttons gray out immediately (before Redis poll catches up). */
  const [localBusy, setLocalBusy] = useState(false)
  const [assets, setAssets] = useState<ScannerAssetItem[]>([])
  const shouldShowButton = isAdmin && !config?.features?.scanner_assets_auto_update_enabled

  const refreshAssets = useCallback(async () => {
    try {
      const response = await fetch(resolveApiUrl('/api/scanners/assets'))
      if (!response.ok) {
        console.error('[ScannerDataUpdate] Failed to fetch assets:', response.status)
        return
      }
      const data = await response.json()
      const assetItems = Array.isArray(data.assets) ? data.assets : []
      setAssets(assetItems)
    } catch (err) {
      console.error('[ScannerDataUpdate] Error fetching assets:', err)
    }
  }, [])

  useEffect(() => {
    if (!isAdmin) return
    void refreshAssets()
  }, [isAdmin, refreshAssets])

  useEffect(() => {
    if (!isAdmin) return
    let pollInterval: number | null = null

    const fetchStatus = async () => {
      try {
        const response = await fetch(resolveApiUrl('/api/scanners/assets/update/status'))
        if (!response.ok) {
          console.error('[ScannerDataUpdate] Failed to fetch status:', response.status)
          return
        }
        const data = await response.json()
        setStatus(data)
        if (data.status === 'running') {
          setLocalBusy(true)
        } else if (data.status === 'done' || data.status === 'error' || data.status === 'idle') {
          setLocalBusy(false)
          if (data.status === 'done' || data.status === 'error') {
            void refreshAssets()
          }
          if (data.status === 'error' && data.error_message) {
            // Surface worker/job failure (post-start) once status flips to error
            console.warn('[ScannerDataUpdate] Update job error:', data.error_message)
          }
        }
      } catch (err) {
        console.error('[ScannerDataUpdate] Error fetching status:', err)
      }
    }

    void fetchStatus()
    pollInterval = window.setInterval(() => {
      void fetchStatus()
    }, 1000)

    return () => {
      if (pollInterval) clearInterval(pollInterval)
    }
  }, [isAdmin, refreshAssets])

  const updatableAssets = useMemo(
    () => assets.filter(item => item.asset?.update?.enabled),
    [assets],
  )

  const busy = localBusy || status.status === 'running'

  const handleUpdateOne = async (scannerName: string, assetId: string) => {
    if (busy) return
    setLocalBusy(true)
    setStatus(prev => ({
      ...prev,
      status: 'running',
      started_at: new Date().toISOString(),
      finished_at: null,
      error_message: null,
    }))
    try {
      const response = await fetch(
        resolveApiUrl(`/api/scanners/${scannerName}/assets/${assetId}/update`),
        { method: 'POST' },
      )
      if (!response.ok) {
        const error = await response.json().catch(() => ({}))
        const detail = formatApiDetail(error, 'Unknown error', response.status)
        toast.error(`Failed to start update for ${scannerName}/${assetId}: ${detail}`)
        setLocalBusy(false)
        setStatus(prev => ({
          ...prev,
          status: 'error',
          finished_at: new Date().toISOString(),
          error_message: detail,
        }))
        return
      }
      const data = await response.json()
      setStatus(data)
      toast.success('Asset update started — buttons stay locked until it finishes')
    } catch (err) {
      console.error('[ScannerDataUpdate] Error starting update:', err)
      toast.error('Failed to start update. Check console for details.')
      setLocalBusy(false)
      setStatus(prev => ({
        ...prev,
        status: 'error',
        finished_at: new Date().toISOString(),
        error_message: 'Request failed',
      }))
    }
  }

  const handleUpdateAll = async () => {
    if (busy || updatableAssets.length === 0) return
    // Sequential: one global lock; backend rejects parallel updates with 409.
    setLocalBusy(true)
    setStatus(prev => ({
      ...prev,
      status: 'running',
      started_at: new Date().toISOString(),
      finished_at: null,
      error_message: null,
    }))
    toast.success(`Starting updates for ${updatableAssets.length} asset(s) one-by-one…`)

    let successCount = 0
    let failCount = 0
    for (const item of updatableAssets) {
      try {
        // Wait until previous job is no longer running
        for (let i = 0; i < 3600; i++) {
          const st = await fetch(resolveApiUrl('/api/scanners/assets/update/status'))
          if (st.ok) {
            const data = await st.json()
            setStatus(data)
            if (data.status !== 'running') break
          }
          await new Promise(r => setTimeout(r, 1000))
        }
        const response = await fetch(
          resolveApiUrl(`/api/scanners/${item.scanner}/assets/${item.asset.id}/update`),
          { method: 'POST' },
        )
        if (!response.ok) {
          const error = await response.json().catch(() => ({}))
          const detail = formatApiDetail(error, 'Unknown error', response.status)
          console.error(`[ScannerDataUpdate] Failed to update ${item.scanner}/${item.asset.id}:`, detail)
          toast.error(`${item.scanner}/${item.asset.id}: ${detail}`)
          failCount++
          continue
        }
        successCount++
        const data = await response.json()
        setStatus(data)
      } catch {
        failCount++
      }
    }

    // Wait for last job
    for (let i = 0; i < 3600; i++) {
      const st = await fetch(resolveApiUrl('/api/scanners/assets/update/status'))
      if (st.ok) {
        const data = await st.json()
        setStatus(data)
        if (data.status !== 'running') {
          setLocalBusy(false)
          break
        }
      }
      await new Promise(r => setTimeout(r, 1000))
    }

    if (failCount === 0) {
      toast.success(`Finished queueing ${successCount} asset update(s).`)
    } else {
      toast.error(`Started ${successCount}, ${failCount} failed. Check status panel.`)
    }
    void refreshAssets()
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
        return '🔄 Updating… (all buttons locked)'
      case 'done':
        return '✅ Last job completed'
      case 'error':
        return '❌ Last job failed'
      default:
        return '⏸️ Idle'
    }
  }

  if (!isAdmin) {
    return null
  }

  const typeBadge = (type: string) => {
    const t = (type || 'unknown').toLowerCase()
    const color =
      t === 'data' ? 'rgba(40, 167, 69, 0.25)' : t === 'config' ? 'rgba(0, 123, 255, 0.25)' : 'rgba(108, 117, 125, 0.35)'
    return (
      <span style={{ ...badgeBase, background: color }}>
        {t}
      </span>
    )
  }

  const btnPrimary: React.CSSProperties = {
    padding: '0.45rem 0.85rem',
    background: busy
      ? 'linear-gradient(135deg, #6c757d 0%, #495057 100%)'
      : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: busy ? 'not-allowed' : 'pointer',
    fontWeight: 600,
    fontSize: '0.85rem',
    opacity: busy ? 0.55 : 1,
  }

  const cardStyle: CSSProperties = {
    padding: '1rem',
    background: 'rgba(0, 0, 0, 0.22)',
    borderRadius: '8px',
    border: '1px solid rgba(255, 255, 255, 0.12)',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
    minHeight: '140px',
  }

  return (
    <div>
      <div style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h3 style={{ margin: 0, marginBottom: '0.5rem' }}>Scanner assets</h3>
          <p style={{ margin: 0, opacity: 0.8, fontSize: '0.9rem', maxWidth: '42rem' }}>
            Shared host caches (vuln DBs). Update once here — scans reuse the cache instead of downloading every time.
          </p>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
          {shouldShowButton && updatableAssets.length > 1 && (
            <button type="button" style={btnPrimary} disabled={busy} onClick={() => void handleUpdateAll()}>
              {busy ? 'Updating…' : `🔄 Update all (${updatableAssets.length})`}
            </button>
          )}
          {!shouldShowButton && (
            <span style={{ opacity: 0.75, fontSize: '0.9rem' }}>Auto-update enabled</span>
          )}
        </div>
      </div>

      <div
        style={{
          marginBottom: '1rem',
          padding: '0.85rem 1rem',
          background: 'rgba(0, 0, 0, 0.2)',
          borderRadius: '6px',
          border: '1px solid rgba(255, 255, 255, 0.1)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span style={{ color: getStatusColor(), fontWeight: 'bold' }}>{getStatusText()}</span>
          {status.started_at && (
            <span style={{ fontSize: '0.85rem', opacity: 0.7 }}>
              Started: {new Date(status.started_at).toLocaleString()}
            </span>
          )}
          {status.finished_at && (
            <span style={{ fontSize: '0.85rem', opacity: 0.7 }}>
              Finished: {new Date(status.finished_at).toLocaleString()}
            </span>
          )}
        </div>
        {status.error_message && (
          <div style={{ marginTop: '0.5rem', color: '#f8a0a0', fontSize: '0.9rem' }}>
            {status.error_message}
          </div>
        )}
      </div>

      {assets.length === 0 ? (
        <p style={{ opacity: 0.75 }}>No scanner assets registered. Refresh scanners from the container so manifests sync to the database.</p>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: '1rem',
          }}
        >
          {assets.map(item => {
            const key = assetKey(item.scanner, item.asset.id)
            const canUpdate = Boolean(item.asset.update?.enabled) && shouldShowButton
            const age = item.last_updated?.age_human
            return (
              <div key={key} style={cardStyle}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '1rem', lineHeight: 1.3 }}>{item.scanner}</div>
                    <div style={{ fontSize: '0.8rem', opacity: 0.75, marginTop: '0.15rem' }}>{item.asset.id}</div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.35rem' }}>
                    {typeBadge(item.asset.type)}
                    {item.asset.update?.enabled ? (
                      <span style={{ ...badgeBase, background: 'rgba(102, 126, 234, 0.35)' }}>updatable</span>
                    ) : (
                      <span style={{ ...badgeBase, background: 'rgba(108, 117, 125, 0.25)' }}>mount</span>
                    )}
                  </div>
                </div>
                {item.asset.description && (
                  <p style={{ margin: 0, fontSize: '0.82rem', opacity: 0.85, lineHeight: 1.4 }}>{item.asset.description}</p>
                )}
                <div style={{ fontSize: '0.72rem', opacity: 0.55, fontFamily: 'ui-monospace, monospace', wordBreak: 'break-all' }}>
                  {item.asset.mount.host_subpath}
                </div>
                <div style={{ marginTop: 'auto', paddingTop: '0.35rem', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                  {age ? (
                    <div style={{ fontSize: '0.8rem', opacity: 0.8 }}>Cache age: {age}</div>
                  ) : (
                    <div style={{ fontSize: '0.8rem', opacity: 0.55 }}>No cache timestamp</div>
                  )}
                </div>
                {canUpdate && (
                  <button
                    type="button"
                    style={{ ...btnPrimary, alignSelf: 'flex-start', marginTop: '0.25rem' }}
                    disabled={busy}
                    aria-disabled={busy}
                    title={busy ? 'An update is already running' : 'Refresh shared cache'}
                    onClick={() => void handleUpdateOne(item.scanner, item.asset.id)}
                  >
                    {busy ? 'Locked…' : '🔄 Update'}
                  </button>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
