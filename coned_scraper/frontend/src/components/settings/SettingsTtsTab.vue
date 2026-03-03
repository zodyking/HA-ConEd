<template>
  <div class="tts-settings">
    <!-- Loading State -->
    <div v-if="loading" class="tts-loading">
      <div class="tts-spinner"></div>
      <p>Loading TTS settings...</p>
    </div>

    <template v-else>
      <!-- Event TTS Alerts (new bill, payment received) -->
      <div class="tts-section">
        <div class="tts-section-header" @click="toggleSection('alerts')">
          <div class="tts-section-title">
            <span class="tts-section-icon">🔔</span>
            <span>Event TTS Alerts</span>
          </div>
          <span class="tts-section-sub">New bill & payment notifications</span>
          <span class="tts-section-chevron" :class="{ expanded: expandedSections.alerts }">▼</span>
        </div>
        
        <div v-if="expandedSections.alerts" class="tts-section-content">
          <div class="tts-toggle-row">
            <label class="tts-toggle">
              <input v-model="config.enabled" type="checkbox" />
              <span class="tts-toggle-slider"></span>
            </label>
            <span class="tts-toggle-label">Enable TTS Alerts</span>
          </div>
          <p class="tts-hint">Announce when new bills arrive or payments are received</p>

          <template v-if="config.enabled">
            <div class="tts-form-group">
              <label class="tts-label">Media Player <span class="tts-required">*</span></label>
              <select v-model="config.media_player" class="tts-select">
                <option value="">-- Select Media Player --</option>
                <option v-for="mp in mediaPlayers" :key="mp.entity_id" :value="mp.entity_id">
                  {{ mp.friendly_name }} ({{ mp.state }})
                </option>
              </select>
              <input
                v-if="!isAddon || mediaPlayers.length === 0"
                v-model="config.media_player"
                type="text"
                class="tts-input tts-input-mt"
                placeholder="media_player.living_room"
              />
            </div>

            <div class="tts-form-group">
              <label class="tts-label">TTS Entity <span class="tts-required">*</span></label>
              <select v-model="config.tts_service" class="tts-select">
                <option value="">-- Select TTS Entity --</option>
                <option v-for="tts in ttsEntities" :key="tts.entity_id" :value="tts.entity_id">
                  {{ tts.friendly_name }}
                </option>
              </select>
              <input
                v-if="!isAddon || ttsEntities.length === 0"
                v-model="config.tts_service"
                type="text"
                class="tts-input tts-input-mt"
                placeholder="tts.google_en_com"
              />
            </div>

            <div class="tts-form-group">
              <label class="tts-label">Volume</label>
              <div class="tts-volume-row">
                <input
                  v-model.number="config.volume"
                  type="range"
                  class="tts-volume-slider"
                  min="0"
                  max="1"
                  step="0.05"
                />
                <span class="tts-volume-value">{{ Math.round((config.volume || 0) * 100) }}%</span>
              </div>
            </div>

            <div class="tts-toggle-row">
              <label class="tts-toggle">
                <input v-model="config.wait_for_idle" type="checkbox" />
                <span class="tts-toggle-slider"></span>
              </label>
              <span class="tts-toggle-label">Wait for media player idle</span>
            </div>

            <div class="tts-form-group">
              <label class="tts-label">Message Prefix</label>
              <input
                v-model="config.prefix"
                type="text"
                class="tts-input"
                placeholder="Message from Con Edison."
              />
              <p class="tts-hint">Spoken at the start of all TTS messages</p>
            </div>

            <!-- Message Templates -->
            <div class="tts-subsection">
              <h4 class="tts-subsection-title">Message Templates</h4>
              <p class="tts-hint">Click a variable to insert it into the template</p>

              <div class="tts-form-group">
                <label class="tts-label">New Bill Message</label>
                <div class="tts-var-chips">
                  <span class="tts-var-chip tts-var-chip-prefix" @click="insertVar('new_bill', '{prefix}')">{prefix}</span>
                  <span class="tts-var-chip" @click="insertVar('new_bill', '{month_range}')">{month_range}</span>
                  <span class="tts-var-chip" @click="insertVar('new_bill', '{amount}')">{amount}</span>
                  <span class="tts-var-chip" @click="insertVar('new_bill', '{due_date}')">{due_date}</span>
                </div>
                <textarea
                  ref="newBillInput"
                  v-model="config.messages.new_bill"
                  class="tts-textarea"
                  rows="2"
                  placeholder="{prefix} Your new bill for {month_range} is {amount}."
                ></textarea>
              </div>

              <div class="tts-form-group">
                <label class="tts-label">Payment Received Message</label>
                <div class="tts-var-chips">
                  <span class="tts-var-chip tts-var-chip-prefix" @click="insertVar('payment_received', '{prefix}')">{prefix}</span>
                  <span class="tts-var-chip" @click="insertVar('payment_received', '{amount}')">{amount}</span>
                  <span class="tts-var-chip" @click="insertVar('payment_received', '{balance}')">{balance}</span>
                  <span class="tts-var-chip" @click="insertVar('payment_received', '{payee_name}')">{payee_name}</span>
                </div>
                <textarea
                  ref="paymentInput"
                  v-model="config.messages.payment_received"
                  class="tts-textarea"
                  rows="2"
                  placeholder="{prefix} Payment of {amount} received. Balance is now {balance}."
                ></textarea>
              </div>
            </div>
          </template>

          <div class="tts-actions-row">
            <button class="tts-btn tts-btn-primary" :disabled="saving" @click="saveConfig">
              {{ saving ? 'Saving...' : 'Save Alert Settings' }}
            </button>
            <button
              class="tts-btn tts-btn-orange"
              :disabled="!config.enabled || !config.media_player || testing"
              @click="testTts"
            >
              {{ testing ? 'Sending...' : 'Test TTS' }}
            </button>
          </div>

          <div v-if="alertMessage" :class="['tts-message', alertMessage.type]">
            {{ alertMessage.text }}
          </div>
        </div>
      </div>

      <!-- Scheduled Announcements -->
      <div class="tts-section">
        <div class="tts-section-header" @click="toggleSection('schedule')">
          <div class="tts-section-title">
            <span class="tts-section-icon">⏰</span>
            <span>Scheduled Announcements</span>
          </div>
          <span class="tts-section-sub">Automatic bill summary at set times</span>
          <span class="tts-section-chevron" :class="{ expanded: expandedSections.schedule }">▼</span>
        </div>
        
        <div v-if="expandedSections.schedule" class="tts-section-content">
          <div class="tts-toggle-row">
            <label class="tts-toggle">
              <input v-model="schedule.enabled" type="checkbox" />
              <span class="tts-toggle-slider"></span>
            </label>
            <span class="tts-toggle-label">Enable Scheduled Announcements</span>
          </div>
          <p class="tts-hint">Requires TTS alerts to be enabled and configured above</p>

          <template v-if="schedule.enabled">
            <div class="tts-form-group">
              <label class="tts-label">Announce Every</label>
              <select v-model.number="schedule.hour_pattern" class="tts-select">
                <option :value="1">1 hour</option>
                <option :value="2">2 hours</option>
                <option :value="3">3 hours</option>
                <option :value="4">4 hours</option>
                <option :value="6">6 hours</option>
                <option :value="12">12 hours</option>
              </select>
            </div>

            <div class="tts-form-group">
              <label class="tts-label">Minute Offset (0-59)</label>
              <input
                v-model.number="schedule.minute_offset"
                type="number"
                class="tts-input tts-input-small"
                min="0"
                max="59"
              />
              <p class="tts-hint">e.g., 3 = announcements at :03 past the hour</p>
            </div>

            <div class="tts-form-group">
              <label class="tts-label">Active Hours</label>
              <div class="tts-time-row">
                <input v-model="schedule.start_time" type="time" class="tts-time-input" />
                <span class="tts-time-separator">to</span>
                <input v-model="schedule.end_time" type="time" class="tts-time-input" />
              </div>
            </div>

            <div class="tts-form-group">
              <label class="tts-label">Active Days</label>
              <div class="tts-days-row">
                <label
                  v-for="day in dayOptions"
                  :key="day.value"
                  class="tts-day-chip"
                  :class="{ active: schedule.days_of_week?.includes(day.value) }"
                >
                  <input
                    type="checkbox"
                    :checked="schedule.days_of_week?.includes(day.value)"
                    @change="toggleDay(day.value)"
                  />
                  {{ day.label }}
                </label>
              </div>
            </div>

            <!-- Usage Sensors - Only show when meter tracking is NOT enabled -->
            <div v-if="!meterTrackingEnabled" class="tts-subsection">
              <h4 class="tts-subsection-title">Usage Projection Sensors</h4>
              <p class="tts-hint">Configure Home Assistant sensors for real-time usage projections. The app will multiply these values by the kWh cost sensor (from the Con Edison integration).</p>

              <div class="tts-form-group">
                <label class="tts-label">Current Usage Sensor (kWh)</label>
                <input
                  v-model="schedule.current_usage_sensor"
                  type="text"
                  class="tts-input"
                  placeholder="sensor.electric_meter_kwh"
                />
                <p class="tts-hint">Sensor that tracks current month-to-date kWh usage</p>
              </div>

              <div class="tts-form-group">
                <label class="tts-label">Future Usage Projection Sensor (kWh)</label>
                <input
                  v-model="schedule.future_usage_sensor"
                  type="text"
                  class="tts-input"
                  placeholder="sensor.projected_monthly_kwh"
                />
                <p class="tts-hint">Sensor that projects end-of-month kWh usage</p>
              </div>
            </div>
            
            <!-- Meter Tracking Active Notice -->
            <div v-if="meterTrackingEnabled" class="tts-subsection tts-meter-active">
              <div class="tts-meter-notice">
                <span class="tts-meter-icon">⚡</span>
                <div>
                  <strong>Meter Tracking Active</strong>
                  <p>Usage data is automatically sourced from your Con Edison meter via the Con Edison integration sensors.</p>
                </div>
              </div>
            </div>

            <!-- Schedule Message Builder -->
            <div class="tts-subsection">
              <h4 class="tts-subsection-title">Scheduled Message Template</h4>
              <p class="tts-hint">Build your bill summary message. Click variables to insert.</p>

              <div class="tts-var-chips">
                <span class="tts-var-chip tts-var-chip-prefix" @click="insertScheduleVar('{prefix}')">{prefix}</span>
                <span class="tts-var-chip" @click="insertScheduleVar('{balance}')">{balance}</span>
                <span class="tts-var-chip" @click="insertScheduleVar('{latest_bill_amount}')">{latest_bill_amount}</span>
                <span class="tts-var-chip" @click="insertScheduleVar('{due_date}')">{due_date}</span>
                <span class="tts-var-chip" @click="insertScheduleVar('{last_bill_kwh}')">{last_bill_kwh}</span>
                <span class="tts-var-chip tts-var-chip-usage" @click="insertScheduleVar('{current_usage_kwh}')">{current_usage_kwh}</span>
                <span class="tts-var-chip tts-var-chip-usage" @click="insertScheduleVar('{current_usage_cost}')">{current_usage_cost}</span>
                <span class="tts-var-chip tts-var-chip-usage" @click="insertScheduleVar('{projected_usage_kwh}')">{projected_usage_kwh}</span>
                <span class="tts-var-chip tts-var-chip-usage" @click="insertScheduleVar('{projected_usage_cost}')">{projected_usage_cost}</span>
              </div>

              <textarea
                ref="scheduleMessageInput"
                v-model="schedule.message_template"
                class="tts-textarea tts-textarea-lg"
                rows="5"
                placeholder="{prefix} Your current balance is {balance}. Your last bill was {latest_bill_amount}, using {last_bill_kwh}, due {due_date}."
              ></textarea>

              <div class="tts-preview-section">
                <button class="tts-btn tts-btn-secondary tts-btn-sm" @click="generatePreview">
                  Preview Message
                </button>
                <div v-if="previewMessage" class="tts-preview-box">
                  <span class="tts-preview-label">Preview:</span>
                  {{ previewMessage }}
                </div>
              </div>
            </div>
          </template>

          <div class="tts-actions-row">
            <button class="tts-btn tts-btn-primary" :disabled="scheduleSaving" @click="saveSchedule">
              {{ scheduleSaving ? 'Saving...' : 'Save Schedule' }}
            </button>
            <button
              class="tts-btn tts-btn-orange"
              :disabled="!config.enabled || !config.media_player || testingSummary"
              @click="testBillSummary"
            >
              {{ testingSummary ? 'Sending...' : 'Test Bill Summary' }}
            </button>
          </div>

          <div v-if="scheduleMessage" :class="['tts-message', scheduleMessage.type]">
            {{ scheduleMessage.text }}
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getApiBase } from '../../lib/api-base'

