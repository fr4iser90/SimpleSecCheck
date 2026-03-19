import { useState, useEffect, useRef, createContext, useContext, ReactNode } from 'react'
import { useConfig } from './useConfig'
import * as apiClient from '../utils/apiClient'
import { resolveApiUrl } from '../utils/resolveApiUrl'

interface User {
  user_id: string
  email: string
  name?: string
  role?: string
}

interface AuthContextType {
  isAuthenticated: boolean
  user: User | null
  token: string | null
  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>
  logout: () => Promise<void>
  loading: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const { config } = useConfig()
  const [token, setToken] = useState<string | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const tokenRef = useRef<string | null>(null)

  tokenRef.current = token

  useEffect(() => {
    apiClient.setTokenGetter(() => tokenRef.current)
    apiClient.setOnTokenRefreshed((newToken, userData) => {
      setToken(newToken)
      if (userData) {
        setUser({
          user_id: userData.user_id,
          email: userData.email,
          name: userData.name,
          role: userData.role
        })
      }
    })
    apiClient.setOnUnauthorized(() => {
      setToken(null)
      setUser(null)
    })
  }, [])

  // Restore session from HttpOnly refresh_token cookie (reload / new tab)
  useEffect(() => {
    let cancelled = false
    fetch(resolveApiUrl('/api/v1/auth/refresh'), { method: 'POST', credentials: 'include' })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!cancelled && data?.access_token) {
          setToken(data.access_token)
          setUser({
            user_id: data.user_id,
            email: data.email,
            name: data.name,
            role: data.role
          })
        }
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    if (token && config?.login_required) {
      verifyToken()
    }
  }, [token, config?.login_required])

  const verifyToken = async () => {
    if (!token) return
    try {
      const response = await apiClient.apiFetch('/api/v1/auth/me', {}, false)
      if (response.ok) {
        const data = await response.json()
        setUser({
          user_id: data.user_id,
          email: data.email,
          name: data.name,
          role: data.role
        })
      } else {
        setToken(null)
        setUser(null)
      }
    } catch {
      setToken(null)
      setUser(null)
    }
  }

  const login = async (email: string, password: string, _rememberMe: boolean = false) => {
    const response = await apiClient.apiFetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    }, false)

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Login failed' }))
      throw new Error(error.detail || 'Login failed')
    }

    const data = await response.json()
    setToken(data.access_token)
    setUser({
      user_id: data.user_id,
      email: data.email,
      name: data.name,
      role: data.role
    })
  }

  const logout = async () => {
    try {
      if (token) {
        await apiClient.apiFetch('/api/v1/auth/logout', { method: 'POST' }, false)
      }
    } catch {
      // ignore
    } finally {
      setToken(null)
      setUser(null)
    }
  }

  const isAuthenticated = token !== null && user !== null

  return (
    <AuthContext.Provider value={{
      isAuthenticated,
      user,
      token,
      login,
      logout,
      loading
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
