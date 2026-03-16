import { useState, useEffect } from 'react'
import { apiFetch } from '../utils/apiClient'

interface Scanner {
  name: string
  description?: string
  scan_types?: string[]
}

export function useScanners(scanType: string = 'code') {
  const [scanners, setScanners] = useState<Scanner[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadScanners = async () => {
      try {
        const response = await apiFetch(`/api/scanners?scan_type=${scanType}`)
        if (response.ok) {
          const data = await response.json()
          setScanners(data.scanners || [])
        }
      } catch (error) {
        console.error('Failed to load scanners:', error)
      } finally {
        setLoading(false)
      }
    }
    
    loadScanners()
  }, [scanType])

  return { scanners, loading }
}