interface HaEntity {
  entity_id: string
  friendly_name: string
  state?: string
}

const loading = ref(true)
const saving = ref(false)
const scheduleSaving = ref(false)
const testing = ref(false)
const testingSummary = ref(false)

const isAddon = ref(false)
const mediaPlayers = ref<HaEntity[]>([])
const ttsEntities = ref<HaEntity[]>([])

const newBillInput = ref<HTMLTextAreaElement | null>(null)
const paymentInput = ref<HTMLTextAreaElement | null>(null)
const scheduleMessageInput = ref<HTMLTextAreaElement | null>(null)

const config = reactive({
  enabled: false,
  media_player: '',
  volume: 0.7,
  tts_service: '',
  wait_for_idle: true,
  prefix: 'Message from Con Edison.',
  messages: {
    new_bill: '{prefix} Your new bill for {month_range} is now available. The total is {amount}, due {due_date}.',
    payment_received: '{prefix} Your payment of {amount} has been received. Your account balance is now {balance}.',
  }
})

const schedule = reactive({
  enabled: false,
  hour_pattern: 3,
  minute_offset: 0,
  start_time: '08:00',
  end_time: '21:00',
  days_of_week: ['mon', 'tue', 'wed', 'thu', 'fri'] as string[],
  message_template: '{prefix} Your current bill is {latest_bill_amount}, using {last_bill_kwh}, due {due_date}. Your account balance is {balance}. Current usage: {current_usage_kwh} at {current_usage_cost}. Projected usage: {projected_usage_kwh} at {projected_usage_cost}.',
  current_usage_sensor: '',
  future_usage_sensor: ''
})

