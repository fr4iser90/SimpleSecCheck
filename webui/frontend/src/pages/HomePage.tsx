import { useNavigate } from 'react-router-dom'
import ScanForm from '../components/ScanForm'

export default function HomePage() {
  const navigate = useNavigate()

  const handleScanStart = () => {
    navigate('/scan')
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
