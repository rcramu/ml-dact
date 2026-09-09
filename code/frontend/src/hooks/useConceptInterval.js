import { useEffect, useRef } from 'react'

/** setInterval that cleans up automatically and restarts when deps change. */
export function useConceptInterval(callback, delay, deps = []) {
  const savedCallback = useRef(callback)
  useEffect(() => { savedCallback.current = callback }, [callback])

  useEffect(() => {
    if (delay == null) return undefined
    const id = setInterval(() => savedCallback.current(), delay)
    return () => clearInterval(id)
  }, [delay, ...deps])
}
