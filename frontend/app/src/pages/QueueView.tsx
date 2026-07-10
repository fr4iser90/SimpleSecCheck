import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import PageHeader from '../components/PageHeader'
import RefreshToolbar from '../components/RefreshToolbar'
import { useConfig } from '../hooks/useConfig'
import { useSseRefresh } from '../hooks/useSseRefresh'
import { formatQueuePosition } from '../utils/timeUtils'
import { resolveApiUrl } from '../utils/resolveApiUrl'

interface QueueItem {
  queue_id: string
  repository_name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  position?: number
  created_at: string
  branch?: string
  scanners?: string[]
}

interface QueueData {
  items: QueueItem[]
  queue_length: number
  max_queue_length: number
}

interface MyScanRef {
  queue_id: string
  scan_id?: string
  status: QueueItem['status']
  started_at?: string
}

function statusClass(status: string): string {
  switch (status) {
    case 'pending':
      return 'queue-card--pending'
    case 'running':
      return 'queue-card--running'
    case 'completed':
      return 'queue-card--completed'
    case 'failed':
      return 'queue-card--failed'
    default:
      return ''
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case 'pending':
      return 'Pending'
    case 'running':
      return 'Running'
    case 'completed':
      return 'Completed'
    case 'failed':
      return 'Failed'
    default:
      return status
  }
}

