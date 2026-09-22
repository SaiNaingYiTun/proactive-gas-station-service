import { useEffect, useRef } from 'react'

// Re-runs `load` whenever the tab regains focus/visibility. Without this, a
// fetch that failed while the tab was backgrounded (backend blip, laptop
// sleep, wifi drop) leaves the page stuck on that error until the user does
// a full page refresh, even though the backend has long since recovered.
export function useRefetchOnFocus(load) {
  const loadRef = useRef(load)
  loadRef.current = load

  useEffect(() => {
    function onVisible() {
      if (document.visibilityState === 'visible') loadRef.current()
    }
    document.addEventListener('visibilitychange', onVisible)
    window.addEventListener('focus', onVisible)
    return () => {
      document.removeEventListener('visibilitychange', onVisible)
      window.removeEventListener('focus', onVisible)
    }
  }, [])
}
