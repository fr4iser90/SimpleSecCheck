import AppIcon from './AppIcon'

function formatLastUpdated(date: Date | null): string {
  if (!date) return 'Not updated yet'
  return date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

interface RefreshToolbarProps {
  autoRefresh: boolean
  onAutoRefreshChange: (enabled: boolean) => void
  onRefresh: () => void
  isRefreshing?: boolean
  lastUpdated?: Date | null
  intervalMs?: number
  compact?: boolean
}

export default function RefreshToolbar({
  autoRefresh,
  onAutoRefreshChange,
  onRefresh,
  isRefreshing = false,
  lastUpdated = null,
  intervalMs = 5000,
  compact = false,
}: RefreshToolbarProps) {
  const intervalLabel = intervalMs >= 1000 ? `${Math.round(intervalMs / 1000)}s` : `${intervalMs}ms`

  return (
    <div className={`refresh-toolbar${compact ? ' refresh-toolbar--compact' : ''}`}>
      {autoRefresh && (
        <span className="refresh-toolbar__live" title={`Auto-refresh every ${intervalLabel}`}>
          <span className="refresh-toolbar__live-dot" aria-hidden />
          Live
        </span>
      )}
      <label className="refresh-toolbar__toggle">
        <input
          type="checkbox"
          checked={autoRefresh}
          onChange={(e) => onAutoRefreshChange(e.target.checked)}
        />
        <span>Auto ({intervalLabel})</span>
      </label>
      <button
        type="button"
        className="btn-secondary refresh-toolbar__btn"
        onClick={onRefresh}
        disabled={isRefreshing}
        aria-label="Refresh now"
        title="Refresh now"
      >
        <AppIcon name="refresh" size={15} className={isRefreshing ? 'refresh-toolbar__icon--spin' : undefined} />
        <span>{isRefreshing ? 'Updating…' : 'Refresh'}</span>
      </button>
      {!compact && (
        <span className="refresh-toolbar__updated" title={lastUpdated?.toISOString()}>
          Updated {formatLastUpdated(lastUpdated)}
        </span>
      )}
    </div>
  )
}
