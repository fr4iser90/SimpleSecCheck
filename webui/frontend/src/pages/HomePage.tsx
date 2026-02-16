import { useNavigate } from 'react-router-dom'
import ScanForm from '../components/ScanForm'

interface ScanStatusData {
  status: 'idle' | 'running' | 'done' | 'error'
  scan_id: string | null
  results_dir: string | null
  started_at: string | null
  error_code?: number | null
  error_message?: string | null
}

export default function HomePage() {
  const navigate = useNavigate()

  const handleScanStart = (scanStatus: ScanStatusData) => {
    navigate('/scan', { state: scanStatus })
  }

  return (
    <div className="container">
      <div className="card">
        <h2>Start New Scan</h2>
        <p style={{ marginBottom: '2rem', opacity: 0.8 }}>
          Single-shot security scanner. Each scan is independent. No history is stored.
        </p>
        <ScanForm onScanStart={handleScanStart} />
      </div>
    </div>
  )
}
