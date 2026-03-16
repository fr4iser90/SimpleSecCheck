import { useState, useEffect } from 'react'
import { apiFetch } from '../utils/apiClient'
import { GitHubRepo, RepoScanStatus } from '../utils/repoUtils'

export function useRepos() {
  const [repos, setRepos] = useState<GitHubRepo[]>([])
  const [scanStatuses, setScanStatuses] = useState<Record<string, RepoScanStatus>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadRepos = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiFetch('/api/user/github/repos')
      if (response.ok) {
        const data = await response.json()
        setRepos(data)
        
        // Load scan statuses for all repos
        const statusPromises = data.map(async (repo: GitHubRepo) => {
          try {
            const statusResponse = await apiFetch(`/api/user/github/repos/${repo.id}/scan-status`)
            if (statusResponse.ok) {
              const statusData = await statusResponse.json()
              return { repoId: repo.id, status: statusData }
            }
          } catch (error) {
            console.error(`Failed to load scan status for repo ${repo.id}:`, error)
          }
          return { repoId: repo.id, status: { has_active_scan: false, status: null, scan_id: null, queue_position: null } }
        })
        
        const statusResults = await Promise.all(statusPromises)
        const statusMap: Record<string, RepoScanStatus> = {}
        statusResults.forEach(({ repoId, status }) => {
          statusMap[repoId] = status
        })
        setScanStatuses(statusMap)
      } else {
        setError('Failed to load repositories')
      }
    } catch (error) {
      console.error('Failed to load repos:', error)
      setError('Failed to load repositories')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRepos()
    const interval = setInterval(loadRepos, 30000)
    return () => clearInterval(interval)
  }, [])

  return { repos, scanStatuses, loading, error, loadRepos }
}