const expandedSections = reactive({
  alerts: true,
  schedule: false
})

const alertMessage = ref<{ type: string; text: string } | null>(null)
const scheduleMessage = ref<{ type: string; text: string } | null>(null)
const previewMessage = ref('')
const meterTrackingEnabled = ref(false)

const dayOptions = [
  { value: 'mon', label: 'Mon' },
  { value: 'tue', label: 'Tue' },
  { value: 'wed', label: 'Wed' },
  { value: 'thu', label: 'Thu' },
  { value: 'fri', label: 'Fri' },
  { value: 'sat', label: 'Sat' },
  { value: 'sun', label: 'Sun' }
]

function toggleSection(key: keyof typeof expandedSections) {
  expandedSections[key] = !expandedSections[key]
}

function toggleDay(day: string) {
  if (!schedule.days_of_week) schedule.days_of_week = []
  const idx = schedule.days_of_week.indexOf(day)
  if (idx >= 0) {
    schedule.days_of_week.splice(idx, 1)
  } else {
    schedule.days_of_week.push(day)
  }
}

function insertVar(templateKey: 'new_bill' | 'payment_received', varName: string) {
  const inputRef = templateKey === 'new_bill' ? newBillInput.value : paymentInput.value
  if (!inputRef) {
    config.messages[templateKey] += varName
    return
  }
  const start = inputRef.selectionStart || 0
  const end = inputRef.selectionEnd || 0
  const text = config.messages[templateKey]
  config.messages[templateKey] = text.slice(0, start) + varName + text.slice(end)
  setTimeout(() => {
    inputRef.focus()
    inputRef.setSelectionRange(start + varName.length, start + varName.length)
  }, 0)
}

