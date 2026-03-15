import { useEffect, useRef, useCallback } from 'react'

interface UseAutoScrollOptions {
  trigger: any // Value that triggers scroll when changed
  enabled?: boolean
  delay?: number
  offset?: number
}

export function useAutoScroll({
  trigger,
  enabled = true,
  delay = 300,
  offset = 30
}: UseAutoScrollOptions) {
  const prevTriggerRef = useRef<any>(trigger)
  const elementRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (!enabled || !trigger || !elementRef.current) return
    
    // Only scroll if trigger actually changed
    if (trigger !== prevTriggerRef.current && trigger) {
      const timeoutId = setTimeout(() => {
        if (elementRef.current) {
          const element = elementRef.current
          const elementPosition = element.getBoundingClientRect().top + window.pageYOffset
          const offsetPosition = elementPosition - offset

          window.scrollTo({
            top: offsetPosition,
            behavior: 'smooth'
          })
        }
      }, delay)

      prevTriggerRef.current = trigger
      return () => clearTimeout(timeoutId)
    } else {
      prevTriggerRef.current = trigger
    }
  }, [trigger, enabled, delay, offset])

  // Return a ref callback
  const setRef = useCallback((element: HTMLElement | null) => {
    elementRef.current = element
  }, [])

  return setRef
}
