import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import ReportViewer from '../components/ReportViewer'
import StepsSidebar from '../components/StepsSidebar'
import AIPromptModal from '../components/AIPromptModal'
import { SubstepSlot } from '../components/SubstepSlot'
import { useWebSocket } from '../services/websocketService'
import { formatDuration, parseStepInstantMs } from '../utils/timeUtils'
import type { ScanRunStatus, ScanStatusState } from '../types/scanStatus'

type ScanStatusData = ScanStatusState

interface QueueStatus {
  queue_id: string
  repository_name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  position?: number
  created_at: string
  scan_id?: string
  /** Estimated duration of this scan (from its tools), in seconds */
  estimated_time_seconds?: number | null
  /** Estimated wait until this scan starts (sum of tool-based durations of scans before this one), in seconds */
  estimated_wait_seconds?: number | null
}

interface SubStep {
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  message?: string
  started_at?: string | null
  completed_at?: string | null
  type?: 'phase' | 'action' | 'output'  // Substep type for visual distinction
}

interface Step {
  number: number
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  message?: string
  substeps?: SubStep[]
  /** Step start (ISO); used for live elapsed while running */
  started_at?: string | null
  /** Elapsed time in seconds (final when completed; while running prefer started_at + tick) */
  duration_seconds?: number | null
  /** Max duration in seconds from manifest (timeout) */
  timeout_seconds?: number | null
}

interface WebSocketMessage {
  type: string
  steps?: Step[]
  progress_percentage?: number
  total_steps?: number
  scan_id?: string
  timestamp?: number
}

