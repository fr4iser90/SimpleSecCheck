import type { AutoScanConfig, ScanTargetItem } from '../hooks/useTargets'

export type AddTargetPayload = {
  type: string
  source: string
  display_name?: string
  config: Record<string, unknown>
  auto_scan: AutoScanConfig
  initial_scan_paused?: boolean
}

export function normalizeTargetSource(s: string): string {
  return s
    .trim()
    .replace(/\.git$/i, '')
    .replace(/\/+$/, '')
    .toLowerCase()
}

export function findDuplicateTarget(
  list: ScanTargetItem[],
  payload: Pick<AddTargetPayload, 'type' | 'source'>
): ScanTargetItem | undefined {
  const n = normalizeTargetSource(payload.source)
  return list.find(
    (t) => t.type === payload.type && normalizeTargetSource(t.source) === n
  )
}

export class DuplicateTargetError extends Error {
  override name = 'DuplicateTargetError'

  constructor(
    message: string,
    public payload: AddTargetPayload,
    public existing: ScanTargetItem | null
  ) {
    super(message)
  }
}
