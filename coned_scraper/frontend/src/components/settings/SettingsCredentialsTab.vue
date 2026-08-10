<template>
  <div class="ha-credentials-page">
    <!-- Credentials Card -->
    <div class="ha-card">
      <div class="ha-card-header">
        <span class="ha-card-icon">🔐</span>
        <span>Con Edison Credentials</span>
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
            <div class="info-text">
              Your 2FA secret key (usually 16-32 characters). In ConEd settings, set up Google Authenticator and click "Can't scan?" to get the secret key.
            </div>
          </div>
          
          <div class="ha-form-actions">
            <button type="submit" class="ha-button ha-button-primary" :disabled="isLoading">
              {{ isLoading ? 'Saving...' : 'Save Credentials' }}
            </button>
            <button type="button" class="ha-button" :disabled="isLoading" @click="testCredentials">
              Test Credentials
            </button>
          </div>
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

    <!-- Meter Tracking Card -->
    <div class="ha-card">
      <div class="ha-card-header">
        <span class="ha-card-icon">⚡</span>
        <span>Meter Tracking</span>
      </div>
      <div class="ha-card-content">
        <div class="info-text" style="margin-bottom: 1rem">
          Enable real-time meter readings using the 
          <a href="https://github.com/tronikos/opower" target="_blank" rel="noopener">opower</a> library. 
          Uses the same credentials as above. Creates MQTT sensors for current usage (kWh) and calculated cost.
        </div>
        
        <div class="ha-form-group">
          <label class="ha-check-label">
            <input v-model="meterConfig.enabled" type="checkbox" @change="onMeterToggle" />
            <span>Enable Meter Tracking</span>
          </label>
        </div>

        <template v-if="meterConfig.enabled">
          <div class="ha-form-group">
            <label for="meter-account" class="ha-form-label">Electric Account</label>
            <div class="ha-account-picker-row">
              <select
                id="meter-account"
                v-model="meterConfig.selected_account_id"
                class="ha-form-input"
                :disabled="meterAccounts.length === 0 || meterLoading"
                @change="onMeterAccountChange"
              >
                <option value="">Use the first electric account (legacy default)</option>
                <option v-for="account in meterAccounts" :key="account.id" :value="account.id">
                  {{ formatAccountLabel(account) }}
                </option>
              </select>
              <button type="button" class="ha-button" :disabled="meterLoading" @click="discoverMeterAccounts()">
                Find Accounts
              </button>
            </div>
            <div class="info-text">
              Choose the service address used for both Opower meter readings and browser-scraped bills and balance.
            </div>
          </div>

          <div class="ha-form-group">
            <label class="ha-form-label">Polling Interval (minutes)</label>
            <input v-model.number="meterConfig.polling_interval" type="number" min="15" max="60" class="ha-form-input ha-input-small" />
            <div class="info-text">Cannot be less than data update interval (quarter-hour = 15 min minimum)</div>
          </div>

          <div class="ha-form-actions">
            <button type="button" class="ha-button ha-button-primary" :disabled="meterLoading" @click="saveMeterConfig">
              {{ meterLoading ? 'Saving...' : 'Save Meter Settings' }}
            </button>
            <button type="button" class="ha-button" :disabled="meterLoading" @click="testMeterConnection">
              Test Connection
            </button>
            <button type="button" class="ha-button" :disabled="meterLoading" @click="refreshReading">
              Refresh Reading
            </button>
          </div>

          <div v-if="meterMessage" :class="['ha-message', meterMessage.type]">{{ meterMessage.text }}</div>

          <!-- Latest Reading Info -->
          <div v-if="lastReading" class="ha-reading-info">
            <div class="ha-reading-header">Latest Reading (Hourly Data)</div>
            <div class="ha-reading-row">
              <span class="ha-reading-label">Usage:</span>
              <span class="ha-reading-value">{{ lastReading.value?.toFixed(3) }} {{ lastReading.unit }}</span>
            </div>
            <div v-if="lastReadingCost !== null" class="ha-reading-row">
              <span class="ha-reading-label">Estimated Cost:</span>
              <span class="ha-reading-value">${{ lastReadingCost.toFixed(2) }}</span>
            </div>
            <div class="ha-reading-row">
              <span class="ha-reading-label">Data From:</span>
              <span class="ha-reading-value ha-reading-time">{{ formatTime(lastReading.end_time) }}</span>
            </div>
            <div class="ha-reading-row">
              <span class="ha-reading-label">Fetched:</span>
              <span class="ha-reading-value ha-reading-time">{{ formatTime(lastReading.fetched_at) }}</span>
            </div>
          </div>

          <!-- Account Info -->
          <div v-if="accountInfo" class="ha-reading-info">
            <div class="ha-reading-header">Account Info</div>
            <div class="ha-reading-row">
              <span class="ha-reading-label">Account ID:</span>
              <span class="ha-reading-value">{{ accountInfo.utility_account_id }}</span>
            </div>
            <div v-if="accountInfo.address" class="ha-reading-row">
              <span class="ha-reading-label">Service Address:</span>
              <span class="ha-reading-value">{{ accountInfo.address }}</span>
            </div>
            <div class="ha-reading-row">
              <span class="ha-reading-label">Meter Type:</span>
              <span class="ha-reading-value">{{ accountInfo.meter_type }}</span>
            </div>
            <div class="ha-reading-row">
              <span class="ha-reading-label">Resolution:</span>
              <span class="ha-reading-value">{{ accountInfo.read_resolution }}</span>
            </div>
            <div class="ha-reading-row">
              <span class="ha-reading-label">Realtime Access:</span>
              <span class="ha-reading-value" :style="{ color: accountInfo.has_realtime_access ? '#4caf50' : '#ff9800' }">
                {{ accountInfo.has_realtime_access ? 'Yes' : 'No (using hourly data)' }}
              </span>
            </div>
          </div>

          <!-- Forecast Info -->
          <div v-if="forecast" class="ha-reading-info">
            <div class="ha-reading-header">Current Period Forecast</div>
            <div class="ha-reading-row">
              <span class="ha-reading-label">Period:</span>
              <span class="ha-reading-value">{{ forecast.start_date }} to {{ forecast.end_date }}</span>
            </div>
            <div class="ha-reading-row">
              <span class="ha-reading-label">Usage to Date:</span>
              <span class="ha-reading-value">{{ forecast.usage_to_date }} {{ forecast.unit }}</span>
            </div>
            <div class="ha-reading-row">
              <span class="ha-reading-label">Forecasted Usage:</span>
              <span class="ha-reading-value">{{ forecast.forecasted_usage }} {{ forecast.unit }}</span>
            </div>
          </div>

          <!-- Smart Meter Info Box -->
          <div class="info-box">
            <strong>About Smart Meters:</strong> Real-time data requires enrollment in Con Edison's 
            smart meter program with real-time data sharing enabled. This addon uses hourly historical 
            data from Opower (typically 1-24 hour delay) which is available to all smart meter customers.
          </div>

          <!-- MQTT Sensors Info -->
          <div class="mqtt-sensor-info">
            <div class="mqtt-sensor-header">MQTT Sensors Created</div>
            <ul class="mqtt-sensor-list">
              <li><code>sensor.ConEd_current_usage_cost</code> — Calculated cost (USD)</li>
              <li><code>sensor.ConEd_billing_start_date</code> — Billing period start date</li>
              <li><code>sensor.ConEd_billing_end_date</code> — Billing period end date</li>
              <li><code>sensor.ConEd_current_cycle_usage</code> — kWh used so far this billing cycle</li>
              <li><code>sensor.ConEd_forecasted_usage</code> — Projected kWh for full billing period</li>
              <li><code>sensor.ConEd_last_bill_kwh</code> — kWh from your most recent bill statement</li>
            </ul>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted, onUnmounted } from 'vue'
