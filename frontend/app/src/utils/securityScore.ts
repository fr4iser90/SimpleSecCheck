/** Match scanner/output/html_utils.py enterprise score bands. */

const SEVERITY_WEIGHTS = {
  CRITICAL: 10,
  HIGH: 6,
  MEDIUM: 3,
  LOW: 1,
  INFO: 0,
} as const

const PENALTY_CAP = 60
const SCORE_FLOOR = 10

const SCORE_LABELS: Array<{ min: number; label: string; color: string }> = [
  { min: 90, label: 'Excellent', color: 'var(--color-pass)' },
  { min: 75, label: 'Good', color: 'var(--color-pass)' },
  { min: 60, label: 'Moderate', color: 'var(--color-warning)' },
  { min: 40, label: 'Needs Attention', color: 'var(--color-high)' },
  { min: 0, label: 'Critical', color: 'var(--color-critical)' },
]

export interface VulnCounts {
  critical: number
  high: number
  medium: number
  low: number
  info: number
}

export function computeSecurityScore(counts: VulnCounts): {
  score: number
  label: string
  color: string
} {
  const penalty = Math.min(
    PENALTY_CAP,
    counts.critical * SEVERITY_WEIGHTS.CRITICAL
      + counts.high * SEVERITY_WEIGHTS.HIGH
      + counts.medium * SEVERITY_WEIGHTS.MEDIUM
      + counts.low * SEVERITY_WEIGHTS.LOW
      + counts.info * SEVERITY_WEIGHTS.INFO,
  )
  const score = Math.max(SCORE_FLOOR, Math.round(100 - penalty))
  const band = SCORE_LABELS.find((b) => score >= b.min) ?? SCORE_LABELS[SCORE_LABELS.length - 1]
  return { score, label: band.label, color: band.color }
}
