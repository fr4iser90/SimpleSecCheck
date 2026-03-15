/**
 * Time formatting utilities for displaying durations and estimated times.
 */

/**
 * Format estimated time in seconds to a human-readable string.
 * 
 * @param seconds - Time in seconds (can be null/undefined)
 * @returns Formatted string like "~2m 30s" or "~45s"
 */
export function formatEstimatedTime(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || seconds <= 0) {
    return '-'
  }
  
  if (seconds < 60) {
    return `~${Math.round(seconds)}s`
  }
  
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = Math.round(seconds % 60)
  
  if (remainingSeconds === 0) {
    return `~${minutes}m`
  }
  
  return `~${minutes}m ${remainingSeconds}s`
}

/**
 * Format duration in seconds to a human-readable string.
 * 
 * @param seconds - Duration in seconds (can be null/undefined)
 * @returns Formatted string like "2m 30s" or "45s"
 */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || seconds <= 0) {
    return '-'
  }
  
  if (seconds < 60) {
    return `${Math.round(seconds)}s`
  }
  
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = Math.round(seconds % 60)
  
  if (remainingSeconds === 0) {
    return `${minutes}m`
  }
  
  return `${minutes}m ${remainingSeconds}s`
}

/**
 * Format duration to a more detailed string (hours, minutes, seconds).
 * 
 * @param seconds - Duration in seconds (can be null/undefined)
 * @returns Formatted string like "1h 23m 45s" or "23m 45s"
 */
export function formatDetailedDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || seconds <= 0) {
    return '-'
  }
  
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = Math.round(seconds % 60)
  
  const parts: string[] = []
  
  if (hours > 0) {
    parts.push(`${hours}h`)
  }
  
  if (minutes > 0 || hours > 0) {
    parts.push(`${minutes}m`)
  }
  
  if (secs > 0 || parts.length === 0) {
    parts.push(`${secs}s`)
  }
  
  return parts.join(' ')
}

/**
 * Calculate estimated wait time based on queue position and average scan duration.
 * 
 * @param position - Position in queue (1-based)
 * @param avgDurationSeconds - Average duration per scan in seconds
 * @returns Estimated wait time in seconds
 */
export function calculateEstimatedWaitTime(
  position: number | null | undefined,
  avgDurationSeconds: number | null | undefined
): number | null {
  if (!position || position <= 0) {
    return null
  }
  
  // Position 1 means currently running or next to run, so wait time is 0
  if (position === 1) {
    return 0
  }
  
  // Use provided average or default to 2 minutes (120 seconds)
  const avgDuration = avgDurationSeconds || 120
  
  // Estimate: (position - 1) * average duration
  // Position 2 means 1 scan ahead, position 3 means 2 scans ahead, etc.
  return (position - 1) * avgDuration
}
