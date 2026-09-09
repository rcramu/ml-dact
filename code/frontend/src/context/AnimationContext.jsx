import { createContext, useContext, useMemo, useState } from 'react'

const AnimationContext = createContext({ paused: false, setPaused: () => {} })

export function AnimationProvider({ children }) {
  const [paused, setPaused] = useState(false)
  const value = useMemo(() => ({ paused, setPaused }), [paused])
  return <AnimationContext.Provider value={value}>{children}</AnimationContext.Provider>
}

export function useAnimationControl() {
  return useContext(AnimationContext)
}
