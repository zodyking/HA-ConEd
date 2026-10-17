import { onUnmounted, ref } from 'vue'

export type RefreshPhase = 'idle' | 'updating' | 'updated' | 'error'

const UPDATED_HOLD_MS = 2500

export function useRefreshStatus() {
  const phase = ref<RefreshPhase>('idle')
  const message = ref('')
  let timer: ReturnType<typeof setTimeout> | null = null

  function clearTimer() {
    if (timer !== null) {
      clearTimeout(timer)
      timer = null
    }
  }

  function setUpdating(text: string) {
    clearTimer()
    phase.value = 'updating'
    message.value = text
  }

  function setUpdated(text: string) {
    clearTimer()
    phase.value = 'updated'
    message.value = text
    timer = setTimeout(() => {
      phase.value = 'idle'
      message.value = ''
      timer = null
    }, UPDATED_HOLD_MS)
  }

  function setError(text: string) {
    clearTimer()
    phase.value = 'error'
    message.value = text
  }

  function reset() {
    clearTimer()
    phase.value = 'idle'
    message.value = ''
  }

  onUnmounted(clearTimer)

  return { phase, message, setUpdating, setUpdated, setError, reset }
}
