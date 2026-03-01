import { useLocation, useNavigate } from 'react-router-dom'
import BatchProgress from '../components/BatchProgress'

export default function BatchProgressPage() {
  const location = useLocation()
  const navigate = useNavigate()
  
  const batchId = location.state?.batchId

  if (!batchId) {
    return (
      <div className="container">
        <div className="card">
          <h2>Batch Scan Not Found</h2>
          <p>No batch scan ID provided.</p>
          <button
            onClick={() => navigate('/')}
            className="primary"
            style={{ marginTop: '1rem' }}
          >
            Back to Home
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="container">
      <div className="card">
        <BatchProgress batchId={batchId} />
      </div>
    </div>
  )
}
