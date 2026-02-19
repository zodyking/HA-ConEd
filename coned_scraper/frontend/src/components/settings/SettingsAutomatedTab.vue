<template>
  <div class="ha-card">
    <div class="ha-card-header">
      <span class="ha-card-icon">⏰</span>
      <span>Automated Scrape Schedule</span>
    </div>
    <div class="ha-card-content">
      <form @submit.prevent="handleSave">
        <div class="ha-form-group">
          <label class="ha-check-label">
            <input v-model="enabled" type="checkbox" />
            <span>Enable Automated Scraping</span>
          </label>
        </div>
        <template v-if="enabled">
          <div class="ha-form-group">
            <label class="ha-form-label">Scrape Frequency</label>
            <div class="ha-freq-row">
              <div class="ha-freq-col">
                <label for="hours" class="ha-form-label small">Hours</label>
                <input id="hours" v-model.number="hours" type="number" class="ha-form-input" min="0" max="23" />
              </div>
              <div class="ha-freq-col">
                <label for="minutes" class="ha-form-label small">Minutes</label>
                <input id="minutes" v-model.number="minutes" type="number" class="ha-form-input" min="0" max="59" />
              </div>
              <div class="ha-freq-col">
                <label for="seconds" class="ha-form-label small">Seconds</label>
                <input id="seconds" v-model.number="seconds" type="number" class="ha-form-input" min="0" max="59" />
              </div>
            </div>
            <div class="info-text">Scraper will run every {{ hours }}:{{ String(minutes).padStart(2, '0') }}:{{ String(seconds).padStart(2, '0') }}</div>
          </div>
        </template>
        <button type="submit" class="ha-button ha-button-primary" :disabled="isLoading">{{ isLoading ? 'Saving...' : 'Save Schedule' }}</button>
      </form>
      <div v-if="message" :class="['ha-message', message.type]">{{ message.text }}</div>
      <div v-if="status?.enabled && status?.nextRun" class="ha-status-box">
        Next run: {{ formatTZ(status.nextRun) }}
      </div>
      <div class="ha-history">
        <h4>Scrape History</h4>
        <div v-if="scrapeHistory.length === 0" class="ha-empty">No history yet</div>
        <div v-for="entry in scrapeHistory" :key="entry.id" class="ha-history-row">
          <span class="ha-history-time">{{ formattedTimestamps.get(entry.id) || entry.timestamp }}</span>
          <span :class="['ha-history-status', entry.success ? 'ok' : 'err']">{{ entry.success ? '✓' : '✗' }}</span>
          <span class="ha-history-duration">{{ formatDuration(entry.duration_seconds) }}</span>
          <span class="ha-history-detail">{{ entry.error_message || entry.failure_step || '' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { formatTimestamp as formatTZ } from '../../lib/timezone'
import { getApiBase } from '../../lib/api-base'

interface ScrapeHistoryEntry { id: number; timestamp: string; success: boolean; error_message?: string; failure_step?: string; duration_seconds?: number }
interface Status { enabled: boolean; frequency: number; nextRun?: string; isRunning?: boolean }

const enabled = ref(false)
const hours = ref(0)
const minutes = ref(0)
const seconds = ref(0)
const isLoading = ref(false)
const message = ref<{ type: 'success' | 'error'; text: string } | null>(null)
const status = ref<Status | null>(null)
const scrapeHistory = ref<ScrapeHistoryEntry[]>([])
const formattedTimestamps = ref<Map<number, string>>(new Map())

async function loadSchedule() {
  try {
    const res = await fetch(`${getApiBase()}/automated-schedule`)
    if (res.ok) {
      const data = await res.json()
      status.value = data
      if (data.enabled) {
        enabled.value = true
        const total = data.frequency || 0
        hours.value = Math.floor(total / 3600)
        minutes.value = Math.floor((total % 3600) / 60)
        seconds.value = total % 60
      }
    }
  } catch (e) {
    console.error(e)
  }
}

async function loadScrapeHistory() {
  try {
    const res = await fetch(`${getApiBase()}/scrape-history?limit=20`)
    if (res.ok) {
      const data = await res.json()
      scrapeHistory.value = data.history || []
    }
  } catch (e) {
    console.error(e)
  }
}

function formatDuration(sec?: number) {
  if (sec == null) return 'N/A'
  return `${sec.toFixed(1)}s`
}

async function handleSave() {
  isLoading.value = true
  message.value = null
  try {
    const totalSeconds = hours.value * 3600 + minutes.value * 60 + seconds.value
    if (totalSeconds <= 0) {
      message.value = { type: 'error', text: 'Frequency must be greater than 0' }
      isLoading.value = false
      return
    }
    const res = await fetch(`${getApiBase()}/automated-schedule`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: enabled.value, frequency: totalSeconds }),
    })
    if (res.ok) {
      message.value = { type: 'success', text: 'Automated scrape schedule saved successfully!' }
      await loadSchedule()
    } else {
      const err = await res.json().catch(() => ({}))
      message.value = { type: 'error', text: err.error || 'Failed to save schedule' }
    }
  } catch {
    message.value = { type: 'error', text: 'Failed to connect to API.' }
  } finally {
    isLoading.value = false
  }
}

watch(scrapeHistory, (hist) => {
  const m = new Map<number, string>()
  for (const e of hist) {
    try { m.set(e.id, formatTZ(e.timestamp)) } catch { m.set(e.id, e.timestamp) }
  }
  formattedTimestamps.value = m
}, { immediate: true })

let interval: ReturnType<typeof setInterval>
onMounted(() => { loadSchedule(); loadScrapeHistory(); interval = setInterval(loadScrapeHistory, 30000) })
onUnmounted(() => clearInterval(interval))
</script>

<style scoped>
.ha-check-label { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; }
.ha-check-label input { width: 18px; height: 18px; }
.ha-freq-row { display: flex; gap: 1rem; }
.ha-freq-col { flex: 1; }
.ha-form-label.small { font-size: 0.85rem; }
.ha-message { margin-top: 1rem; padding: 0.75rem; border-radius: 4px; }
.ha-message.success { background: #e8f5e9; color: #2e7d32; }
.ha-message.error { background: #ffebee; color: #c62828; }
.ha-status-box { margin-top: 1rem; padding: 0.75rem; background: #e3f2fd; border-radius: 6px; }
.ha-history { margin-top: 1.5rem; }
.ha-history h4 { font-size: 1rem; margin-bottom: 0.5rem; }
.ha-history-row { display: flex; gap: 0.5rem; padding: 0.4rem 0; border-bottom: 1px solid #eee; font-size: 0.8rem; }
.ha-history-time { color: #666; min-width: 160px; }
.ha-history-status.ok { color: #4caf50; }
.ha-history-status.err { color: #f44336; }
.ha-empty { color: #999; font-style: italic; padding: 0.5rem; }
</style>
