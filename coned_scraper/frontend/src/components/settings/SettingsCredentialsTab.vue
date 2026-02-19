<template>
  <div class="ha-card">
    <div class="ha-card-header">
      <span class="ha-card-icon">🔐</span>
      <span>Credentials</span>
    </div>
    <div class="ha-card-content">
      <form @submit.prevent="handleSave">
        <div class="ha-form-group">
          <label for="username" class="ha-form-label">Username / Email</label>
          <div class="password-input-wrapper">
            <input
              id="username"
              :value="showUsername ? username : (username ? maskText(username) : '')"
              class="ha-form-input"
              :type="showUsername ? 'text' : 'password'"
              autocomplete="off"
              required
              @focus="showUsername = true"
              @blur="showUsername = false"
              @input="username = ($event.target as HTMLInputElement).value"
            />
          </div>
        </div>
        <div class="ha-form-group">
          <label for="password" class="ha-form-label">
            Password
            <span class="ha-form-hint">(leave empty to keep existing)</span>
          </label>
          <div class="password-input-wrapper">
            <input
              id="password"
              v-model="password"
              class="ha-form-input"
              :type="showPassword ? 'text' : 'password'"
              autocomplete="new-password"
              @focus="showPassword = true"
              @blur="showPassword = false"
            />
          </div>
        </div>
        <div class="ha-form-group">
          <label for="totp-secret" class="ha-form-label">TOTP Secret</label>
          <div class="password-input-wrapper">
            <input
              id="totp-secret"
              :value="totpSecret"
              class="ha-form-input ha-totp-input"
              :type="showTotpSecret ? 'text' : 'password'"
              autocomplete="off"
              required
              @focus="showTotpSecret = true"
              @blur="showTotpSecret = false"
              @input="totpSecret = ($event.target as HTMLInputElement).value.trim().toUpperCase()"
            />
          </div>
          <div class="info-text">Your 2FA secret key (usually 16-32 characters)</div>
        </div>
        <button type="submit" class="ha-button ha-button-primary" :disabled="isLoading">
          {{ isLoading ? 'Saving...' : 'Save Credentials' }}
        </button>
      </form>

      <div v-if="currentTOTP && !['Connection Error', 'No credentials saved'].includes(currentTOTP)" class="ha-totp-card">
        <div class="ha-totp-row">
          <div>
            <div class="ha-totp-label">Current TOTP Code</div>
            <div class="ha-totp-code">{{ currentTOTP }}</div>
          </div>
          <div class="ha-totp-time-box">
            <div class="ha-totp-label">Time Remaining</div>
            <div :class="['ha-totp-time', { low: timeRemaining < 10 }]">{{ timeRemaining }}s</div>
          </div>
        </div>
      </div>

      <div v-if="message" :class="['ha-message', message.type]">{{ message.text }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { getApiBase } from '../../lib/api-base'

interface Message {
  type: 'success' | 'error'
  text: string
}

interface TOTPResponse {
  code: string
  time_remaining: number
}

const username = ref('')
const password = ref('')
const totpSecret = ref('')
const showUsername = ref(false)
const showPassword = ref(false)
const showTotpSecret = ref(false)
const currentTOTP = ref('')
const timeRemaining = ref(30)
const isLoading = ref(false)
const message = ref<Message | null>(null)

function maskText(text: string) {
  return text ? '•'.repeat(text.length) : ''
}

async function loadSettings() {
  try {
    const res = await fetch(`${getApiBase()}/settings`)
    if (res.ok) {
      const data = await res.json()
      username.value = data.username || ''
      password.value = ''
      totpSecret.value = data.totp_secret || ''
      showUsername.value = false
      showPassword.value = false
      showTotpSecret.value = false
    }
  } catch (e) {
    console.error(e)
    message.value = { type: 'error', text: 'Failed to connect to API. Make sure the Python service is running.' }
  }
}

async function handleSave() {
  isLoading.value = true
  message.value = null
  try {
    const res = await fetch(`${getApiBase()}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: username.value,
        password: password.value || null,
        totp_secret: totpSecret.value,
      }),
    })
    if (res.ok) {
      message.value = { type: 'success', text: 'Settings saved successfully!' }
      if (totpSecret.value) {
        const totpRes = await fetch(`${getApiBase()}/totp`)
        if (totpRes.ok) {
          const totpData: TOTPResponse = await totpRes.json()
          currentTOTP.value = totpData.code
          timeRemaining.value = totpData.time_remaining
        }
      }
    } else {
      const err = await res.json()
      message.value = { type: 'error', text: err.detail || 'Failed to save settings' }
    }
  } catch (e) {
    message.value = { type: 'error', text: 'Failed to connect to API. Make sure the Python service is running.' }
  } finally {
    isLoading.value = false
  }
}

watch(totpSecret, (val) => {
  if (!val?.trim()) {
    currentTOTP.value = ''
    timeRemaining.value = 30
  }
})

let totpInterval: ReturnType<typeof setInterval>
onMounted(() => {
  loadSettings()
  totpInterval = setInterval(async () => {
    if (!totpSecret.value?.trim()) return
    try {
      const res = await fetch(`${getApiBase()}/totp`)
      if (res.ok) {
        const data: TOTPResponse = await res.json()
        currentTOTP.value = data.code
        timeRemaining.value = data.time_remaining
      } else {
        const err = await res.json().catch(() => ({}))
        if (res.status === 404) currentTOTP.value = 'No credentials saved'
        else if (res.status === 400) currentTOTP.value = err.detail || 'Invalid TOTP secret'
        else currentTOTP.value = err.detail || 'Failed to fetch TOTP'
      }
    } catch {
      currentTOTP.value = 'Connection Error'
    }
  }, 1000)
})
onUnmounted(() => clearInterval(totpInterval))

defineExpose({ loadSettings })
</script>

<style scoped>
.ha-form-hint { font-size: 0.85rem; font-weight: normal; margin-left: 0.5rem; color: #666; }
.ha-totp-input { font-family: monospace; letter-spacing: 0.1em; }
.ha-totp-card {
  margin-top: 1.5rem;
  padding: 1rem;
  background: #f5f5f5;
  border-radius: 6px;
}
.ha-totp-row { display: flex; justify-content: space-between; align-items: center; }
.ha-totp-label { font-size: 0.85rem; color: #666; margin-bottom: 0.25rem; }
.ha-totp-code { font-size: 1.5rem; font-weight: bold; font-family: monospace; letter-spacing: 0.15em; }
.ha-totp-time-box { text-align: right; }
.ha-totp-time { font-size: 1.5rem; font-weight: bold; color: #4caf50; }
.ha-totp-time.low { color: #d32f2f; }
.ha-message { margin-top: 1rem; padding: 0.75rem; border-radius: 4px; }
.ha-message.success { background: #e8f5e9; color: #2e7d32; }
.ha-message.error { background: #ffebee; color: #c62828; }
</style>