import { getApiBase } from '../../lib/api-base'

interface Message {
  type: 'success' | 'error'
  text: string
}

interface TOTPResponse {
  code: string
  time_remaining: number
}

interface MeterReading {
  start_time: string | null
  end_time: string | null
  value: number | null
  unit: string
  fetched_at: string
}

interface MeterAccount {
  id: string
  uuid: string
  utility_account_id: string
  meter_type: string
  read_resolution: string
  customer_uuid: string
  account_name: string
  account_type: string
  account_number: string
  address: string
}

// Credentials state
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

// Meter tracking state
const meterConfig = reactive({
  enabled: false,
  polling_interval: 15,
  selected_account_id: '',
  selected_account_address: ''
})
const meterAccounts = ref<MeterAccount[]>([])
const meterLoading = ref(false)
const meterMessage = ref<Message | null>(null)
const lastReading = ref<MeterReading | null>(null)
const lastReadingCost = ref<number | null>(null)
const accountInfo = ref<any>(null)
const forecast = ref<any>(null)

function maskText(text: string) {
  return text ? '•'.repeat(text.length) : ''
}

function formatTime(isoString: string | null): string {
  if (!isoString) return '—'
  try {
    const date = new Date(isoString)
    return date.toLocaleString()
  } catch {
    return isoString
  }
}

