<template>
  <div class="ha-dashboard">
    <div v-if="apiError" class="ha-card ha-card-error">
      <div class="ha-card-header">
        <span class="ha-card-icon">⚠️</span>
        <strong>API Connection Error</strong>
      </div>
      <div class="ha-card-content">{{ apiError }}</div>
    </div>

    <div class="ha-card ha-card-status">
      <div class="ha-card-header">
        <span class="ha-card-icon">🔌</span>
        <span>Service Status</span>
      </div>
      <div class="ha-card-content ha-status-padding">
        <div class="ha-status-controls">
          <div class="ha-status-info">
            <span :class="['ha-status-indicator', status]"></span>
            <span class="ha-status-text">
              {{ status === 'running' ? 'Running' : status === 'error' ? 'Error' : 'Stopped' }}
            </span>
          </div>
          <button
            class="ha-button ha-button-primary"
            :disabled="isRunning"
            @click="handleStartScraper"
          >
            <img v-if="isRunning" :src="ajaxLoader" alt="Loading" class="ha-loader-inline" />
            {{ isRunning ? 'Running...' : 'Start Scraper' }}
          </button>
        </div>
      </div>
    </div>

    <div class="ha-panels-grid">
      <div class="ha-card ha-card-logs">
        <div class="ha-card-header">
          <span class="ha-card-icon">📝</span>
          <span>Console Logs</span>
        </div>
        <div ref="logContainerRef" class="ha-card-content ha-log-container">
          <div v-if="logs.length === 0" class="ha-empty-state">
            No logs yet. Start the scraper to see activity.
          </div>
          <div
            v-for="log in logs"
            :key="log.id"
            :class="['ha-log-entry', `ha-log-${log.level.toLowerCase()}`]"
          >
            <span class="ha-log-time">{{ formattedTimestamps.get(log.id) || log.timestamp }}</span>
            <span :class="getLogLevelClass(log.level)">[{{ log.level.toUpperCase() }}]</span>
            <span class="ha-log-message">{{ log.message }}</span>
          </div>
        </div>
      </div>

      <div class="ha-card ha-card-preview">
        <div class="ha-card-header">
          <span class="ha-card-icon">🖥️</span>
          <span>Browser Preview</span>
        </div>
        <div class="ha-card-content ha-preview-container">
          <img
            v-if="previewUrl"
            :src="previewUrl"
            alt="Browser preview"
            class="ha-preview-img"
          />
          <div v-else class="ha-empty-state ha-preview-empty">
            <img
              v-if="isRunning"
              :src="ajaxLoader"
              alt="Loading"
              class="ha-preview-loader"
            />
            <div>{{ isRunning ? 'Waiting for browser preview...' : 'No preview available. Start the scraper to see browser activity.' }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { formatTimestamp } from '../lib/timezone'
import { getApiBase } from '../lib/api-base'
import { ajaxLoader } from '../lib/assets'

interface LogEntry {
  id: number
  timestamp: string
  level: string
  message: string
}

const isRunning = ref(false)
const logs = ref<LogEntry[]>([])
const status = ref<'stopped' | 'running' | 'error'>('stopped')
const logContainerRef = ref<HTMLDivElement | null>(null)
const apiError = ref<string | null>(null)
const previewUrl = ref<string | null>(null)
const formattedTimestamps = ref<Map<number, string>>(new Map())

async function loadLogs() {
  try {
    const response = await fetch(`${getApiBase()}/logs?limit=100`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    })
    if (response?.ok) {
      const data = await response.json()
      logs.value = (data.logs || []).reverse()
    }
  } catch {
    // Keep existing logs
  }
}

async function loadLivePreview() {
  try {
    const timestamp = Date.now()
    const url = `${getApiBase()}/live-preview?t=${timestamp}`
    const response = await fetch(url)
    if (response.ok && response.headers.get('content-type')?.startsWith('image/')) {
      const blob = await response.blob()
      const imageUrl = URL.createObjectURL(blob)
      if (previewUrl.value?.startsWith('blob:')) {
        URL.revokeObjectURL(previewUrl.value)
      }
      previewUrl.value = imageUrl
    } else {
      if (previewUrl.value?.startsWith('blob:')) {
        URL.revokeObjectURL(previewUrl.value)
      }
      previewUrl.value = null
    }
  } catch {
    if (previewUrl.value?.startsWith('blob:')) {
      URL.revokeObjectURL(previewUrl.value)
    }
    previewUrl.value = null
  }
}

function getLogLevelClass(level: string) {
  switch (level.toLowerCase()) {
    case 'error':
      return 'log-level-error'
    case 'success':
      return 'log-level-success'
    case 'warning':
      return 'log-level-warning'
    default:
      return 'log-level-info'
  }
}

async function handleStartScraper() {
  isRunning.value = true
  status.value = 'running'
  logs.value = []
  apiError.value = null

  try {
    await fetch(`${getApiBase()}/logs`, { method: 'DELETE' }).catch(() => {})
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 30000)
    const response = await fetch(`${getApiBase()}/scrape`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
    }).catch(() => null)
    clearTimeout(timeoutId)

    if (response?.ok) {
      const result = await response.json()
      status.value = result.success ? 'stopped' : 'error'
      setTimeout(loadLogs, 1000)
    } else if (response) {
      let errorMessage = 'Unknown error occurred'
      try {
        const errorData = await response.json()
        errorMessage = errorData.detail || errorData.error || errorData.message || errorMessage
      } catch {
        try {
          errorMessage = (await response.text()) || `HTTP ${response.status}: ${response.statusText}`
        } catch {
          errorMessage = `HTTP ${response.status}: ${response.statusText}`
        }
      }
      status.value = 'error'
      apiError.value = `Scraper error: ${errorMessage}`
    } else {
      status.value = 'error'
      apiError.value = "Cannot connect to Python service. Make sure it's running on port 8000."
    }
  } catch {
    status.value = 'error'
    apiError.value = 'Failed to start scraper. Check console for details.'
  } finally {
    isRunning.value = false
  }
}

watch(logs, () => {
  const newMap = new Map<number, string>()
  for (const log of logs.value) {
    try {
      newMap.set(log.id, formatTimestamp(log.timestamp))
    } catch {
      newMap.set(log.id, log.timestamp)
    }
  }
  formattedTimestamps.value = newMap
}, { immediate: true })

watch(logs, () => {
  if (logContainerRef.value) {
    logContainerRef.value.scrollTop = logContainerRef.value.scrollHeight
  }
})

let logInterval: ReturnType<typeof setInterval>
let previewInterval: ReturnType<typeof setInterval>

onMounted(() => {
  loadLogs()
  loadLivePreview()
  logInterval = setInterval(loadLogs, 1000)
  previewInterval = setInterval(loadLivePreview, isRunning.value ? 500 : 2000)
})

onUnmounted(() => {
  clearInterval(logInterval)
  clearInterval(previewInterval)
  if (previewUrl.value?.startsWith('blob:')) {
    URL.revokeObjectURL(previewUrl.value)
  }
})
</script>

<style scoped>
.ha-status-padding {
  padding: 0.5rem 0.75rem !important;
}
.ha-preview-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border: 1px solid #333;
  border-radius: 4px;
}
.ha-preview-empty {
  text-align: center;
  color: #888;
}
.ha-preview-loader {
  width: 40px;
  height: 40px;
  margin-bottom: 1rem;
}
</style>