function insertScheduleVar(varName: string) {
  const inputRef = scheduleMessageInput.value
  if (!inputRef) {
    schedule.message_template += varName
    return
  }
  const start = inputRef.selectionStart || 0
  const end = inputRef.selectionEnd || 0
  const text = schedule.message_template
  schedule.message_template = text.slice(0, start) + varName + text.slice(end)
  setTimeout(() => {
    inputRef.focus()
    inputRef.setSelectionRange(start + varName.length, start + varName.length)
  }, 0)
}

async function generatePreview() {
  try {
    // Pass current sensor values as query params (in case not saved yet)
    const params = new URLSearchParams()
    if (schedule.current_usage_sensor) {
      params.append('current_sensor', schedule.current_usage_sensor)
    }
    if (schedule.future_usage_sensor) {
      params.append('future_sensor', schedule.future_usage_sensor)
    }
    const queryString = params.toString()
    const url = `${getApiBase()}/tts/preview-message${queryString ? '?' + queryString : ''}`
    const res = await fetch(url)
    if (res.ok) {
      const data = await res.json()
      console.log('TTS Preview response:', JSON.stringify(data, null, 2))
      console.log('Debug info:', data._debug)
      console.log('Current usage:', data.current_usage)
      console.log('Projected usage:', data.projected_usage)
      let msg = schedule.message_template || ''
      msg = msg.replace(/{prefix}/g, config.prefix || 'Message from Con Edison.')
      msg = msg.replace(/{balance}/g, data.balance ?? 'N/A')
      msg = msg.replace(/{latest_bill_amount}/g, data.latest_bill?.amount || 'N/A')
      msg = msg.replace(/{due_date}/g, data.latest_bill?.due_date || 'N/A')
      msg = msg.replace(/{last_bill_kwh}/g, data.latest_bill?.kwh_used || 'N/A')
      msg = msg.replace(/{current_usage_kwh}/g, data.current_usage?.kwh || 'N/A')
      msg = msg.replace(/{current_usage_cost}/g, data.current_usage?.cost || 'N/A')
      msg = msg.replace(/{projected_usage_kwh}/g, data.projected_usage?.kwh || 'N/A')
      msg = msg.replace(/{projected_usage_cost}/g, data.projected_usage?.cost || 'N/A')
      previewMessage.value = msg
    } else {
      console.error('Preview API returned error:', res.status)
      previewMessage.value = 'Error generating preview. Check the logs.'
    }
  } catch (e) {
    console.error('Failed to generate preview:', e)
    previewMessage.value = 'Failed to connect to server.'
  }
}