function formatAccountLabel(account: MeterAccount): string {
  const identity = account.address || account.account_name || 'Con Edison account'
  const details = [account.account_type, account.account_number, account.meter_type].filter(Boolean)
  return details.length ? `${identity} — ${details.join(' · ')}` : identity
}

function onMeterAccountChange() {
  const selected = meterAccounts.value.find(account => account.id === meterConfig.selected_account_id)
  meterConfig.selected_account_address = selected?.address || ''
}

// Load credentials
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

// Save credentials (also updates meter config with same credentials)
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
      message.value = { type: 'success', text: 'Credentials saved successfully!' }
      if (totpSecret.value) {
        const totpRes = await fetch(`${getApiBase()}/totp`)
        if (totpRes.ok) {
          const totpData: TOTPResponse = await totpRes.json()
          currentTOTP.value = totpData.code
          timeRemaining.value = totpData.time_remaining
        }
      }
      // Also sync credentials to meter config if meter tracking is enabled
      if (meterConfig.enabled) {
        await syncMeterCredentials()
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

// Test credentials
async function testCredentials() {
  isLoading.value = true
  message.value = null
  try {
    const res = await fetch(`${getApiBase()}/test-login`, { method: 'POST' })
    const data = await res.json()
    if (res.ok && data.success) {
      message.value = { type: 'success', text: data.message || 'Login successful!' }
    } else {
      message.value = { type: 'error', text: data.detail || data.message || 'Login test failed' }
    }
  } catch {
    message.value = { type: 'error', text: 'Failed to connect to API' }
  } finally {
    isLoading.value = false
  }
}

// Load meter config
async function loadMeterConfig() {
  try {
    const res = await fetch(`${getApiBase()}/meter-config`)
    if (res.ok) {
      const d = await res.json()
      meterConfig.enabled = d.enabled || false
      meterConfig.polling_interval = Math.max(15, d.polling_interval ?? 15)
      meterConfig.selected_account_id = d.selected_account_id || ''
      meterConfig.selected_account_address = d.selected_account_address || ''
      if (meterConfig.enabled) {
        await discoverMeterAccounts(false)
      }
    }
  } catch (e) {
    console.error('Failed to load meter config:', e)
  }
}

// Load meter reading
async function loadMeterReading() {
  try {
    const res = await fetch(`${getApiBase()}/meter-reading`)
    if (res.ok) {
      const d = await res.json()
      if (d.reading) {
        lastReading.value = d.reading
        lastReadingCost.value = d.cost ?? null
      }
      if (d.forecast) {
        forecast.value = d.forecast
      }
    }
  } catch (e) {
    console.error('Failed to load meter reading:', e)
  }
}

// Sync credentials to meter config
async function syncMeterCredentials() {
  try {
    await fetch(`${getApiBase()}/meter-config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        enabled: meterConfig.enabled,
        email: username.value,
        password: password.value || undefined,
        totp_secret: totpSecret.value,
        polling_interval: meterConfig.polling_interval,
        selected_account_id: meterConfig.selected_account_id,
        selected_account_address: meterConfig.selected_account_address
      })
    })
  } catch (e) {
    console.error('Failed to sync meter credentials:', e)
  }
}

async function discoverMeterAccounts(showMessage = true) {
  meterLoading.value = true
  if (showMessage) meterMessage.value = null
  try {
    const res = await fetch(`${getApiBase()}/meter-accounts`)
    const d = await res.json().catch(() => ({}))
    if (!res.ok) {
      if (showMessage) meterMessage.value = { type: 'error', text: d.detail || 'Failed to find accounts' }
      return
    }

    meterAccounts.value = d.accounts || []
    const onlyAccount = meterAccounts.value.length === 1 ? meterAccounts.value[0] : undefined
    if (!meterConfig.selected_account_id && onlyAccount) {
      meterConfig.selected_account_id = onlyAccount.id
    }
    onMeterAccountChange()
    if (showMessage) {
      meterMessage.value = {
        type: 'success',
        text: `Found ${meterAccounts.value.length} electric account${meterAccounts.value.length === 1 ? '' : 's'}.`
      }
    }
  } catch {
    if (showMessage) meterMessage.value = { type: 'error', text: 'Failed to connect' }
  } finally {
    meterLoading.value = false
  }
}

// Handle meter toggle
async function onMeterToggle() {
  if (meterConfig.enabled) {
    await syncMeterCredentials()
  } else {
    await saveMeterConfig()
  }
}

// Save meter config
async function saveMeterConfig() {
  meterLoading.value = true
  meterMessage.value = null
  try {
    const res = await fetch(`${getApiBase()}/meter-config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        enabled: meterConfig.enabled,
        email: username.value,
        password: password.value || undefined,
        totp_secret: totpSecret.value,
        polling_interval: meterConfig.polling_interval,
        selected_account_id: meterConfig.selected_account_id,
        selected_account_address: meterConfig.selected_account_address
      })
    })
    if (res.ok) {
      meterMessage.value = { type: 'success', text: 'Meter configuration saved!' }
      if (meterConfig.enabled) {
        await loadMeterReading()
      }
    } else {
      const err = await res.json().catch(() => ({}))
      meterMessage.value = { type: 'error', text: err.detail || 'Failed to save' }
    }
  } catch {
    meterMessage.value = { type: 'error', text: 'Failed to connect' }
  } finally {
    meterLoading.value = false
  }
}

