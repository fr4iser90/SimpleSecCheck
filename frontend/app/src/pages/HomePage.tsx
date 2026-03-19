import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ScanForm from '../components/ScanForm'
import BulkScanForm from '../components/BulkScanForm'
import ScannerDataUpdate from '../components/ScannerDataUpdate'
import { useConfig } from '../hooks/useConfig'
import { useAuth } from '../hooks/useAuth'

import type { ScanStatusState } from '../types/scanStatus'

type ScanStatusData = ScanStatusState

export default function HomePage() {
  const navigate = useNavigate()
  const { config, loading } = useConfig()
  const { token } = useAuth()
  const [activeTab, setActiveTab] = useState<'single' | 'bulk'>('single')
  const isAuthenticated = !!token
  // Bulk scan: logged-in users always see tab when feature is on; guests only when admin enabled bulk_scan_allow_guests
  const showBulkScan = (config?.features.bulk_scan ?? true) && (isAuthenticated || (config?.features.bulk_scan_allow_guests ?? false))

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
            borderBottom: '1px solid var(--glass-border-main)'
          }}>
            <button
              type="button"
              onClick={() => setActiveTab('single')}
              style={{
                padding: '0.75rem 1.5rem',
                border: 'none',
                background: 'transparent',
                borderBottom: activeTab === 'single' ? '2px solid var(--accent)' : '2px solid transparent',
                color: activeTab === 'single' ? 'var(--accent)' : 'var(--text-secondary)',
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
                borderBottom: activeTab === 'bulk' ? '2px solid var(--accent)' : '2px solid transparent',
                color: activeTab === 'bulk' ? 'var(--accent)' : 'var(--text-secondary)',
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
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
            Loading configuration...
          </div>
        ) : showBulkScan && activeTab === 'bulk' ? (
          <BulkScanForm onBatchStart={handleBatchStart} />
        ) : (
          <ScanForm onScanStart={handleScanStart} config={config} />
        )}
      </div>

      {/* Scanner Asset Updates */}
      <div className="card" style={{ marginTop: '2rem' }}>
        <ScannerDataUpdate />
      </div>
    </div>
  )
}