async function loadHaEntities() {
  try {
    const res = await fetch(`${getApiBase()}/ha-entities`)
    if (res.ok) {
      const data = await res.json()
      isAddon.value = data.is_addon || false
      mediaPlayers.value = data.media_players || []
      ttsEntities.value = data.tts_entities || []
    }
  } catch (e) {
    console.error('Failed to load HA entities:', e)
  }
}

async function loadConfig() {
  try {
    const res = await fetch(`${getApiBase()}/tts-config`)
    if (res.ok) {
      const data = await res.json()
      config.enabled = data.enabled ?? false
      config.media_player = data.media_player ?? ''
      config.volume = typeof data.volume === 'number' ? data.volume : 0.7
      config.tts_service = data.tts_service ?? ''
      config.wait_for_idle = data.wait_for_idle ?? true
      config.prefix = data.prefix ?? 'Message from Con Edison.'
      if (data.messages && typeof data.messages === 'object') {
        config.messages = { ...config.messages, ...data.messages }
      }
    }
  } catch (e) {
    console.error('Failed to load TTS config:', e)
  }
}

async function loadSchedule() {
  try {
    const res = await fetch(`${getApiBase()}/tts-schedule`)
    if (res.ok) {
      const data = await res.json()
      schedule.enabled = data.enabled ?? false
      schedule.hour_pattern = data.hour_pattern ?? 3
      schedule.minute_offset = data.minute_offset ?? 0
      schedule.start_time = data.start_time ?? '08:00'
      schedule.end_time = data.end_time ?? '21:00'
      schedule.days_of_week = data.days_of_week ?? ['mon', 'tue', 'wed', 'thu', 'fri']
      schedule.message_template = data.message_template ?? schedule.message_template
      schedule.current_usage_sensor = data.current_usage_sensor ?? ''
      schedule.future_usage_sensor = data.future_usage_sensor ?? ''
    }
  } catch (e) {
    console.error('Failed to load schedule:', e)
  }
}

