import { GITHUB_REPO, HAS_DONATE_LINK, SUPPORT_DONATE_URL } from '../constants/support'
import { formatEstimatedTime } from '../utils/timeUtils'

interface AsideStep {
  number: number
  name: string
  status: string
}

interface QueueSummary {
  position?: number
  repository_name?: string
  estimated_wait_seconds?: number | null
  estimated_time_seconds?: number | null
}

interface ScanProgressAsideProps {
  mode: 'pending' | 'running'
  progress?: number
  steps?: AsideStep[]
  queueStatus?: QueueSummary | null
  scanId?: string | null
}

export default function ScanProgressAside({
  mode,
  progress = 0,
  steps = [],
  queueStatus,
  scanId,
}: ScanProgressAsideProps) {
  const completed = steps.filter((s) => s.status === 'completed').length
  const total = steps.length
  const runningStep = steps.find((s) => s.status === 'running')

  return (
    <div className="scan-progress-aside">
      <section className="scan-progress-aside__panel">
        <h3 className="scan-progress-aside__title">Scan status</h3>
        {mode === 'pending' && queueStatus ? (
          <dl className="scan-progress-aside__kv">
            {queueStatus.repository_name ? (
              <div>
                <dt>Repository</dt>
                <dd>{queueStatus.repository_name}</dd>
              </div>
            ) : null}
            {queueStatus.position != null ? (
              <div>
                <dt>Queue position</dt>
                <dd>#{queueStatus.position}</dd>
              </div>
            ) : null}
            {queueStatus.estimated_wait_seconds != null && queueStatus.estimated_wait_seconds > 0 ? (
              <div>
                <dt>Estimated wait</dt>
                <dd>{formatEstimatedTime(queueStatus.estimated_wait_seconds)}</dd>
              </div>
            ) : null}
          </dl>
        ) : (
          <dl className="scan-progress-aside__kv">
            <div>
              <dt>Progress</dt>
              <dd>{progress}%</dd>
            </div>
            {total > 0 ? (
              <div>
                <dt>Steps</dt>
                <dd>
                  {completed} / {total}
                </dd>
              </div>
            ) : null}
            {runningStep ? (
              <div>
                <dt>Current</dt>
                <dd>
                  Step {runningStep.number}: {runningStep.name}
                </dd>
              </div>
            ) : null}
            {queueStatus?.estimated_time_seconds != null && queueStatus.estimated_time_seconds > 0 ? (
              <div>
                <dt>Est. duration</dt>
                <dd>{formatEstimatedTime(queueStatus.estimated_time_seconds)}</dd>
              </div>
            ) : null}
          </dl>
        )}
        {scanId ? (
          <p className="scan-progress-aside__scan-id" title={scanId}>
            ID: {scanId.slice(0, 8)}…
          </p>
        ) : null}
      </section>

      <section className="scan-progress-aside__panel scan-progress-aside__panel--support">
        <h3 className="scan-progress-aside__title">Support SimpleSecCheck</h3>
        <p className="scan-progress-aside__text">
          Open source — donations help cover hosting and scanner infrastructure while your scan runs.
        </p>
        <div className="scan-progress-aside__actions">
          {HAS_DONATE_LINK ? (
            <a
              href={SUPPORT_DONATE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-primary scan-progress-aside__donate"
            >
              Donate
            </a>
          ) : null}
          <a
            href={GITHUB_REPO}
            target="_blank"
            rel="noopener noreferrer"
            className={HAS_DONATE_LINK ? 'btn-secondary' : 'btn-primary'}
          >
            {HAS_DONATE_LINK ? 'Star on GitHub' : 'Support on GitHub'}
          </a>
        </div>
      </section>
    </div>
  )
}