export default function ScanView() {
  const navigate = useNavigate()
  const location = useLocation()
  
  // Get initial status from navigation state (passed from ScanForm)
  const [status, setStatus] = useState<ScanStatusData>(
    location.state || {
      status: 'idle',
      scan_id: null,
      results_dir: null,
      started_at: null,
    }
  )

  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null)
  const [steps, setSteps] = useState<Step[]>([])
  const [progress, setProgress] = useState<number>(0)
  const [isStepsSidebarOpen, setIsStepsSidebarOpen] = useState(false)
  const [isLogsSidebarOpen, setIsLogsSidebarOpen] = useState(false)
  const [isAIPromptModalOpen, setIsAIPromptModalOpen] = useState(false)
  /** Step numbers with expanded substep list */
  const [expandedStepNumbers, setExpandedStepNumbers] = useState<Set<number>>(new Set())
  const [cancelLoading, setCancelLoading] = useState(false)
  const [cancelError, setCancelError] = useState<string | null>(null)
  /** Re-render every second while scan runs so step/substep durations tick */
  const [, setLiveTick] = useState(0)

  // Check if scan_id is a queue_id (UUID format)
  const isQueueId = (id: string | null): boolean => {
    if (!id) return false
    // UUID format: 8-4-4-4-12 hex characters
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
    return uuidRegex.test(id)
  }

  // Poll queue status if scan_id is a queue_id (ALWAYS poll, not just when pending/idle!)
  useEffect(() => {
    if (status.scan_id && isQueueId(status.scan_id) && (status.status === 'pending' || status.status === 'idle' || status.status === 'running')) {
      const fetchQueueStatus = async () => {
        try {
          const { apiFetch } = await import('../utils/apiClient')
          const response = await apiFetch(`/api/queue/${status.scan_id}/status`)
          if (response.ok) {
            const data = await response.json()
            setQueueStatus(data)
            
            if (data.status === 'running') {
              setStatus((prev) => ({ ...prev, status: 'running' as ScanRunStatus }))
            } else if (data.status === 'completed' && data.scan_id) {
              setStatus((prev) => ({
                ...prev,
                status: 'completed',
                scan_id: data.scan_id,
                results_dir:
                  data.results_dir ||
                  data.scan_id ||
                  prev.results_dir ||
                  prev.scan_id,
              }))
            } else if (data.status === 'completed') {
              setStatus((prev) => ({ ...prev, status: 'completed' }))
            } else if (data.status === 'failed') {
              setStatus((prev) => ({ ...prev, status: 'failed' }))
            } else if (data.status === 'pending') {
              setStatus((prev) => ({ ...prev, status: 'pending' }))
            }
          }
        } catch (error) {
          console.error('Failed to fetch queue status:', error)
        }
      }

      fetchQueueStatus()
      const interval = setInterval(fetchQueueStatus, 6000) // Poll every 6 seconds
      return () => clearInterval(interval)
    }
  }, [status.scan_id, status.status])

  // Poll scan status if running (non-queue scan or after queue scan started)
  useEffect(() => {
    if (status.status === 'running' && status.scan_id && !isQueueId(status.scan_id)) {
      const sid = status.scan_id
      let intervalId: ReturnType<typeof setInterval> | null = null
      const poll = async () => {
        try {
          const { apiFetch } = await import('../utils/apiClient')
          const response = await apiFetch(
            `/api/v1/scans/${encodeURIComponent(sid)}/status`
          )
          if (response.ok) {
            const data = await response.json()
            const st = data.status as ScanRunStatus
            setStatus((prev) => ({
              ...prev,
              scan_id: data.scan_id ?? prev.scan_id,
              status: st,
              started_at: data.started_at ?? prev.started_at,
              results_dir:
                st === 'completed'
                  ? prev.results_dir || data.scan_id || prev.scan_id
                  : prev.results_dir,
            }))
            if (
              ['completed', 'failed', 'cancelled', 'interrupted'].includes(
                data.status
              ) &&
              intervalId != null
            ) {
              clearInterval(intervalId)
              intervalId = null
            }
          }
        } catch (error) {
          console.error('Failed to fetch scan status:', error)
        }
      }
      void poll()
      intervalId = setInterval(poll, 2000)
      return () => {
        if (intervalId != null) clearInterval(intervalId)
      }
    }
  }, [status.status, status.scan_id])

  useEffect(() => {
    if (status.status !== 'running') return
    const id = window.setInterval(() => setLiveTick((n) => n + 1), 1000)
    return () => window.clearInterval(id)
  }, [status.status])

  // WebSocket: Real-time scan updates using new service
  const { service } = useWebSocket(
    status.status === 'running' && status.scan_id ? status.scan_id : null
  )

  // Load steps from REST API when scan_id is available (initial load)
  useEffect(() => {
    if (!status.scan_id) return

    const fetchSteps = async () => {
      try {
        const { apiFetch } = await import('../utils/apiClient')
        const response = await apiFetch(`/api/v1/scans/${status.scan_id}/steps`)
        if (response.ok) {
          const data = await response.json()
          if (data.steps && data.steps.length > 0) {
            const convertedSteps: Step[] = data.steps.map((step: any) => ({
              number: step.number || 0,
              name: step.name || 'Unknown',
              status: (step.status || 'pending') as 'pending' | 'running' | 'completed' | 'failed',
              message: step.message || '',
              substeps: step.substeps ? step.substeps.map((substep: any) => ({
                name: substep.name || '',
                status: (substep.status || 'pending') as 'pending' | 'running' | 'completed' | 'failed',
                message: substep.message || '',
                started_at: substep.started_at || null,
                completed_at: substep.completed_at || null,
              })) : [],
              started_at: step.started_at ?? null,
              duration_seconds: step.duration_seconds ?? null,
              timeout_seconds: step.timeout_seconds ?? null,
            }))
            setSteps(convertedSteps)
            if (data.progress_percentage !== undefined) {
              setProgress(data.progress_percentage)
            }
          }
        }
      } catch (error) {
        console.error('Failed to fetch steps:', error)
      }
    }

    fetchSteps()
  }, [status.scan_id])

  // Handle WebSocket messages to update steps and progress (real-time updates)
  useEffect(() => {
    if (!service) return

    const handleMessage = (data: WebSocketMessage) => {
      if (data.type === 'step_update' && data.steps) {
        setSteps(data.steps)
        if (data.progress_percentage !== undefined) {
          setProgress(data.progress_percentage)
        }
      } else if (data.type === 'initial_steps' && data.steps) {
        setSteps(data.steps)
        if (data.progress_percentage !== undefined) {
          setProgress(data.progress_percentage)
        }
      }
    }

    // Set up message handler
    service.onMessage(handleMessage)

    return () => {
      // Clean up message handler
      if (service) {
        service.onMessage(() => {}) // Clear handler
      }
    }
  }, [service])

  // Listen for messages from iframe (HTML Report)
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin && !event.origin.includes('localhost:8080')) {
        return
      }
      
      if (event.data && event.data.type === 'OPEN_AI_PROMPT_MODAL') {
        setIsAIPromptModalOpen(true)
      }
    }

    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [])

  // Progress is now calculated in backend and sent via WebSocket

  const toggleStepExpand = (stepNumber: number) => {
    setExpandedStepNumbers((prev) => {
      const next = new Set(prev)
      if (next.has(stepNumber)) next.delete(stepNumber)
      else next.add(stepNumber)
      return next
    })
  }

  const formatSubstepDuration = (s: SubStep): string => {
    if (s.completed_at && s.started_at) {
      const a = parseStepInstantMs(s.started_at)
      const b = parseStepInstantMs(s.completed_at)
      if (!Number.isNaN(a) && !Number.isNaN(b) && b >= a) return `${Math.round((b - a) / 1000)}s`
    }
    if (s.status === 'running' && s.started_at) {
      const a = parseStepInstantMs(s.started_at)
      if (!Number.isNaN(a)) return `${Math.max(0, Math.round((Date.now() - a) / 1000))}s`
    }
    return ''
  }

  const getStepElapsedSeconds = (step: Step): number | null => {
    if (step.status === 'running' && step.started_at) {
      const t = parseStepInstantMs(step.started_at)
      if (!Number.isNaN(t)) return Math.max(0, Math.floor((Date.now() - t) / 1000))
    }
    if (step.duration_seconds != null) return step.duration_seconds
    return null
  }

  const handleCancelScan = useCallback(async () => {
    const id = status.scan_id
    if (!id || cancelLoading) return
    if (!window.confirm('Cancel this scan? It will be removed from the queue or stopped if already running.')) return
    setCancelError(null)
    setCancelLoading(true)
    try {
      const { apiFetch } = await import('../utils/apiClient')
      const res = await apiFetch(`/api/v1/scans/${id}/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scan_id: id, force: false }),
      })
      if (!res.ok) {
        let msg = `Request failed (${res.status})`
        try {
          const j = await res.json()
          const d = j.detail
          msg = typeof d === 'string' ? d : Array.isArray(d) ? String(d[0]?.msg ?? msg) : msg
        } catch {
          /* ignore */
        }
        throw new Error(msg)
      }
      navigate('/my-scans', { replace: true, state: { flash: 'Scan cancelled.' } })
    } catch (e) {
      setCancelError(e instanceof Error ? e.message : 'Cancel failed')
    } finally {
      setCancelLoading(false)
    }
  }, [status.scan_id, cancelLoading, navigate])

  const cancelButtonStyle = {
    marginTop: '1.25rem',
    padding: '0.6rem 1.25rem',
    background: 'transparent',
    color: 'var(--text-muted, #adb5bd)',
    border: '1px solid rgba(220, 53, 69, 0.5)',
    borderRadius: '8px',
    cursor: cancelLoading ? 'wait' : 'pointer',
    fontSize: '0.9rem',
    opacity: cancelLoading ? 0.7 : 1,
  }

  // Show queue waiting state (Backend queue status: 'pending')
  if (status.status === 'pending') {
    const estimatedWaitSeconds = queueStatus?.estimated_wait_seconds ?? null
    const formatWait = (sec: number): string => {
      if (sec < 60) return `${sec}s`
      const m = Math.floor(sec / 60)
      const s = Math.round(sec % 60)
      return s ? `${m}m ${s}s` : `${m}m`
    }

    return (
      <div style={{ 
        flex: 1,
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '2rem',
        padding: '2rem',
      }}>
        <div style={{ textAlign: 'center', maxWidth: '600px' }}>
          <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>⏳</div>
          <h2>Waiting in Queue</h2>
          <p style={{ opacity: 0.7, marginTop: '0.5rem', fontSize: '1.1rem' }}>
            Your scan is queued and will start automatically
          </p>
          
          {queueStatus ? (
            <>
              <div style={{
                marginTop: '2rem',
                padding: '1.5rem',
                background: 'var(--glass-bg-main)',
                border: '1px solid var(--glass-border-main)',
                borderRadius: '12px',
                width: '100%',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                  <span style={{ opacity: 0.8 }}>Position in Queue:</span>
                  <strong style={{ fontSize: '1.5rem' }}>#{queueStatus.position || '?'}</strong>
                </div>
                {estimatedWaitSeconds != null && estimatedWaitSeconds > 0 && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                    <span style={{ opacity: 0.8 }}>Estimated Wait:</span>
                    <strong>{formatWait(estimatedWaitSeconds)}</strong>
                  </div>
                )}
                {estimatedWaitSeconds === 0 && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                    <span style={{ opacity: 0.8 }}>Estimated Wait:</span>
                    <strong>Next in line</strong>
                  </div>
                )}
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ opacity: '0.8' }}>Repository:</span>
                  <strong>{queueStatus.repository_name}</strong>
                </div>
              </div>
            </>
          ) : (
            <div style={{
              marginTop: '2rem',
              padding: '1.5rem',
              background: 'var(--glass-bg-main)',
              border: '1px solid var(--glass-border-main)',
              borderRadius: '12px',
              width: '100%',
            }}>
              <div style={{ opacity: 0.7 }}>Loading queue information...</div>
            </div>
          )}

          <div style={{
            marginTop: '2rem',
            width: '100%',
            maxWidth: '600px',
            background: 'var(--glass-bg-main)',
            border: '1px solid var(--glass-border-main)',
            borderRadius: '8px',
            padding: '1rem',
          }}>
            <div style={{ marginBottom: '0.5rem', fontSize: '0.9rem', opacity: 0.8 }}>
              Waiting for your turn...
            </div>
            <div style={{
              width: '100%',
              height: '8px',
              background: 'var(--surface-muted)',
              borderRadius: '4px',
              overflow: 'hidden',
            }}>
              <div style={{
                width: '100%',
                height: '100%',
                background: 'linear-gradient(90deg, #007bff, #0056b3)',
                animation: 'pulse 2s ease-in-out infinite',
              }} />
            </div>
          </div>

          {status.scan_id && (
            <div style={{ textAlign: 'center', marginTop: '1.5rem' }}>
              <button type="button" onClick={handleCancelScan} disabled={cancelLoading} style={cancelButtonStyle}>
                {cancelLoading ? 'Cancelling…' : 'Cancel scan (leave queue)'}
              </button>
              {cancelError && (
                <div style={{ marginTop: '0.75rem', color: '#dc3545', fontSize: '0.875rem' }}>{cancelError}</div>
              )}
            </div>
          )}
        </div>
      </div>
    )
  }

  // Show loading/running state with steps (Backend status: 'running' from both systems)
  if (status.status === 'running' || (status.status === 'completed' && !status.results_dir)) {
    
    return (
      <div style={{ 
        flex: 1,
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column',
        padding: '2rem',
        gap: '2rem',
      }}>
        {/* Header with Progress */}
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🔄</div>
          <h2>Scan in Progress...</h2>
          <p style={{ opacity: 0.7, marginTop: '0.5rem' }}>
            Scan ID: {status.scan_id}
          </p>
          {status.scan_id && (
            <div style={{ marginTop: '1rem' }}>
              <button type="button" onClick={handleCancelScan} disabled={cancelLoading} style={cancelButtonStyle}>
                {cancelLoading ? 'Cancelling…' : 'Cancel scan'}
              </button>
              {cancelError && (
                <div style={{ marginTop: '0.5rem', color: '#dc3545', fontSize: '0.875rem' }}>{cancelError}</div>
              )}
            </div>
          )}

          {/* Progress Bar */}
          {steps.length > 0 && (
            <div style={{
              marginTop: '2rem',
              maxWidth: '800px',
              margin: '2rem auto 0',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.9rem', opacity: 0.8 }}>Progress</span>
                <strong style={{ fontSize: '1.1rem' }}>{progress}%</strong>
              </div>
              <div style={{
                width: '100%',
                height: '12px',
                background: 'var(--surface-muted)',
                borderRadius: '6px',
                overflow: 'hidden',
              }}>
                <div style={{
                  width: `${progress}%`,
                  height: '100%',
                  background: 'linear-gradient(90deg, #28a745, #20c997)',
                  transition: 'width 0.3s ease',
                }} />
              </div>
            </div>
          )}
        </div>

        {/* Steps Cards */}
        {steps.length > 0 && (
          <div className="scan-step-card-grid">
            {steps.map((step) => {
              const getStepColor = () => {
                switch (step.status) {
                  case 'completed': return '#28a745'
                  case 'running': return '#007bff'
                  case 'failed': return '#dc3545'
                  default: return '#6c757d'
                }
              }

              const getStepIcon = () => {
                switch (step.status) {
                  case 'completed': return '✅'
                  case 'running': return '⏳'
                  case 'failed': return '❌'
                  default: return '⏸️'
                }
              }

              const getSubStepIcon = (substepStatus: string) => {
                switch (substepStatus) {
                  case 'completed': return '✓'
                  case 'running': return '⟳'
                  case 'failed': return '✗'
                  default: return '○'
                }
              }

              const getSubStepColor = (substepStatus: string) => {
                switch (substepStatus) {
                  case 'completed': return '#28a745'
                  case 'running': return '#007bff'
                  case 'failed': return '#dc3545'
                  default: return '#6c757d'
                }
              }

              const subs = step.substeps ?? []
              const hasSubsteps = subs.length > 0
              const completedSubs = subs.filter((s) => s.status === 'completed').length
              const totalSubs = subs.length
              const subProgressPct = totalSubs > 0 ? Math.round((completedSubs / totalSubs) * 100) : 0
              const expanded = expandedStepNumbers.has(step.number)
              const borderColor = getStepColor()

              const current = hasSubsteps ? subs[subs.length - 1] : null
              const type = current?.type || 'action'
              const typeStyle =
                type === 'phase'
                  ? { badge: '🔹', bgColor: 'rgba(59, 130, 246, 0.15)', borderColor: 'rgba(59, 130, 246, 0.3)' }
                  : type === 'output'
                    ? { badge: '📄', bgColor: 'rgba(34, 197, 94, 0.15)', borderColor: 'rgba(34, 197, 94, 0.3)' }
                    : { badge: '⚙️', bgColor: 'rgba(0, 0, 0, 0.2)', borderColor: 'rgba(255, 255, 255, 0.1)' }

              return (
                <div
                  key={step.number}
                  className={`scan-step-card ${expanded ? 'scan-step-card-expanded' : ''}`}
                  style={{
                    padding: '1rem 1.25rem',
                    background: 'var(--glass-bg-main)',
                    border: `2px solid ${borderColor}`,
                    borderRadius: '12px',
                    transition: 'border-color 0.2s ease, opacity 0.2s ease',
                    opacity: step.status === 'pending' ? 0.65 : 1,
                    minHeight: expanded ? undefined : 220,
                    display: 'flex',
                    flexDirection: 'column',
                  }}
                >
                  <div
                    className={hasSubsteps ? 'scan-step-card-header scan-step-card-header--clickable' : 'scan-step-card-header'}
                    role={hasSubsteps ? 'button' : undefined}
                    tabIndex={hasSubsteps ? 0 : undefined}
                    aria-expanded={hasSubsteps ? expanded : undefined}
                    onClick={() => hasSubsteps && toggleStepExpand(step.number)}
                    onKeyDown={(e) => {
                      if (!hasSubsteps) return
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        toggleStepExpand(step.number)
                      }
                    }}
                  >
                    {hasSubsteps && (
                      <span
                        className={`scan-step-card-chevron${expanded ? ' scan-step-card-chevron--open' : ''}`}
                        aria-hidden
                      >
                        ▶
                      </span>
                    )}
                    <span className="scan-step-card-emoji">{getStepIcon()}</span>
                    <div className="scan-step-card-title-block">
                      <div className="scan-step-card-step-num">Step {step.number}</div>
                      <div className="scan-step-card-name">{step.name}</div>
                    </div>
                    {hasSubsteps && (
                      <span className="scan-step-card-count" title="Completed substeps / total">
                        {completedSubs}/{totalSubs}
                      </span>
                    )}
                    {(() => {
                      const elapsed = getStepElapsedSeconds(step)
                      if (elapsed == null && step.timeout_seconds == null) return null
                      return (
                        <span
                          className="scan-step-card-duration"
                          title={
                            step.timeout_seconds != null
                              ? elapsed != null
                                ? `Elapsed / max: ${formatDuration(elapsed)} / ${formatDuration(step.timeout_seconds)}`
                                : `Max duration: ${formatDuration(step.timeout_seconds)}`
                              : elapsed != null
                                ? `Elapsed: ${formatDuration(elapsed)}`
                                : undefined
                          }
                        >
                          {elapsed != null && formatDuration(elapsed)}
                          {elapsed != null && step.timeout_seconds != null && ' / '}
                          {step.timeout_seconds != null && `max ${formatDuration(step.timeout_seconds)}`}
                        </span>
                      )
                    })()}
                  </div>
                  {hasSubsteps && (
                    <div
                      className="scan-step-card-sub-bar"
                      title={`${completedSubs} of ${totalSubs} substeps completed`}
                    >
                      <div
                        className="scan-step-card-sub-bar-fill"
                        style={{
                          width: `${subProgressPct}%`,
                          background: borderColor,
                        }}
                      />
                    </div>
                  )}
                  {step.message && (
                    <div
                      className="scan-step-card-message"
                      title={step.message}
                    >
                      {step.message}
                    </div>
                  )}
                  {current && (
                    <SubstepSlot
                      current={current}
                      typeStyle={typeStyle}
                      getSubStepColor={(s) => getSubStepColor(s.status)}
                      getSubStepIcon={(s) => getSubStepIcon(s.status)}
                    />
                  )}
                  {step.status === 'running' && !hasSubsteps && (
                    <div className="scan-step-card-pulse-bar">
                      <div className="scan-step-card-pulse-bar-inner" />
                    </div>
                  )}
                  {hasSubsteps && (
                    <div
                      className={`scan-step-substeps-anim${expanded ? ' scan-step-substeps-anim--open' : ''}`}
                      aria-hidden={!expanded}
                    >
                      <div className="scan-step-substeps-anim-inner">
                        <div className="scan-step-substeps-panel">
                          <div className="scan-step-substeps-panel-title">All substeps</div>
                          <ul className="scan-step-substeps-list">
                            {subs.map((sub, idx) => {
                              const dur = formatSubstepDuration(sub)
                              return (
                                <li key={`${step.number}-${idx}-${sub.name}`} className="scan-step-substeps-row">
                                  <span
                                    className="scan-step-substeps-icon"
                                    style={{ color: getSubStepColor(sub.status) }}
                                  >
                                    {getSubStepIcon(sub.status)}
                                  </span>
                                  <span className="scan-step-substeps-name" title={sub.name}>
                                    {sub.name}
                                  </span>
                                  {sub.message && (
                                    <span className="scan-step-substeps-msg" title={sub.message}>
                                      {sub.message}
                                    </span>
                                  )}
                                  {dur && <span className="scan-step-substeps-time">{dur}</span>}
                                </li>
                              )
                            })}
                          </ul>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}

        {/* Logs Section removed - Backend sends logs: [] for security, no need to display */}
      </div>
    )
  }

  if (
    status.status === 'failed' ||
    status.status === 'cancelled' ||
    status.status === 'interrupted'
  ) {
    return (
      <div style={{ 
        flex: 1,
        minHeight: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem',
      }}>
        <div style={{
          maxWidth: '800px',
          width: '100%',
          background: 'rgba(220, 53, 69, 0.2)',
          border: '1px solid #dc3545',
          borderRadius: '8px',
          padding: '2rem',
          color: '#dc3545',
        }}>
          <strong style={{ fontSize: '1.5rem' }}>❌ Scan failed</strong>
          {status.error_message && (
            <div style={{ 
              marginTop: '1rem', 
              padding: '1rem', 
              background: 'var(--surface-muted)',
              borderRadius: '4px',
              fontFamily: 'monospace',
              fontSize: '0.9rem',
              wordBreak: 'break-word',
              whiteSpace: 'pre-wrap',
              maxHeight: '400px',
              overflowY: 'auto'
            }}>
              {status.error_message}
            </div>
          )}
          {status.error_code && (
            <div style={{ marginTop: '1rem', fontSize: '0.9rem', opacity: 0.8 }}>
              Exit code: {status.error_code}
            </div>
          )}
          <button
            onClick={() => navigate('/')}
            style={{
              marginTop: '1.5rem',
              padding: '0.75rem 1.5rem',
              background: '#dc3545',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 'bold',
            }}
          >
            Start New Scan
          </button>
        </div>
      </div>
    )
  }

  if (status.status === 'completed' && status.results_dir) {
    return (
      <div style={{ 
        position: 'relative',
        flex: 1,
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column',
      }}>
        <div style={{ 
          flex: 1,
          overflow: 'hidden',
          position: 'relative',
        }}>
          <ReportViewer scanId={status.scan_id} />
        </div>

        {/* Floating Action Buttons */}
        <div style={{
          position: 'fixed',
          bottom: '2rem',
          right: '2rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
          zIndex: 100,
        }}>
          <button
            onClick={() => setIsStepsSidebarOpen(true)}
            style={{
              padding: '1rem',
              background: 'var(--glass-bg-main)',
              backdropFilter: 'blur(10px)',
              border: '1px solid var(--glass-border-main)',
              borderRadius: '50%',
              width: '56px',
              height: '56px',
              color: 'var(--text-main)',
              cursor: 'pointer',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
              fontSize: '1.5rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            title="View Steps"
          >
            📋
          </button>
          <button
            onClick={() => setIsLogsSidebarOpen(true)}
            style={{
              padding: '1rem',
              background: 'var(--glass-bg-main)',
              backdropFilter: 'blur(10px)',
              border: '1px solid var(--glass-border-main)',
              borderRadius: '50%',
              width: '56px',
              height: '56px',
              color: 'var(--text-main)',
              cursor: 'pointer',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
              fontSize: '1.5rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            title="View Logs"
          >
            📄
          </button>
        </div>

        {/* Steps Sidebar */}
        <StepsSidebar
          isOpen={isStepsSidebarOpen}
          onClose={() => setIsStepsSidebarOpen(false)}
          scanId={status.scan_id}
        />

        {/* Logs Sidebar */}
        {isLogsSidebarOpen && (
          <>
            <div
              style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'var(--modal-overlay-bg)',
                zIndex: 999,
              }}
              onClick={() => setIsLogsSidebarOpen(false)}
            />
            <div
              style={{
                position: 'fixed',
                top: 0,
                right: 0,
                bottom: 0,
                width: '500px',
                maxWidth: '90vw',
                background: 'var(--glass-bg-main)',
                backdropFilter: 'blur(20px)',
                borderLeft: '1px solid var(--glass-border-main)',
                boxShadow: 'var(--shadow-main)',
                zIndex: 1000,
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  padding: '1.5rem',
                  borderBottom: '1px solid var(--glass-border-main)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <h2 style={{ margin: 0, fontSize: '1.25rem' }}>📄 Scan Logs</h2>
                <button
                  onClick={() => setIsLogsSidebarOpen(false)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    fontSize: '1.5rem',
                    cursor: 'pointer',
                    color: 'var(--text-main)',
                    padding: '0.25rem 0.5rem',
                    lineHeight: 1,
                  }}
                  title="Close"
                >
                  ✕
                </button>
              </div>
              <div
                style={{
                  flex: 1,
                  overflow: 'auto',
                  padding: '1.5rem',
                }}
              >
                <div style={{ opacity: 0.7, textAlign: 'center', padding: '2rem' }}>
                  Logs are not displayed for security reasons.
                </div>
              </div>
            </div>
          </>
        )}

        {/* AI Prompt Modal */}
        <AIPromptModal
          isOpen={isAIPromptModalOpen}
          onClose={() => setIsAIPromptModalOpen(false)}
          scanId={status.scan_id}
        />
      </div>
    )
  }

  // Default: No scan
  return (
    <div style={{ 
      flex: 1,
      minHeight: 0,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }}>
      <div style={{ textAlign: 'center' }}>
        <h2>No active scan</h2>
        <button
          onClick={() => navigate('/')}
          style={{
            marginTop: '1rem',
            padding: '0.75rem 1.5rem',
            background: 'var(--glass-bg-main)',
            border: '1px solid var(--glass-border-main)',
            borderRadius: '8px',
            color: 'var(--text-main)',
            cursor: 'pointer',
          }}
        >
          Start New Scan
        </button>
      </div>
    </div>
  )
}