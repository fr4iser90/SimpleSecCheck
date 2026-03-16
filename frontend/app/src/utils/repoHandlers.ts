import { apiFetch } from './apiClient'
import { GitHubRepo } from './repoUtils'

export async function addRepo(formData: any): Promise<{ success: boolean; error?: string }> {
  try {
    const response = await apiFetch('/api/user/github/repos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    })
    
    if (response.ok) {
      return { success: true }
    } else {
      const error = await response.json()
      return { success: false, error: error.detail || 'Failed to add repository' }
    }
  } catch (error) {
    console.error('Failed to add repo:', error)
    return { success: false, error: 'Failed to add repository' }
  }
}

export async function updateRepo(repoId: string, formData: any): Promise<{ success: boolean; error?: string }> {
  try {
    const response = await apiFetch(`/api/user/github/repos/${repoId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    })
    
    if (response.ok) {
      return { success: true }
    } else {
      const error = await response.json()
      return { success: false, error: error.detail || 'Failed to update repository' }
    }
  } catch (error) {
    console.error('Failed to update repo:', error)
    return { success: false, error: 'Failed to update repository' }
  }
}

export async function removeRepo(repoId: string): Promise<{ success: boolean; error?: string }> {
  try {
    const response = await apiFetch(`/api/user/github/repos/${repoId}`, {
      method: 'DELETE'
    })
    
    if (response.ok) {
      return { success: true }
    } else {
      const error = await response.json()
      return { success: false, error: error.detail || 'Failed to remove repository' }
    }
  } catch (error) {
    console.error('Failed to remove repo:', error)
    return { success: false, error: 'Failed to remove repository' }
  }
}

export async function triggerScan(repoId: string): Promise<{ success: boolean; error?: string }> {
  try {
    const response = await apiFetch(`/api/user/github/repos/${repoId}/scan`, {
      method: 'POST'
    })
    
    if (response.ok) {
      return { success: true }
    } else {
      const error = await response.json()
      return { success: false, error: error.detail || 'Failed to trigger scan' }
    }
  } catch (error) {
    console.error('Failed to trigger scan:', error)
    return { success: false, error: 'Failed to trigger scan' }
  }
}

export async function bulkUpdateScanners(repos: GitHubRepo[], scanners: string[]): Promise<{ successCount: number; errorCount: number }> {
  let successCount = 0
  let errorCount = 0

  for (const repo of repos) {
    try {
      const response = await apiFetch(`/api/user/github/repos/${repo.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scanners })
      })
      
      if (response.ok) {
        successCount++
      } else {
        errorCount++
      }
    } catch (error) {
      errorCount++
    }
  }

  return { successCount, errorCount }
}

export async function discoverRepos(username: string): Promise<{ success: boolean; repos?: any[]; error?: string }> {
  try {
    const response = await apiFetch(`/api/git/repos?username=${encodeURIComponent(username.trim())}`)
    if (response.ok) {
      const data = await response.json()
      return { success: true, repos: data.repos || [] }
    } else {
      const error = await response.json()
      return { success: false, error: error.detail || 'Failed to discover repositories' }
    }
  } catch (error) {
    console.error('Failed to discover repos:', error)
    return { success: false, error: 'Failed to discover repositories. Make sure the username/organization exists.' }
  }
}

export async function addSelectedRepos(discoveredRepos: any[], selectedRepos: Set<string>): Promise<{ successCount: number; errorCount: number }> {
  let successCount = 0
  let errorCount = 0

  const reposToAdd = discoveredRepos.filter(repo => selectedRepos.has(repo.full_name))

  for (const repo of reposToAdd) {
    try {
      const response = await apiFetch('/api/user/github/repos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_url: repo.html_url,
          repo_owner: repo.full_name.split('/')[0],
          repo_name: repo.full_name.split('/')[1] || repo.name,
          branch: repo.default_branch || 'main',
          auto_scan_enabled: true,
          scan_on_push: true,
          scan_frequency: 'on_push'
        })
      })
      
      if (response.ok) {
        successCount++
      } else {
        errorCount++
      }
    } catch (error) {
      errorCount++
    }
  }

  return { successCount, errorCount }
}
