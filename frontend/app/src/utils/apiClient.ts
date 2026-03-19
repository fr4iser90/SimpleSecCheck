import { resolveApiUrl } from './resolveApiUrl'

/**
 * API Client: access token in memory only, refresh via HttpOnly cookie.
 * - All requests send credentials so the refresh_token cookie is sent when needed.
 * - On 401 we call /refresh (cookie only); backend returns new access_token in body.
 */

let tokenGetter: (() => string | null) | null = null
let onTokenRefreshed: ((newToken: string, user?: { user_id: string; email: string; name?: string; role?: string }) => void) | null = null
let onUnauthorized: (() => void) | null = null

export function setTokenGetter(getter: () => string | null): void {
  tokenGetter = getter
}

export function setOnTokenRefreshed(cb: (newToken: string, user?: { user_id: string; email: string; name?: string; role?: string }) => void): void {
  onTokenRefreshed = cb
}

export function setOnUnauthorized(cb: () => void): void {
  onUnauthorized = cb
}

let refreshPromise: Promise<string | null> | null = null

/** Refresh using HttpOnly cookie only (no Bearer). Returns new access_token or null. */
async function refreshToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise
  refreshPromise = (async () => {
    try {
      const response = await fetch(resolveApiUrl('/api/v1/auth/refresh'), {
        method: 'POST',
        credentials: 'include',
      })
      if (response.ok) {
        const data = await response.json()
        const newToken = data.access_token
        if (onTokenRefreshed && newToken) {
          onTokenRefreshed(newToken, {
            user_id: data.user_id,
            email: data.email,
            name: data.name,
            role: data.role
          })
        }
        return newToken
      }
      onUnauthorized?.()
      return null
    } catch (error) {
      console.error('Token refresh failed:', error)
      onUnauthorized?.()
      return null
    } finally {
      refreshPromise = null
    }
  })()
  return refreshPromise
}

const defaultCredentials: RequestCredentials = 'include'

export async function apiFetch(
  url: string,
  options: RequestInit = {},
  retryOn401: boolean = true
): Promise<Response> {
  const token = tokenGetter?.() ?? null
  const headers = new Headers(options.headers)
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  const resolvedUrl = resolveApiUrl(url)
  let response = await fetch(resolvedUrl, {
    ...options,
    headers,
    credentials: options.credentials ?? defaultCredentials,
  })

  if (response.status === 401 && retryOn401) {
    const newToken = await refreshToken()
    if (newToken) {
      headers.set('Authorization', `Bearer ${newToken}`)
      response = await fetch(resolvedUrl, {
        ...options,
        headers,
        credentials: options.credentials ?? defaultCredentials,
      })
    } else {
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }
  }
  return response
}
