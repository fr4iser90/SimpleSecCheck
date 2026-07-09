import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
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
  const [queueData, setQueueData] = useState<QueueData | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchQueue = useCallback(async ({ silent }: { silent: boolean }) => {
    try {
      const response = await fetch(resolveApiUrl('/api/queue/?limit=100'))
      if (!response.ok) throw new Error('Failed to fetch queue')
      const data = await response.json()
      setQueueData(data)
      setError(null)
    } catch (err) {
      if (!silent) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      }
    }
  }, [])

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
            Anonymized view of scans waiting to run. To cancel your own scan, open{' '}
            <Link to="/my-scans">My Scans</Link> or the scan progress page.
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
                return (
                <article key={item.queue_id} className={`queue-card ${statusClass(item.status)}`}>
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