async function saveConfig() {
  saving.value = true
  alertMessage.value = null
  try {
    const res = await fetch(`${getApiBase()}/tts-config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        enabled: config.enabled,
        media_player: config.media_player.trim(),
        volume: config.volume,
        tts_service: config.tts_service || '',
        wait_for_idle: config.wait_for_idle,
        prefix: config.prefix || 'Message from Con Edison.',
        messages: config.messages
      })
    })
    if (res.ok) {
      alertMessage.value = { type: 'success', text: 'Alert settings saved' }
    } else {
      const err = await res.json().catch(() => ({}))
      alertMessage.value = { type: 'error', text: err.detail || 'Failed to save' }
    }
  } catch {
    alertMessage.value = { type: 'error', text: 'Failed to connect' }
  } finally {
    saving.value = false
  }
}

async function saveSchedule() {
  scheduleSaving.value = true
  scheduleMessage.value = null
  try {
    const res = await fetch(`${getApiBase()}/tts-schedule`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        enabled: schedule.enabled,
        hour_pattern: schedule.hour_pattern,
        minute_offset: schedule.minute_offset,
        start_time: schedule.start_time,
        end_time: schedule.end_time,
        days_of_week: schedule.days_of_week,
        message_template: schedule.message_template,
        current_usage_sensor: schedule.current_usage_sensor,
        future_usage_sensor: schedule.future_usage_sensor
      })
    })
    if (res.ok) {
      scheduleMessage.value = { type: 'success', text: 'Schedule saved' }
    } else {
      const err = await res.json().catch(() => ({}))
      scheduleMessage.value = { type: 'error', text: err.detail || 'Failed to save' }
    }
  } catch {
    scheduleMessage.value = { type: 'error', text: 'Failed to connect' }
  } finally {
    scheduleSaving.value = false
  }
}

async function testTts() {
  testing.value = true
  alertMessage.value = null
  try {
    const res = await fetch(`${getApiBase()}/tts/test`, { method: 'POST' })
    const data = await res.json().catch(() => ({}))
    if (res.ok) {
      alertMessage.value = { type: 'success', text: data.message || 'TTS sent' }
    } else {
      alertMessage.value = { type: 'error', text: data.detail || 'Failed' }
    }
  } catch {
    alertMessage.value = { type: 'error', text: 'Failed to connect' }
  } finally {
    testing.value = false
  }
}

async function testBillSummary() {
  testingSummary.value = true
  scheduleMessage.value = null
  try {
    const res = await fetch(`${getApiBase()}/tts/trigger-bill-summary`, { method: 'POST' })
    const data = await res.json().catch(() => ({}))
    if (res.ok) {
      scheduleMessage.value = { type: 'success', text: data.message || 'Bill summary sent' }
    } else {
      scheduleMessage.value = { type: 'error', text: data.detail || 'Failed' }
    }
  } catch {
    scheduleMessage.value = { type: 'error', text: 'Failed to connect' }
  } finally {
    testingSummary.value = false
  }
}

async function checkMeterTracking() {
  try {
    const res = await fetch(`${getApiBase()}/meter-reading`)
    if (res.ok) {
      const data = await res.json()
      meterTrackingEnabled.value = data.enabled && data.forecast?.usage_to_date !== null
    }
  } catch {
    meterTrackingEnabled.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadHaEntities(), loadConfig(), loadSchedule(), checkMeterTracking()])
  loading.value = false
})
</script>

<style scoped>
.tts-settings {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.tts-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: #888;
}

.tts-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e0e0e0;
  border-top-color: #ff9800;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.tts-section {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.tts-section-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  cursor: pointer;
  background: #fafafa;
  border-bottom: 1px solid #eee;
  transition: background 0.2s;
}

.tts-section-header:hover {
  background: #f5f5f5;
}

.tts-section-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: #333;
}

.tts-section-icon {
  font-size: 1.1rem;
}

.tts-section-sub {
  flex: 1;
  font-size: 0.85rem;
  color: #888;
  margin-left: 0.5rem;
}

.tts-section-chevron {
  color: #999;
  font-size: 0.75rem;
  transition: transform 0.2s;
}

.tts-section-chevron.expanded {
  transform: rotate(180deg);
}

.tts-section-content {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.tts-subsection {
  margin-top: 0.5rem;
  padding: 1rem;
  background: #f9f9f9;
  border-radius: 8px;
  border: 1px solid #eee;
}

.tts-subsection-title {
  margin: 0 0 0.75rem 0;
  font-size: 0.95rem;
  font-weight: 600;
  color: #444;
}

.tts-form-group {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.tts-label {
  font-weight: 500;
  color: #444;
  font-size: 0.9rem;
}

.tts-required {
  color: #e65100;
}

.tts-input,
.tts-select,
.tts-textarea {
  padding: 0.65rem 0.85rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 0.95rem;
  background: #fff;
  transition: border-color 0.2s, box-shadow 0.2s;
  font-family: inherit;
}

.tts-input:focus,
.tts-select:focus,
.tts-textarea:focus {
  outline: none;
  border-color: #ff9800;
  box-shadow: 0 0 0 3px rgba(255, 152, 0, 0.1);
}

.tts-input-mt {
  margin-top: 0.5rem;
}

.tts-input-small {
  width: 100px;
}

.tts-textarea {
  resize: vertical;
  min-height: 60px;
  width: 100%;
  box-sizing: border-box;
}

.tts-textarea-lg {
  min-height: 120px;
  width: 100%;
}

.tts-select {
  cursor: pointer;
}

.tts-hint {
  font-size: 0.8rem;
  color: #888;
  margin-top: 0.25rem;
}

.tts-toggle-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.tts-toggle {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 26px;
}

.tts-toggle input {
  opacity: 0;
  width: 0;
  height: 0;
}

.tts-toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: #ccc;
  border-radius: 26px;
  transition: background 0.3s;
}

.tts-toggle-slider::before {
  content: '';
  position: absolute;
  width: 22px;
  height: 22px;
  left: 2px;
  top: 2px;
  background: white;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  transition: transform 0.3s;
}

.tts-toggle input:checked + .tts-toggle-slider {
  background: #ff9800;
}

.tts-toggle input:checked + .tts-toggle-slider::before {
  transform: translateX(22px);
}

.tts-toggle-label {
  font-weight: 500;
  color: #333;
}

.tts-volume-row {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.tts-volume-slider {
  flex: 1;
  height: 8px;
  -webkit-appearance: none;
  appearance: none;
  background: #e0e0e0;
  border-radius: 4px;
}

.tts-volume-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  background: #ff9800;
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.tts-volume-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  background: #ff9800;
  border-radius: 50%;
  cursor: pointer;
  border: none;
}

.tts-volume-value {
  min-width: 3.5rem;
  font-weight: 500;
  color: #333;
}

.tts-time-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.tts-time-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 0.95rem;
}

.tts-time-separator {
  color: #888;
}

.tts-days-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.tts-day-chip {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.4rem 0.75rem;
  background: #f5f5f5;
  border: 1px solid #ddd;
  border-radius: 20px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.tts-day-chip input {
  display: none;
}

.tts-day-chip.active {
  background: #ff9800;
  border-color: #ff9800;
  color: white;
}

.tts-var-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.5rem;
}

.tts-var-chip {
  padding: 0.25rem 0.6rem;
  background: #e3f2fd;
  border: 1px solid #90caf9;
  border-radius: 4px;
  font-size: 0.8rem;
  font-family: monospace;
  color: #1565c0;
  cursor: pointer;
  transition: all 0.2s;
}

.tts-var-chip:hover {
  background: #bbdefb;
  border-color: #64b5f6;
}

.tts-var-chip-prefix {
  background: #fce4ec;
  border-color: #f48fb1;
  color: #c2185b;
}

.tts-var-chip-prefix:hover {
  background: #f8bbd9;
  border-color: #f06292;
}

.tts-var-chip-usage {
  background: #e8f5e9;
  border-color: #81c784;
  color: #2e7d32;
}

.tts-var-chip-usage:hover {
  background: #c8e6c9;
  border-color: #66bb6a;
}

.tts-preview-section {
  margin-top: 0.75rem;
  width: 100%;
}

.tts-preview-box {
  margin-top: 0.5rem;
  padding: 1rem;
  background: #fff8e1;
  border: 1px solid #ffe082;
  border-radius: 8px;
  font-size: 0.9rem;
  color: #5d4037;
  line-height: 1.6;
  width: 100%;
  box-sizing: border-box;
  word-wrap: break-word;
}

.tts-preview-label {
  font-weight: 600;
  margin-right: 0.5rem;
}

.tts-actions-row {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-top: 0.5rem;
}

.tts-btn {
  padding: 0.65rem 1.25rem;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s;
}

.tts-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.tts-btn-sm {
  padding: 0.4rem 0.85rem;
  font-size: 0.85rem;
}

.tts-btn-primary {
  background: #03a9f4;
  color: white;
}

.tts-btn-primary:hover:not(:disabled) {
  background: #0288d1;
}

.tts-btn-secondary {
  background: #e0e0e0;
  color: #333;
}

.tts-btn-secondary:hover:not(:disabled) {
  background: #d0d0d0;
}

.tts-btn-orange {
  background: #ff9800;
  color: white;
}

.tts-btn-orange:hover:not(:disabled) {
  background: #f57c00;
}

.tts-message {
  padding: 0.75rem 1rem;
  border-radius: 8px;
  font-size: 0.9rem;
}

.tts-message.success {
  background: #e8f5e9;
  color: #2e7d32;
}

.tts-message.error {
  background: #ffebee;
  color: #c62828;
}

/* Meter Tracking Active Notice */
.tts-meter-active {
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  border: 1px solid #64b5f6;
}

.tts-meter-notice {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.tts-meter-icon {
  font-size: 1.5rem;
  line-height: 1;
}

.tts-meter-notice strong {
  color: #1565c0;
  font-size: 0.95rem;
}

.tts-meter-notice p {
  margin: 0.25rem 0 0 0;
  font-size: 0.85rem;
  color: #1976d2;
}
</style>
