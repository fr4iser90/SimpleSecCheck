import { useCallback, useEffect, useRef, useState } from 'react'

interface UseAutoRefreshOptions {
  intervalMs?: number
  enabledDefault?: boolean
  runOnMount?: boolean
}

export function useAutoRefresh(
  onRefresh: (opts: { silent: boolean }) => void | Promise<void>,
  { intervalMs = 5000, enabledDefault = true, runOnMount = true }: UseAutoRefreshOptions = {}
) {
  const onRefreshRef = useRef(onRefresh)
  onRefreshRef.current = onRefresh

  const [autoRefresh, setAutoRefresh] = useState(enabledDefault)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [initialLoad, setInitialLoad] = useState(runOnMount)

  const refresh = useCallback(async (silent = false) => {
    if (!silent) setIsRefreshing(true)
    try {
      await onRefreshRef.current({ silent })
      setLastUpdated(new Date())
    } finally {
      setIsRefreshing(false)
      setInitialLoad(false)
    }
  }, [])

  useEffect(() => {
    if (!runOnMount) return
    void refresh(false)
  }, [runOnMount, refresh])

  useEffect(() => {
    if (!autoRefresh) return
    const id = window.setInterval(() => void refresh(true), intervalMs)
    return () => window.clearInterval(id)
  }, [autoRefresh, intervalMs, refresh])

  return {
    autoRefresh,
    setAutoRefresh,
    refresh: () => refresh(false),
    isRefreshing,
    initialLoad,
    lastUpdated,
    intervalMs,
  }
}
