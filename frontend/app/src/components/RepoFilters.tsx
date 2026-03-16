import { FilterType, SortType } from '../utils/repoUtils'

interface RepoFiltersProps {
  filter: FilterType
  sortBy: SortType
  searchQuery: string
  onFilterChange: (filter: FilterType) => void
  onSortChange: (sortBy: SortType) => void
  onSearchChange: (query: string) => void
  onDiscoverClick: () => void
  onAddClick: () => void
  onConfigureScannersClick: () => void
}

export default function RepoFilters({
  filter,
  sortBy,
  searchQuery,
  onFilterChange,
  onSortChange,
  onSearchChange,
  onDiscoverClick,
  onAddClick,
  onConfigureScannersClick
}: RepoFiltersProps) {
  return (
    <div style={{
      display: 'flex',
      gap: '1rem',
      marginBottom: '1.5rem',
      flexWrap: 'wrap',
      alignItems: 'center',
      justifyContent: 'space-between'
    }}>
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center', flex: 1 }}>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <label style={{ fontSize: '0.9rem' }}>Filter:</label>
          <select
            value={filter}
            onChange={(e) => onFilterChange(e.target.value as FilterType)}
            style={{ padding: '0.5rem', borderRadius: '6px', background: 'var(--glass-bg-dark)', border: '1px solid var(--glass-border-dark)', color: 'var(--text-dark)' }}
          >
            <option value="all">All</option>
            <option value="healthy">🟢 Healthy</option>
            <option value="needs_attention">🟡 Needs Attention</option>
            <option value="critical">🔴 Critical</option>
            <option value="not_scanned">⚪ Not Scanned</option>
          </select>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <label style={{ fontSize: '0.9rem' }}>Sort:</label>
          <select
            value={sortBy}
            onChange={(e) => onSortChange(e.target.value as SortType)}
            style={{ padding: '0.5rem', borderRadius: '6px', background: 'var(--glass-bg-dark)', border: '1px solid var(--glass-border-dark)', color: 'var(--text-dark)' }}
          >
            <option value="name">Name</option>
            <option value="score">Score</option>
            <option value="last_scan">Last Scan</option>
            <option value="vulnerabilities">Vulnerabilities</option>
          </select>
        </div>
        <div style={{ flex: 1, minWidth: '200px', maxWidth: '400px' }}>
          <input
            type="text"
            placeholder="🔍 Search repositories..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: 'var(--glass-bg-dark)', border: '1px solid var(--glass-border-dark)', color: 'var(--text-dark)' }}
          />
        </div>
      </div>
      <div style={{ display: 'flex', gap: '0.5rem', flexShrink: 0 }}>
        <button onClick={onDiscoverClick}>
          🔍 Discover
        </button>
        <button className="primary" onClick={onAddClick}>
          + Add Repo
        </button>
        <button 
          onClick={onConfigureScannersClick}
          style={{
            background: 'var(--glass-bg-dark)',
            border: '1px solid var(--glass-border-dark)',
            color: 'var(--text-primary)',
            padding: '0.5rem 1rem',
            borderRadius: '8px',
            cursor: 'pointer'
          }}
        >
          ⚙️ Configure Scanners
        </button>
      </div>
    </div>
  )
}
