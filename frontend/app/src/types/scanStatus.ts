/**
 * Scan lifecycle status — same strings as backend ScanStatus (+ idle).
 * @see backend/domain/entities/scan.py ScanStatus
 */
export type ScanRunStatus =
  | 'idle'
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'interrupted'

export interface ScanStatusState {
  status: ScanRunStatus
  scan_id: string | null
  results_dir: string | null
  started_at: string | null
  error_code?: number | null
  error_message?: string | null
}
