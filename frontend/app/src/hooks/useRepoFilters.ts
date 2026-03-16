import { useMemo } from 'react'
import { GitHubRepo, RepoScanStatus, FilterType, SortType, getRepoStatus } from '../utils/repoUtils'

export function useRepoFilters(
  repos: GitHubRepo[],
  scanStatuses: Record<string, RepoScanStatus>,
  filter: FilterType,
  sortBy: SortType,
  searchQuery: string
) {
  const filteredAndSortedRepos = useMemo(() => {
    let filtered = repos.filter(repo => {
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        const fullName = `${repo.repo_owner || ''}/${repo.repo_name}`.toLowerCase()
        if (!fullName.includes(query) && !repo.repo_url.toLowerCase().includes(query)) {
          return false
        }
      }
      
      // Status filter
      if (filter !== 'all') {
        const status = getRepoStatus(repo, scanStatuses[repo.id])
        if (filter === 'healthy' && status.type !== 'healthy') return false
        if (filter === 'needs_attention' && status.type !== 'needs_attention') return false
        if (filter === 'critical' && status.type !== 'critical') return false
        if (filter === 'not_scanned' && status.type !== 'not_scanned') return false
      }
      
      return true
    })
    
    // Sort
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'score':
          const scoreA = a.score ?? 0
          const scoreB = b.score ?? 0
          return scoreB - scoreA
        case 'last_scan':
          const dateA = a.last_scan?.created_at ? new Date(a.last_scan.created_at).getTime() : 0
          const dateB = b.last_scan?.created_at ? new Date(b.last_scan.created_at).getTime() : 0
          return dateB - dateA
        case 'vulnerabilities':
          const vulnA = (a.vulnerabilities?.critical || 0) + (a.vulnerabilities?.high || 0) + (a.vulnerabilities?.medium || 0) + (a.vulnerabilities?.low || 0)
          const vulnB = (b.vulnerabilities?.critical || 0) + (b.vulnerabilities?.high || 0) + (b.vulnerabilities?.medium || 0) + (b.vulnerabilities?.low || 0)
          return vulnB - vulnA
        case 'name':
        default:
          const nameA = `${a.repo_owner || ''}/${a.repo_name}`.toLowerCase()
          const nameB = `${b.repo_owner || ''}/${b.repo_name}`.toLowerCase()
          return nameA.localeCompare(nameB)
      }
    })
    
    return filtered
  }, [repos, scanStatuses, filter, sortBy, searchQuery])

  return filteredAndSortedRepos
}
