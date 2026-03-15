import { useState, useEffect, createContext, useContext, ReactNode } from 'react'
import { useConfig } from './useConfig'

interface User {
  user_id: string
  email: string
  name?: string
  role?: string  // 'admin' or 'user'
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

const TOKEN_STORAGE_KEY = 'auth_token'
const USER_STORAGE_KEY = 'auth_user'

export function AuthProvider({ children }: { children: ReactNode }) {
  const { config } = useConfig()
  const [token, setToken] = useState<string | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  // Load token and user from storage on mount (check both localStorage and sessionStorage)
  useEffect(() => {
    let storedToken = localStorage.getItem(TOKEN_STORAGE_KEY)
    let storedUser = localStorage.getItem(USER_STORAGE_KEY)
    
    // If not in localStorage, check sessionStorage
    if (!storedToken) {
      storedToken = sessionStorage.getItem(TOKEN_STORAGE_KEY)
      storedUser = sessionStorage.getItem(USER_STORAGE_KEY)
    }
    
    if (storedToken && storedUser) {
      try {
        setToken(storedToken)
        setUser(JSON.parse(storedUser))
        // Also ensure it's in localStorage for apiFetch
        localStorage.setItem(TOKEN_STORAGE_KEY, storedToken)
      } catch (e) {
        // Invalid storage, clear it
        localStorage.removeItem(TOKEN_STORAGE_KEY)
        localStorage.removeItem(USER_STORAGE_KEY)
        sessionStorage.removeItem(TOKEN_STORAGE_KEY)
        sessionStorage.removeItem(USER_STORAGE_KEY)
      }
    }
    
    setLoading(false)
  }, [])

  // Verify token on mount if we have one
  useEffect(() => {
    if (token && config?.login_required) {
      verifyToken()
    }
  }, [token, config?.login_required])

  const verifyToken = async () => {
    if (!token) return
    
    try {
      const { apiFetch } = await import('../utils/apiClient')
      const response = await apiFetch('/api/v1/auth/me', {}, false)
      
      if (response.ok) {
        const data = await response.json()
        setUser({
          user_id: data.user_id,
          email: data.email,
          name: data.name,
          role: data.role
        })
      } else {
        // Token invalid, clear it
        logout()
      }
    } catch (error) {
      console.error('Token verification failed:', error)
      logout()
    }
  }

  const login = async (email: string, password: string, rememberMe: boolean = false) => {
    const { apiFetch } = await import('../utils/apiClient')
    const response = await apiFetch('/api/v1/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ email, password })
    }, false)

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Login failed' }))
      throw new Error(error.detail || 'Login failed')
    }

    const data = await response.json()
    
    // Store token and user
    // Use sessionStorage if rememberMe is false, localStorage if true
    const storage = rememberMe ? localStorage : sessionStorage
    storage.setItem(TOKEN_STORAGE_KEY, data.access_token)
    storage.setItem(USER_STORAGE_KEY, JSON.stringify({
      user_id: data.user_id,
      email: data.email,
      name: data.name,
      role: data.role
    }))
    
    // Also store in localStorage for apiFetch to find it
    localStorage.setItem(TOKEN_STORAGE_KEY, data.access_token)
    
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
      // Call logout endpoint if we have a token
      if (token) {
        const { apiFetch } = await import('../utils/apiClient')
        await apiFetch('/api/v1/auth/logout', {
          method: 'POST'
        }, false)
      }
    } catch (error) {
      console.error('Logout request failed:', error)
    } finally {
      // Always clear local state (both localStorage and sessionStorage)
      localStorage.removeItem(TOKEN_STORAGE_KEY)
      localStorage.removeItem(USER_STORAGE_KEY)
      sessionStorage.removeItem(TOKEN_STORAGE_KEY)
      sessionStorage.removeItem(USER_STORAGE_KEY)
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