export default function QueueView() {
  useConfig()
  const navigate = useNavigate()
  const [queueData, setQueueData] = useState<QueueData | null>(null)
  const [myScans, setMyScans] = useState<MyScanRef[]>([])
  const [error, setError] = useState<string | null>(null)

  const fetchQueue = useCallback(async ({ silent }: { silent: boolean }) => {
    try {
      const [queueRes, myScansRes] = await Promise.all([
        fetch(resolveApiUrl('/api/queue/?limit=100')),
        fetch(resolveApiUrl('/api/queue/my-scans')),
      ])
      if (!queueRes.ok) throw new Error('Failed to fetch queue')
      const data = await queueRes.json()
      setQueueData(data)
      if (myScansRes.ok) {
        const mine = await myScansRes.json()
        setMyScans(Array.isArray(mine.scans) ? mine.scans : [])
      }
      setError(null)
    } catch (err) {
      if (!silent) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      }
    }
  }, [])

  const myScanByQueueId = useMemo(() => {
    const map = new Map<string, MyScanRef>()
    for (const scan of myScans) {
      map.set(scan.queue_id, scan)
      if (scan.scan_id) map.set(scan.scan_id, scan)
    }
    return map
  }, [myScans])

  const openMyScan = useCallback(
    (item: QueueItem) => {
      const mine = myScanByQueueId.get(item.queue_id)
      const scanId = mine?.scan_id || item.queue_id
      navigate(`/scan?scan_id=${encodeURIComponent(scanId)}`, {
        state: {
          status: item.status,
          scan_id: scanId,
          results_dir: item.status === 'completed' ? scanId : null,
          started_at: mine?.started_at || null,
        },
      })
    },
    [myScanByQueueId, navigate],
  )

  const [autoRefresh] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [initialLoad, setInitialLoad] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const refresh = useCallback(async (silent = false) => {
    if (!silent) setIsRefreshing(true)
    try {
      await fetchQueue({ silent })
      setLastUpdated(new Date())
    } finally {
      setIsRefreshing(false)
      setInitialLoad(false)
    }
  }, [fetchQueue])

  useSseRefresh(['queue_update', 'scan_update'], () => {
    void refresh(true)
  })

  useEffect(() => {
    void refresh(false)
  }, [refresh])

  return (
    <div className="container">
      <PageHeader
        title="Queue"
        subtitle={
          <>
            Anonymized view of scans waiting to run. Click your own scan to open progress, or use{' '}
            <Link to="/my-scans">My Scans</Link> to cancel.
          </>
        }
      >
        <RefreshToolbar
          autoRefresh={autoRefresh}
          onAutoRefreshChange={() => {}}
          onRefresh={() => void refresh(false)}
          isRefreshing={isRefreshing}
          lastUpdated={lastUpdated}
        />
      </PageHeader>

      {queueData && (
        <div className="queue-metrics">
          <span>
            <strong>{queueData.queue_length}</strong> / {queueData.max_queue_length} in queue
          </span>
          <span>
            <strong>{queueData.items.filter((item) => item.status === 'pending').length}</strong> pending
          </span>
          <span>
            <strong>{queueData.items.filter((item) => item.status === 'running').length}</strong> running
          </span>
          <span>
            <strong>{queueData.items.filter((item) => item.status === 'completed').length}</strong> completed
          </span>
        </div>
      )}

      {error && <div className="error-message" role="alert">{error}</div>}

      <div className="panel">
        <div className="panel__body">
          {initialLoad && !queueData ? (
            <div className="loading">Loading queue…</div>
          ) : queueData && queueData.queue_length === 0 && queueData.items.length === 0 ? (
            <p style={{ textAlign: 'center', color: 'var(--ds-text-secondary)', margin: 0 }}>Queue is empty</p>
          ) : queueData && queueData.items.length > 0 ? (
            <div className="queue-grid">
              {queueData.items.map((item) => {
                const positionLabel = formatQueuePosition(item.position, item.status)
                const isMine = myScanByQueueId.has(item.queue_id)
                const cardClass = `queue-card ${statusClass(item.status)}${isMine ? ' queue-card--mine' : ''}`

                if (isMine) {
                  return (
                    <button
                      key={item.queue_id}
                      type="button"
                      className={cardClass}
                      onClick={() => openMyScan(item)}
                      title="Open scan progress"
                    >
                      <div className="queue-card__header">
                        <div>
                          {positionLabel !== '—' && (
                            <div className="queue-card__position">{positionLabel}</div>
                          )}
                          <div className="queue-card__meta">{new Date(item.created_at).toLocaleString()}</div>
                        </div>
                        <span className={`status-pill status-pill--${item.status === 'running' ? 'active' : item.status === 'pending' ? 'pending' : 'inactive'}`}>
                          {statusLabel(item.status)}
                        </span>
                      </div>

                      <div className="queue-card__section">
                        <div className="queue-card__label">Repository</div>
                        <div className="queue-card__value queue-card__value--mono">{item.repository_name}</div>
                      </div>

                      {item.branch && (
                        <div className="queue-card__section">
                          <div className="queue-card__label">Branch</div>
                          <div className="queue-card__value">{item.branch}</div>
                        </div>
                      )}

                      {item.scanners && item.scanners.length > 0 && (
                        <div className="queue-card__section">
                          <div className="queue-card__label">Scanners ({item.scanners.length})</div>
                          <div className="queue-card__chips">
                            {item.scanners.map((scanner) => (
                              <span key={scanner} className="ui-chip ui-chip--accent">
                                {scanner}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="queue-card__action-hint">Your scan — open progress</div>
                    </button>
                  )
                }

                return (
                  <article key={item.queue_id} className={cardClass}>
                    <div className="queue-card__header">
                      <div>
                        {positionLabel !== '—' && (
                          <div className="queue-card__position">{positionLabel}</div>
                        )}
                        <div className="queue-card__meta">{new Date(item.created_at).toLocaleString()}</div>
                      </div>
                      <span className={`status-pill status-pill--${item.status === 'running' ? 'active' : item.status === 'pending' ? 'pending' : 'inactive'}`}>
                        {statusLabel(item.status)}
                      </span>
                    </div>

                    <div className="queue-card__section">
                      <div className="queue-card__label">Repository</div>
                      <div className="queue-card__value queue-card__value--mono">{item.repository_name}</div>
                    </div>

                    {item.branch && (
                      <div className="queue-card__section">
                        <div className="queue-card__label">Branch</div>
                        <div className="queue-card__value">{item.branch}</div>
                      </div>
                    )}

                    {item.scanners && item.scanners.length > 0 && (
                      <div className="queue-card__section">
                        <div className="queue-card__label">Scanners ({item.scanners.length})</div>
                        <div className="queue-card__chips">
                          {item.scanners.map((scanner) => (
                            <span key={scanner} className="ui-chip ui-chip--accent">
                              {scanner}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </article>
                )
              })}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
