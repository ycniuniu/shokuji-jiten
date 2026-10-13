import { useCallback, useEffect, useRef } from 'react'
import type { Mode } from '../types'

export function useSpeech(mode: Mode, voiceEnabled: boolean) {
  const ready = useRef(typeof window !== 'undefined' && 'speechSynthesis' in window)

  useEffect(() => {
    if (!ready.current) return
    // Warm voices list (Chrome loads async)
    window.speechSynthesis.getVoices()
  }, [])

  const speak = useCallback(
    (text: string) => {
      if (!ready.current || !voiceEnabled || !text) return
      window.speechSynthesis.cancel()
      const u = new SpeechSynthesisUtterance(text)
      u.lang = 'zh-CN'
      u.rate = 0.75
      u.volume = 1
      const voices = window.speechSynthesis.getVoices()
      const zh =
        voices.find((v) => v.lang === 'zh-CN') ||
        voices.find((v) => v.lang.startsWith('zh'))
      if (zh) u.voice = zh
      window.speechSynthesis.speak(u)
    },
    [voiceEnabled],
  )

  const stop = useCallback(() => {
    if (ready.current) window.speechSynthesis.cancel()
  }, [])

  // Elder mode: voice on by default is handled by parent; keep hook mode-aware for rate tweaks
  useEffect(() => {
    if (mode === 'elder' && voiceEnabled) {
      // no-op: parent sets voiceEnabled
    }
  }, [mode, voiceEnabled])

  return { speak, stop, supported: ready.current }
}
