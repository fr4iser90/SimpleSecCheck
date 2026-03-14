/**
 * API Client with automatic Authorization header and token refresh
 * 
 * Automatically adds Authorization header to all requests if token is available.
 * Handles token refresh on 401 errors.
 */

const TOKEN_STORAGE_KEY = 'auth_token'
const USER_STORAGE_KEY = 'auth_user'

let refreshPromise: Promise<string | null> | null = null

async function refreshToken(): Promise<string | null> {
  // If refresh is already in progress, wait for it
  if (refreshPromise) {
    return refreshPromise
  }

  refreshPromise = (async () => {
    try {
      const token = localStorage.getItem(TOKEN_STORAGE_KEY)
      if (!token) {
        return null
      }

      const response = await fetch('/api/v1/auth/refresh', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (response.ok) {
        const data = await response.json()
        const newToken = data.access_token
        
        // Update token in storage
        localStorage.setItem(TOKEN_STORAGE_KEY, newToken)
        
        // Update user info if provided
        if (data.user_id && data.email) {
          localStorage.setItem(USER_STORAGE_KEY, JSON.stringify({
            user_id: data.user_id,
            email: data.email,
            name: data.name
          }))
        }
        
        return newToken
      } else {
        // Refresh failed, clear token
        localStorage.removeItem(TOKEN_STORAGE_KEY)
        localStorage.removeItem(USER_STORAGE_KEY)
        return null
      }
    } catch (error) {
      console.error('Token refresh failed:', error)
      localStorage.removeItem(TOKEN_STORAGE_KEY)
      localStorage.removeItem(USER_STORAGE_KEY)
      return null
    } finally {
      refreshPromise = null
    }
  })()

  return refreshPromise
}

export async function apiFetch(
  url: string,
  options: RequestInit = {},
  retryOn401: boolean = true
): Promise<Response> {
  // Get token from storage
  let token = localStorage.getItem(TOKEN_STORAGE_KEY)
  
  // Add Authorization header if token exists
  const headers = new Headers(options.headers)
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  
  // Merge with existing headers
  const mergedOptions: RequestInit = {
    ...options,
    headers
  }
  
  let response = await fetch(url, mergedOptions)
  
  // If 401 and retry enabled, try to refresh token
  if (response.status === 401 && retryOn401 && token) {
    const newToken = await refreshToken()
    
    if (newToken) {
      // Retry request with new token
      headers.set('Authorization', `Bearer ${newToken}`)
      const retryOptions: RequestInit = {
        ...options,
        headers
      }
      response = await fetch(url, retryOptions)
    } else {
      // Refresh failed, redirect to login if we're not already there
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }
  }
  
  return response
}
