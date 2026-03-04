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

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const currentTime = ref('')

let timeInterval: ReturnType<typeof setInterval>
onMounted(() => {
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
</style>
