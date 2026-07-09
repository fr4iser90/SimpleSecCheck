import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ScanForm from '../components/ScanForm'
import BulkScanForm from '../components/BulkScanForm'
import ScannerDataUpdate from '../components/ScannerDataUpdate'
import PageHeader from '../components/PageHeader'
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
  const showBulkScan = (config?.features.bulk_scan ?? true) && (isAuthenticated || (config?.features.bulk_scan_allow_guests ?? false))

  const handleScanStart = (scanStatus: ScanStatusData) => {
    navigate('/scan', { state: scanStatus })
  }

  const handleBatchStart = (batchId: string) => {
    navigate('/bulk', { state: { batchId } })
  }

  return (
    <div className="container">
      <PageHeader
        title="Start New Scan"
        subtitle="Configure a security scan for a repository, container, or target."
      >
        {showBulkScan ? (
          <div className="segmented-tabs">
            <button
              type="button"
              className={`segmented-tab${activeTab === 'single' ? ' segmented-tab--active' : ''}`}
              onClick={() => setActiveTab('single')}
            >
              Single target
            </button>
            <button
              type="button"
              className={`segmented-tab${activeTab === 'bulk' ? ' segmented-tab--active' : ''}`}
              onClick={() => setActiveTab('bulk')}
            >
              Bulk scan
            </button>
          </div>
        ) : null}
      </PageHeader>

      {loading ? (
        <div className="panel">
          <div className="panel__body" style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
            Loading configuration…
          </div>
        </div>
      ) : showBulkScan && activeTab === 'bulk' ? (
        <div className="panel">
          <div className="panel__header">
            <h2 className="panel__title">Bulk scan</h2>
            <p className="panel__desc">Scan multiple repositories in one batch.</p>
          </div>
          <div className="panel__body">
            <BulkScanForm onBatchStart={handleBatchStart} />
          </div>
        </div>
      ) : (
        <ScanForm onScanStart={handleScanStart} config={config} />
      )}

      <div className="panel">
        <div className="panel__header">
          <h2 className="panel__title">Scanner assets</h2>
          <p className="panel__desc">Vulnerability databases and rule bundles.</p>
        </div>
        <div className="panel__body">
          <ScannerDataUpdate />
        </div>
      </div>
    </div>
  )
}
