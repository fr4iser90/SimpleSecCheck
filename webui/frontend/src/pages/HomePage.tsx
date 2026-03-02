import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ScanForm from '../components/ScanForm'
import BulkScanForm from '../components/BulkScanForm'
import OwaspUpdate from '../components/OwaspUpdate'
import { useConfig } from '../hooks/useConfig'

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
  const { config, loading } = useConfig()
  const [activeTab, setActiveTab] = useState<'single' | 'bulk'>('single')
  
  // Only show bulk scan tab if enabled
  const showBulkScan = config?.features.bulk_scan ?? true

  const handleScanStart = (scanStatus: ScanStatusData) => {
    navigate('/scan', { state: scanStatus })
  }

  const handleBatchStart = (batchId: string) => {
    navigate('/bulk', { state: { batchId } })
  }

  return (
    <div className="container">
      <div className="card">
        <h2>Start New Scan</h2>
        <p style={{ marginBottom: '2rem', opacity: 0.8 }}>
          Single-shot security scanner. Each scan is independent. No history is stored.
        </p>

        {/* Tab Navigation - Only show if bulk scan is enabled */}
        {showBulkScan && (
          <div style={{
            display: 'flex',
            gap: '0.5rem',
            marginBottom: '2rem',
            borderBottom: '2px solid #e9ecef'
          }}>
            <button
              type="button"
              onClick={() => setActiveTab('single')}
              style={{
                padding: '0.75rem 1.5rem',
                border: 'none',
                background: 'transparent',
                borderBottom: activeTab === 'single' ? '2px solid #007bff' : '2px solid transparent',
                color: activeTab === 'single' ? '#007bff' : '#6c757d',
                fontWeight: activeTab === 'single' ? 'bold' : 'normal',
                cursor: 'pointer',
                marginBottom: '-2px'
              }}
            >
              Single Repository
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('bulk')}
              style={{
                padding: '0.75rem 1.5rem',
                border: 'none',
                background: 'transparent',
                borderBottom: activeTab === 'bulk' ? '2px solid #007bff' : '2px solid transparent',
                color: activeTab === 'bulk' ? '#007bff' : '#6c757d',
                fontWeight: activeTab === 'bulk' ? 'bold' : 'normal',
                cursor: 'pointer',
                marginBottom: '-2px'
              }}
            >
              Bulk Scan (Multiple Repos)
            </button>
          </div>
        )}

        {/* Tab Content */}
        {loading ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#6c757d' }}>
            Loading configuration...
          </div>
        ) : showBulkScan && activeTab === 'bulk' ? (
          <BulkScanForm onBatchStart={handleBatchStart} />
        ) : (
          <ScanForm onScanStart={handleScanStart} config={config} />
        )}
      </div>

      <div className="card" style={{ marginTop: '2rem' }}>
        <OwaspUpdate />
      </div>
    </div>
  )
}