// Test meter connection
async function testMeterConnection() {
  meterLoading.value = true
  meterMessage.value = null
  try {
    const res = await fetch(`${getApiBase()}/meter-config/test`, { method: 'POST' })
    const d = await res.json()
    if (d.success) {
      meterMessage.value = { type: 'success', text: d.message }
      if (d.reading) {
        lastReading.value = d.reading
      }
      if (d.account_info) {
        accountInfo.value = d.account_info
      }
      if (d.accounts) {
        meterAccounts.value = d.accounts
        onMeterAccountChange()
      }
      if (d.forecast) {
        forecast.value = d.forecast
      }
      await loadMeterReading()
    } else {
      meterMessage.value = { type: 'error', text: d.detail || d.message || 'Test failed' }
    }
  } catch {
    meterMessage.value = { type: 'error', text: 'Connection test failed' }
  } finally {
    meterLoading.value = false
  }
}

// Refresh meter reading
async function refreshReading() {
  meterLoading.value = true
  meterMessage.value = null
  try {
    const res = await fetch(`${getApiBase()}/meter-reading/refresh`, { method: 'POST' })
    const d = await res.json()
    if (d.success) {
      meterMessage.value = { type: 'success', text: `Reading updated: ${d.reading?.value ?? 0} kWh` }
      lastReading.value = d.reading
      lastReadingCost.value = d.cost ?? null
    } else {
      meterMessage.value = { type: 'error', text: d.detail || 'Failed to refresh' }
    }
  } catch {
    meterMessage.value = { type: 'error', text: 'Failed to refresh reading' }
  } finally {
    meterLoading.value = false
  }
}

// TOTP watcher
watch(totpSecret, (val) => {
  if (!val?.trim()) {
    currentTOTP.value = ''
    timeRemaining.value = 30
  }
})

let totpInterval: ReturnType<typeof setInterval>
onMounted(() => {
  loadSettings()
  loadMeterConfig()
  loadMeterReading()
  
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
.ha-credentials-page {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

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

/* Meter tracking styles */
.ha-check-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}
.ha-check-label input {
  width: 18px;
  height: 18px;
}
.ha-form-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: 1rem;
}
.ha-input-small {
  max-width: 120px;
}
.ha-account-picker-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.ha-account-picker-row select {
  flex: 1;
  min-width: 0;
}
.ha-reading-info {
  margin-top: 1.5rem;
  padding: 1rem;
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  border-radius: 8px;
  border-left: 4px solid #1976d2;
}
.ha-reading-header {
  font-weight: 600;
  font-size: 0.9rem;
  color: #1565c0;
  margin-bottom: 0.75rem;
}
.ha-reading-row {
  display: flex;
  justify-content: space-between;
  padding: 0.25rem 0;
}
.ha-reading-label {
  color: #37474f;
  font-size: 0.9rem;
}
.ha-reading-value {
  font-weight: 600;
  color: #0d47a1;
}
.ha-reading-time {
  font-weight: 400;
  font-size: 0.85rem;
  color: #546e7a;
}
.mqtt-sensor-info {
  margin-top: 1.5rem;
  padding: 1rem;
  background: #f5f5f5;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
}
.mqtt-sensor-header {
  font-weight: 600;
  font-size: 0.9rem;
  color: #424242;
  margin-bottom: 0.5rem;
}
.mqtt-sensor-list {
  margin: 0;
  padding-left: 1.25rem;
  font-size: 0.85rem;
  color: #616161;
}
.mqtt-sensor-list li {
  margin: 0.25rem 0;
}
.mqtt-sensor-list code {
  background: #e0e0e0;
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
  font-family: monospace;
  font-size: 0.8rem;
}
.info-box {
  margin-top: 1.5rem;
  padding: 1rem;
  background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
  border-radius: 8px;
  border-left: 4px solid #ff9800;
  font-size: 0.85rem;
  color: #5d4037;
  line-height: 1.5;
}
.info-box strong {
  color: #e65100;
}
</style>
