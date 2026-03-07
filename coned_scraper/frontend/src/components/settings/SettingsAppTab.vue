<template>
  <div class="ha-card">
    <div class="ha-card-header">
      <span class="ha-card-icon">⚙️</span>
      <span>App Settings</span>
    </div>
    <div class="ha-card-content">
      <div class="ha-section">
        <label class="ha-form-label">Your Local Time</label>
        <div class="ha-time-display">{{ currentTime || '--:--:--' }}</div>
        <div class="info-text">{{ Intl.DateTimeFormat().resolvedOptions().timeZone }}</div>
      </div>

      <div class="ha-section">
        <label class="ha-form-label">Database</label>
        <a
          :href="prismaUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="ha-prisma-btn"
        >
          Open Prisma Studio
        </a>
        <div class="ha-helper">Database browser UI (port 5555). Use when accessing HA from the same network.</div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { getApiBase } from '../../lib/api-base'

const currentTime = ref('')
const prismaUrl = ref('http://localhost:5555')

let timeInterval: ReturnType<typeof setInterval>
onMounted(async () => {
  try {
    const res = await fetch(`${getApiBase()}/prisma-url`)
    if (res.ok) {
      const data = await res.json()
      if (data?.url) prismaUrl.value = data.url
    }
  } catch {
    prismaUrl.value = `http://${window.location.hostname}:5555`
  }
  timeInterval = setInterval(() => {
    currentTime.value = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true })
  }, 1000)
})
onUnmounted(() => clearInterval(timeInterval))
</script>

<style scoped>
.ha-section { margin-top: 2rem; padding-top: 2rem; border-top: 1px solid #e0e0e0; }
.ha-section:first-child { margin-top: 0; padding-top: 0; border-top: none; }
.ha-time-display { padding: 0.75rem 1.25rem; background: #1a1a2e; border-radius: 8px; font-family: monospace; font-size: 1.5rem; font-weight: bold; color: #4ade80; min-width: 150px; text-align: center; margin: 0.5rem 0; }
.ha-section-title { font-size: 1.1rem; font-weight: 600; margin-bottom: 1rem; color: #333; }
.ha-prisma-btn {
  display: inline-block;
  padding: 0.5rem 1rem;
  background: #03a9f4;
  color: white;
  border-radius: 6px;
  text-decoration: none;
  font-weight: 500;
  margin-top: 0.5rem;
}
.ha-prisma-btn:hover { background: #0288d1; color: white; }
.ha-helper { font-size: 0.8rem; color: #666; margin-top: 0.25rem; }
</style>
