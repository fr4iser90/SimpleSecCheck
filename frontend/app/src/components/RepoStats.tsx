interface RepoStatsProps {
  total: number
  scanned: number
  needsAttention: number
  critical: number
}

export default function RepoStats({ total, scanned, needsAttention, critical }: RepoStatsProps) {
  return (
    <div style={{
      background: 'var(--glass-bg-main)',
      padding: '1rem 1.5rem',
      borderRadius: '8px',
      marginBottom: '1.5rem',
      border: '1px solid var(--glass-border-main)',
      display: 'flex',
      gap: '2rem',
      flexWrap: 'wrap',
      fontSize: '0.9rem'
    }}>
      <div>
        <strong>📦 Total Repos:</strong> {total}
      </div>
      <div>
        <strong>✅ Scanned:</strong> {scanned}
      </div>
      <div style={{ color: needsAttention > 0 ? 'var(--color-medium)' : 'inherit' }}>
        <strong>⚠️ Needs Attention:</strong> {needsAttention}
      </div>
      <div style={{ color: critical > 0 ? 'var(--color-critical)' : 'inherit' }}>
        <strong>🔴 Critical:</strong> {critical}
      </div>
    </div>
  )
}
