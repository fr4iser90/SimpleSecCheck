/** Parsed git hosting identity for workflow links (no repo write from the app). */
export type ParsedRepo =
  | { provider: 'github'; host: string; owner: string; repo: string }
  | { provider: 'gitlab'; host: string; owner: string; repo: string }

const MAX_QUERY_BODY = 6000

/**
 * Parse GitHub / GitLab HTTPS or `git@github.com:owner/repo` into owner/repo.
 */
export function parseGitRemoteUrl(input: string): ParsedRepo | null {
  if (!input || typeof input !== 'string') return null
  const s = input.trim()

  const sshGithub = /^git@github\.com:([^/]+)\/([^/]+?)(\.git)?$/i.exec(s)
  if (sshGithub) {
    return { provider: 'github', host: 'github.com', owner: sshGithub[1], repo: stripGit(sshGithub[2]) }
  }

  const sshGitlab = /^git@([^:]+):([^/]+)\/([^/]+?)(\.git)?$/i.exec(s)
  if (sshGitlab && sshGitlab[1].includes('gitlab')) {
    return { provider: 'gitlab', host: sshGitlab[1], owner: sshGitlab[2], repo: stripGit(sshGitlab[3]) }
  }

  try {
    const u = new URL(s.startsWith('http') ? s : `https://${s}`)
    const pathParts = u.pathname.split('/').filter(Boolean)
    if (pathParts.length < 2) return null
    const hn = u.hostname.replace(/^www\./, '')

    if (hn === 'github.com' || hn.endsWith('.github.com')) {
      if (pathParts.length >= 2) {
        return {
          provider: 'github',
          host: hn,
          owner: pathParts[0],
          repo: stripGit(pathParts[1]),
        }
      }
    }

    if (hn.includes('gitlab') || hn === 'gitlab.com') {
      if (pathParts.length >= 2) {
        const repo = stripGit(pathParts[pathParts.length - 1])
        const owner = pathParts.slice(0, -1).join('/')
        return {
          provider: 'gitlab',
          host: hn,
          owner,
          repo,
        }
      }
    }
  } catch {
    return null
  }

  return null
}

function stripGit(name: string): string {
  return name.replace(/\.git$/i, '')
}

export function truncateForUrlQuery(text: string, max = MAX_QUERY_BODY): string {
  if (text.length <= max) return text
  return `${text.slice(0, max - 80)}\n\n…(truncated — use downloaded fix.md for full text)`
}

/** GitHub: new issue with prefilled title/body. */
export function githubNewIssueUrl(owner: string, repo: string, title: string, body: string): string {
  const q = new URLSearchParams()
  q.set('title', title)
  q.set('body', truncateForUrlQuery(body))
  return `https://github.com/${owner}/${repo}/issues/new?${q.toString()}`
}

/** GitHub: open compare to start a PR after pushing `head` branch. */
export function githubComparePrUrl(owner: string, repo: string, base: string, head: string): string {
  const b = encodeURIComponent(base)
  const h = encodeURIComponent(head)
  return `https://github.com/${owner}/${repo}/compare/${b}...${h}?expand=1`
}

/** GitLab: new issue (title/body via query; length limits vary by instance). */
export function gitlabNewIssueUrl(host: string, owner: string, repo: string, title: string, body: string): string {
  const q = new URLSearchParams()
  q.set('issue[title]', title)
  q.set('issue[description]', truncateForUrlQuery(body))
  return `https://${host}/${owner}/${repo}/-/issues/new?${q.toString()}`
}

/** GitLab: new merge request (user may need to adjust branches in UI). */
export function gitlabNewMrUrl(host: string, owner: string, repo: string): string {
  return `https://${host}/${owner}/${repo}/-/merge_requests/new`
}

export function downloadTextFile(filename: string, content: string, mime = 'text/markdown;charset=utf-8'): void {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.rel = 'noopener'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
