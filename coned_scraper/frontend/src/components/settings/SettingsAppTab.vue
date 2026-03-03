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

      <form @submit.prevent="handleSave" class="ha-section">
        <h4 class="ha-section-title">Change Settings Password</h4>
        <div class="ha-form-group">
          <label for="new-pwd" class="ha-form-label">New Password</label>
          <input id="new-pwd" v-model="newPassword" type="password" class="ha-form-input" placeholder="Leave empty to keep current" autocomplete="new-password" />
          <div class="info-text">Minimum 4 characters</div>
        </div>
        <div v-if="newPassword" class="ha-form-group">
          <label for="confirm-pwd" class="ha-form-label">Confirm New Password</label>
          <input id="confirm-pwd" v-model="confirmPassword" type="password" class="ha-form-input" placeholder="Re-enter" autocomplete="new-password" />
        </div>
        <button type="submit" class="ha-button ha-button-primary" :disabled="isLoading">{{ isLoading ? 'Saving...' : 'Change Password' }}</button>
      </form>
      <div v-if="message" :class="['ha-message', message.type]">{{ message.text }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { getApiBase } from '../../lib/api-base'

const currentTime = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const isLoading = ref(false)
const message = ref<{ type: 'success' | 'error'; text: string } | null>(null)

async function handleSave() {
  if (newPassword.value && newPassword.value !== confirmPassword.value) {
    message.value = { type: 'error', text: 'Passwords do not match' }
    return
  }
  if (newPassword.value && newPassword.value.length < 4) {
    message.value = { type: 'error', text: 'Password must be at least 4 characters' }
    return
  }
  isLoading.value = true
  message.value = null
  try {
    const cur = await fetch(`${getApiBase()}/app-settings`).then((r) => r.json())
    const res = await fetch(`${getApiBase()}/app-settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ time_offset_hours: cur.time_offset_hours || 0, settings_password: newPassword.value || cur.settings_password || '0000' }),
    })
    if (res.ok) {
      const didChange = !!newPassword.value
      message.value = { type: 'success', text: 'Password changed!' }
      newPassword.value = ''
      confirmPassword.value = ''
      if (didChange) setTimeout(() => window.location.reload(), 2000)
    } else {
      const err = await res.json().catch(() => ({}))
      message.value = { type: 'error', text: err.detail || 'Failed' }
    }
  } catch {
    message.value = { type: 'error', text: 'Failed to connect' }
  } finally {
    isLoading.value = false
  }
}


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
.ha-message { margin-top: 0.75rem; padding: 0.75rem; border-radius: 4px; }
.ha-message.success { background: #e8f5e9; color: #2e7d32; }
.ha-message.error { background: #ffebee; color: #c62828; }
</style>
