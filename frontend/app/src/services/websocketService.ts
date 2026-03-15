import { useEffect, useRef, useState } from 'react'

interface WebSocketMessage {
  type: string
  steps?: any[]
  progress_percentage?: number
  status?: string
  scan_id?: string
  results_dir?: string
  error?: string
}

interface WebSocketCallbacks {
  onMessage?: (data: WebSocketMessage) => void
  onError?: (error: Event) => void
  onOpen?: () => void
  onClose?: () => void
}

export class WebSocketService {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private reconnectTimer: number | null = null
  private heartbeatTimer: number | null = null
  private callbacks: WebSocketCallbacks = {}
  private isConnecting = false

  connect(scanId: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.isConnecting || this.ws?.readyState === WebSocket.OPEN) {
        resolve()
        return
      }

      this.isConnecting = true

      try {
        // Convert HTTP to WebSocket URL
        const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/scans/${scanId}/stream`
        this.ws = new WebSocket(wsUrl)

        this.ws.onopen = () => {
          console.log('[WebSocketService] WebSocket connected')
          this.reconnectAttempts = 0
          this.isConnecting = false
          
          // Send ping every 25 seconds to keep connection alive
          this.heartbeatTimer = window.setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
              this.ws.send('ping')
            }
          }, 25000)

          this.callbacks.onOpen?.()
          resolve()
        }

        this.ws.onmessage = (e) => {
          try {
            const data = JSON.parse(e.data) as WebSocketMessage
            
            if (data.error) {
              console.error('[WebSocketService] WebSocket error:', data.error)
              return
            }

            this.callbacks.onMessage?.(data)
          } catch (error) {
            console.error('[WebSocketService] Failed to parse WebSocket data:', error)
          }
        }

        this.ws.onerror = (error) => {
          console.error('[WebSocketService] WebSocket error:', error)
          this.callbacks.onError?.(error)
          reject(error)
        }

        this.ws.onclose = () => {
          console.log('[WebSocketService] WebSocket closed')
          this.isConnecting = false
          
          // Clear heartbeat
          if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer)
            this.heartbeatTimer = null
          }

          this.callbacks.onClose?.()

          // Auto-reconnect if not manually closed and within max attempts
          if (this.reconnectAttempts < 10) {
            this.reconnectAttempts++
            console.log(`[WebSocketService] Reconnecting in 3000ms (attempt ${this.reconnectAttempts}/10)`)
            this.reconnectTimer = window.setTimeout(() => {
              this.connect(scanId).catch(console.error)
            }, 3000)
          } else {
            console.error('[WebSocketService] Max reconnection attempts reached')
          }
        }
      } catch (error) {
        console.error('[WebSocketService] WebSocket connection error:', error)
        this.isConnecting = false
        reject(error)
      }
    })
  }

  disconnect(): void {
    // Clear reconnect timer
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    // Clear heartbeat timer
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }

    // Close WebSocket connection
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    this.isConnecting = false
    this.reconnectAttempts = 0
  }

  onMessage(callback: (data: WebSocketMessage) => void): void {
    this.callbacks.onMessage = callback
  }

  onError(callback: (error: Event) => void): void {
    this.callbacks.onError = callback
  }

  onOpen(callback: () => void): void {
    this.callbacks.onOpen = callback
  }

  onClose(callback: () => void): void {
    this.callbacks.onClose = callback
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  getReconnectAttempts(): number {
    return this.reconnectAttempts
  }

  sendMessage(message: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(message)
    }
  }
}

// React Hook for WebSocket usage
export function useWebSocket(scanId: string | null) {
  const wsService = useRef<WebSocketService | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [reconnectAttempts, setReconnectAttempts] = useState(0)

  useEffect(() => {
    if (!scanId) {
      if (wsService.current) {
        wsService.current.disconnect()
        wsService.current = null
      }
      setIsConnected(false)
      setReconnectAttempts(0)
      return
    }

    if (!wsService.current) {
      wsService.current = new WebSocketService()
    }

    const service = wsService.current

    // Set up callbacks
    service.onOpen(() => {
      setIsConnected(true)
      setReconnectAttempts(0)
    })

    service.onClose(() => {
      setIsConnected(false)
      setReconnectAttempts(service.getReconnectAttempts())
    })

    // Connect
    service.connect(scanId).catch(console.error)

    return () => {
      // Cleanup is handled by the service itself when scanId changes
    }
  }, [scanId])

  const sendMessage = (message: string) => {
    if (wsService.current?.isConnected()) {
      wsService.current.sendMessage(message)
    }
  }

  return {
    isConnected,
    reconnectAttempts,
    sendMessage,
    service: wsService.current
  }
}
