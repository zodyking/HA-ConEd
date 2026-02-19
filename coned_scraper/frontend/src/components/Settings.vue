<template>
  <div class="ha-settings">
    <!-- Password Lock Modal -->
    <div v-if="!isUnlocked" class="ha-lock-overlay">
      <div class="ha-card ha-lock-card">
        <div class="ha-card-header">
          <span class="ha-card-icon">🔒</span>
          <span>Settings Password Required</span>
        </div>
        <div class="ha-card-content">
          <form @submit.prevent="handlePasswordSubmit">
            <div class="ha-form-group">
              <label class="ha-form-label">Enter 4-digit PIN</label>
              <div class="ha-pin-row">
                <input
                  v-for="(_, i) in 4"
                  :key="i"
                  :ref="el => { if (el) pinRefs[i] = el as HTMLInputElement }"
                  v-model="pinDigits[i]"
                  type="password"
                  inputmode="numeric"
                  maxlength="1"
                  autocomplete="one-time-code"
                  class="ha-pin-input"
                  :class="{ error: passwordError }"
                  @input="onPinInput(i, $event)"
                  @keydown="handlePinKeydown($event, i)"
                  @paste="onPinPaste"
                />
              </div>
              <div v-if="passwordError" class="ha-password-error">{{ passwordError }}</div>
              <div class="ha-pin-hint">Default PIN is <strong>0000</strong>. Change in App Settings after unlocking.</div>
            </div>
            <div class="ha-form-actions">
              <button type="button" class="ha-button ha-button-gray" @click="cancelLock">Cancel</button>
              <button type="submit" class="ha-button ha-button-primary" :disabled="pinDigits.some(d => !d)">Unlock Settings</button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Unlocked Content -->
    <template v-else>
      <!-- Menu -->
      <div v-if="currentPage === 'menu'" class="ha-settings-menu">
        <h2 class="ha-settings-title">⚙️ Settings</h2>
        <div class="ha-menu-list">
          <button
            v-for="item in menuItems"
            :key="item.id"
            type="button"
            class="ha-menu-item"
            @click="currentPage = item.id"
          >
            <span class="ha-menu-icon">{{ item.icon }}</span>
            <div class="ha-menu-text">
              <div class="ha-menu-label">{{ item.label }}</div>
              <div class="ha-menu-desc">{{ item.description }}</div>
            </div>
            <span class="ha-menu-arrow">›</span>
          </button>
        </div>
      </div>

      <!-- Sub-pages (Console, Credentials, MQTT, etc.) -->
      <template v-else>
        <div class="ha-settings-page">
          <button type="button" class="ha-back-btn" @click="currentPage = 'menu'">← Back to Settings</button>
          <Dashboard v-if="currentPage === 'console'" />
          <SettingsCredentialsTab v-else-if="currentPage === 'credentials'" />
          <SettingsAutomatedTab v-else-if="currentPage === 'automated'" />
          <SettingsMqttTab v-else-if="currentPage === 'mqtt'" />
          <SettingsAppTab v-else-if="currentPage === 'app-settings'" />
          <SettingsPayeesPaymentsTab v-else-if="currentPage === 'payees-payments'" />
          <div v-else-if="currentPage === 'tts'" class="ha-card ha-tts-card">
            <div class="ha-card-header">
              <span class="ha-card-icon">🔊</span>
              <span>TTS Alerts</span>
            </div>
            <div class="ha-card-content">
              <p class="ha-tts-intro">Configure text-to-speech for Con Edison events. Add multiple media players; TTS is sent to each when triggered.</p>
              <form @submit.prevent="handleTtsSave" class="ha-tts-form">
                <details class="ha-tts-details" open>
                  <summary>General</summary>
                  <div class="ha-tts-details-content">
                    <div class="ha-form-group">
                      <label class="ha-check-label">
                        <input v-model="ttsEnabled" type="checkbox" />
                        <span>Enable TTS Alerts</span>
                      </label>
                    </div>
                    <div class="ha-form-group">
                      <label class="ha-check-label">
                        <input v-model="ttsWaitForIdle" type="checkbox" />
                        <span>Wait for media player idle</span>
                      </label>
                      <div class="info-text">Waits for each player to be idle before playing. Unknown or unavailable (disconnected) are not treated as ready.</div>
                    </div>
                  </div>
                </details>

                <details class="ha-tts-details" open>
                  <summary>Media Players ({{ ttsMediaPlayersList.length }})</summary>
                  <div class="ha-tts-details-content">
                    <div v-for="(p, idx) in ttsMediaPlayersList" :key="idx" class="ha-tts-mp-card">
                      <div class="ha-tts-mp-header">
                        <span class="ha-tts-mp-status" :class="'state-' + (ttsEntityStates[getTtsMpEntityId(p)] || 'unknown')">{{ ttsEntityStates[getTtsMpEntityId(p)] || '—' }}</span>
                        <button type="button" class="ha-btn-sm ha-btn-red" title="Remove" @click="removeTtsMediaPlayer(idx)">×</button>
                      </div>
                      <div class="ha-form-group">
                        <label class="ha-form-label">Media Player</label>
                        <select v-if="ttsMediaPlayersListOptions.length" v-model="p.entity_id" class="ha-form-input">
                          <option value="">Select...</option>
                          <option v-for="mp in ttsMediaPlayersListOptions" :key="mp" :value="mp">{{ mp }}</option>
                          <option value="__custom__">Other</option>
                        </select>
                        <input v-if="p.entity_id === '__custom__'" v-model="p.entity_id_custom" type="text" class="ha-form-input ha-form-input-mt" placeholder="media_player.room" />
                        <input v-else-if="!ttsMediaPlayersListOptions.length" v-model="p.entity_id_custom" type="text" class="ha-form-input" placeholder="media_player.room" />
                      </div>
                      <div class="ha-form-group">
                        <label class="ha-form-label">Volume ({{ Math.round((p.volume ?? 0.7) * 100) }}%)</label>
                        <input v-model.number="p.volume" type="range" class="ha-volume-slider" min="0" max="1" step="0.05" />
                      </div>
                      <button
                        type="button"
                        class="ha-button ha-btn-test ha-btn-test-sm"
                        :disabled="!ttsEnabled || !getTtsMpEntityId(p) || !effectiveTtsEngine || ttsTestLoadingByIdx[idx]"
                        @click="handleTtsTestForPlayer(idx)"
                      >
                        {{ ttsTestLoadingByIdx[idx] ? 'Sending...' : 'Test TTS' }}
                      </button>
                    </div>
                    <button type="button" class="ha-button ha-button-secondary" @click="addTtsMediaPlayer">+ Add Media Player</button>
                  </div>
                </details>

                <details class="ha-tts-details">
                  <summary>TTS Engine & Options</summary>
                  <div class="ha-tts-details-content">
                    <div class="ha-form-group">
                      <label class="ha-form-label">TTS Engine (Target)</label>
                      <select v-if="ttsEntities.length" v-model="ttsEngine" class="ha-form-input">
                        <option value="">Select...</option>
                        <option v-for="e in ttsEntities" :key="e" :value="e">{{ e }}</option>
                        <option value="__custom__">Other</option>
                      </select>
                      <input v-if="ttsEngine === '__custom__' || !ttsEntities.length" v-model="ttsEngineCustom" type="text" class="ha-form-input" placeholder="tts.google_translate_en_com" />
                    </div>
                    <div class="ha-form-group">
                      <label class="ha-check-label">
                        <input v-model="ttsCache" type="checkbox" />
                        <span>Cache TTS</span>
                      </label>
                    </div>
                    <div class="ha-form-group">
                      <label class="ha-form-label">TTS Prefix</label>
                      <input v-model="ttsPrefix" type="text" class="ha-form-input" placeholder="Message from Con Edison." />
                    </div>
                  </div>
                </details>

                <details class="ha-tts-details">
                  <summary>TTS Message Templates</summary>
                  <div class="ha-tts-details-content">
                    <p class="info-text">Use <code>{placeholder}</code> for variables (e.g. <code>{amount}</code>, <code>{balance}</code>, <code>{month_range}</code>).</p>
                    <div class="ha-form-group">
                      <label class="ha-form-label">New Bill Message</label>
                      <input v-model="ttsMsgNewBill" type="text" class="ha-form-input" placeholder="Your new Con Edison bill for {month_range} is now available." />
                    </div>
                    <div class="ha-form-group">
                      <label class="ha-form-label">Payment Received Message</label>
                      <input v-model="ttsMsgPayment" type="text" class="ha-form-input" placeholder="Your payment of {amount} has been received. Balance is now {balance}." />
                    </div>
                  </div>
                </details>

                <details class="ha-tts-details" @toggle="e => (e.target as HTMLDetailsElement).open && fetchTtsLogsAndQueue()">
                  <summary>TTS Logs</summary>
                  <div class="ha-tts-details-content">
                    <p class="info-text">Every TTS sent from this app (success or fail) and the current queue.</p>
                    <div v-if="ttsQueue.length" class="ha-tts-queue-section">
                      <div class="ha-tts-section-label">Queue ({{ ttsQueue.length }})</div>
                      <div v-for="(q, i) in ttsQueue" :key="i" class="ha-tts-log-entry ha-tts-queue-entry">
                        <span class="ha-tts-log-source">{{ q.source || 'pending' }}</span>
                        <span class="ha-tts-log-msg">{{ (q.message || '').slice(0, 60) }}{{ (q.message || '').length > 60 ? '…' : '' }}</span>
                      </div>
                    </div>
                    <div class="ha-tts-logs-section">
                      <div class="ha-tts-section-label">Logs ({{ ttsLogs.length }})</div>
                      <div v-if="!ttsLogs.length" class="ha-tts-logs-empty">No TTS logs yet.</div>
                      <div v-for="(log, i) in ttsLogs" :key="i" class="ha-tts-log-entry" :class="log.success ? 'success' : 'error'">
                        <span class="ha-tts-log-ts">{{ formatTtsLogTs(log.ts) }}</span>
                        <span class="ha-tts-log-source">{{ log.source }}</span>
                        <span class="ha-tts-log-status">{{ log.success ? '✓' : '✗' }}</span>
                        <span class="ha-tts-log-msg">{{ log.message }}</span>
                        <span v-if="log.error" class="ha-tts-log-error">{{ log.error }}</span>
                      </div>
                    </div>
                  </div>
                </details>

                <details class="ha-tts-details">
                  <summary>Special TTS Message (Bill Summary)</summary>
                  <div class="ha-tts-details-content">
                    <p class="info-text">A scheduled TTS that reports bill, balance, avg daily usage, and bill estimates. Plays at the configured frequency between the selected hours on selected days.</p>
                    <form @submit.prevent="handleBillSummarySave" class="ha-tts-form">
                      <div class="ha-form-group">
                        <label class="ha-check-label">
                          <input v-model="billSummaryEnabled" type="checkbox" />
                          <span>Enable scheduled bill summary TTS</span>
                        </label>
                      </div>
                      <div class="ha-form-group">
                        <label class="ha-form-label">Days of week</label>
                        <div class="ha-check-row">
                          <label v-for="d in weekdays" :key="d.value" class="ha-check-inline">
                            <input v-model="billSummaryDays" type="checkbox" :value="d.value" />
                            <span>{{ d.label }}</span>
                          </label>
                        </div>
                      </div>
                      <div class="ha-form-group ha-form-row">
                        <div>
                          <label class="ha-form-label">Start time</label>
                          <div class="ha-time-row">
                            <select v-model.number="billSummaryStartHour12" class="ha-form-input">
                              <option v-for="h in hour12Options" :key="h" :value="h">{{ h }}</option>
                            </select>
                            <select v-model="billSummaryStartAmPm" class="ha-form-input">
                              <option value="am">AM</option>
                              <option value="pm">PM</option>
                            </select>
                          </div>
                        </div>
                        <div>
                          <label class="ha-form-label">End time</label>
                          <div class="ha-time-row">
                            <select v-model.number="billSummaryEndHour12" class="ha-form-input">
                              <option v-for="h in hour12Options" :key="h" :value="h">{{ h }}</option>
                            </select>
                            <select v-model="billSummaryEndAmPm" class="ha-form-input">
                              <option value="am">AM</option>
                              <option value="pm">PM</option>
                            </select>
                          </div>
                        </div>
                        <div>
                          <label class="ha-form-label">Every X hours</label>
                          <input v-model.number="billSummaryFrequencyHours" type="number" class="ha-form-input" min="1" max="24" />
                        </div>
                        <div>
                          <label class="ha-form-label">Minute of hour (0–59)</label>
                          <input v-model.number="billSummaryMinuteOfHour" type="number" class="ha-form-input" min="0" max="59" />
                        </div>
                      </div>
                      <datalist id="ha-sensor-datalist">
                        <option v-for="e in haSensorEntities" :key="e" :value="e" />
                      </datalist>
                      <div class="ha-form-group">
                        <label class="ha-form-label">Current usage sensor (used X so far this cycle)</label>
                        <input v-model="billSummarySensorCurrent" type="text" class="ha-form-input" list="ha-sensor-datalist" placeholder="sensor.usage_this_cycle" autocomplete="off" />
                      </div>
                      <div class="ha-form-group">
                        <label class="ha-form-label">Avg daily usage sensor</label>
                        <input v-model="billSummarySensorAvg" type="text" class="ha-form-input" list="ha-sensor-datalist" placeholder="sensor.daily_energy_usage" autocomplete="off" />
                      </div>
                      <div class="ha-form-group">
                        <label class="ha-form-label">Bill estimate sensor (min)</label>
                        <input v-model="billSummarySensorEstMin" type="text" class="ha-form-input" list="ha-sensor-datalist" placeholder="sensor.bill_estimate_low" autocomplete="off" />
                      </div>
                      <div class="ha-form-group">
                        <label class="ha-form-label">Bill estimate sensor (max)</label>
                        <input v-model="billSummarySensorEstMax" type="text" class="ha-form-input" list="ha-sensor-datalist" placeholder="sensor.bill_estimate_high" autocomplete="off" />
                      </div>
                      <div class="ha-tts-buttons ha-tts-buttons-sm">
                        <button type="submit" class="ha-button ha-button-primary" :disabled="billSummarySaving">{{ billSummarySaving ? 'Saving...' : 'Save Bill Summary Config' }}</button>
                        <button type="button" class="ha-button ha-button-secondary" :disabled="billSummaryPreviewLoading" @click="handleBillSummaryPreview">{{ billSummaryPreviewLoading ? 'Loading...' : 'Preview Message' }}</button>
                      </div>
                      <div v-if="billSummaryPreview" class="ha-tts-preview-box">{{ billSummaryPreview }}</div>
                    </form>
                  </div>
                </details>

                <div class="ha-tts-buttons">
                  <button type="submit" class="ha-button ha-button-primary" :disabled="ttsSaving">{{ ttsSaving ? 'Saving...' : 'Save TTS Config' }}</button>
                </div>
              </form>
              <div v-if="ttsMessage" :class="['ha-message', ttsMessage.type]">{{ ttsMessage.text }}</div>
            </div>
          </div>
          <SettingsImapTab v-else-if="currentPage === 'imap'" />
        </div>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch, onUnmounted } from 'vue'
import { getApiBase } from '../lib/api-base'
import Dashboard from './Dashboard.vue'
import SettingsCredentialsTab from './settings/SettingsCredentialsTab.vue'
import SettingsAutomatedTab from './settings/SettingsAutomatedTab.vue'
import SettingsMqttTab from './settings/SettingsMqttTab.vue'
import SettingsAppTab from './settings/SettingsAppTab.vue'
import SettingsPayeesPaymentsTab from './settings/SettingsPayeesPaymentsTab.vue'
import SettingsImapTab from './settings/SettingsImapTab.vue'

type Page =
  | 'menu'
  | 'console'
  | 'credentials'
  | 'automated'
  | 'mqtt'
  | 'app-settings'
  | 'payees-payments'
  | 'tts'
  | 'imap'

const currentPage = ref<Page>('menu')
const isUnlocked = ref(false)
const pinDigits = ref<string[]>(['', '', '', ''])
const pinRefs = ref<(HTMLInputElement | null)[]>([])
const passwordError = ref('')

const ttsEnabled = ref(false)
const ttsMediaPlayersList = ref<Array<{ entity_id: string; entity_id_custom: string; volume: number }>>([{ entity_id: '', entity_id_custom: '', volume: 0.7 }])
const ttsMediaPlayersListOptions = ref<string[]>([])
const haSensorEntities = ref<string[]>([])
const ttsEntityStates = ref<Record<string, string>>({})
const ttsEngine = ref('')
const ttsEngineCustom = ref('')
const ttsEntities = ref<string[]>([])
const ttsCache = ref(true)
const ttsPrefix = ref('Message from Con Edison.')
const ttsWaitForIdle = ref(true)
const ttsMsgNewBill = ref('Your new Con Edison bill for {month_range} is now available.')
const ttsMsgPayment = ref('Good news — your payment of {amount} has been received. Your account balance is now {balance}.')
const ttsSaving = ref(false)
const ttsTestLoadingByIdx = ref<Record<number, boolean>>({})
const ttsMessage = ref<{ type: 'success' | 'error'; text: string } | null>(null)
let ttsStatePollTimer: ReturnType<typeof setInterval> | null = null

const ttsLogs = ref<Array<{ ts: string; source: string; message: string; success: boolean; error?: string }>>([])
const ttsQueue = ref<Array<{ source: string; message: string }>>([])

const billSummaryEnabled = ref(false)
const billSummaryDays = ref<number[]>([0, 1, 2, 3, 4, 5, 6])
const billSummaryStartHour12 = ref(8)
const billSummaryStartAmPm = ref<'am' | 'pm'>('am')
const billSummaryEndHour12 = ref(10)
const billSummaryEndAmPm = ref<'am' | 'pm'>('am')
const billSummaryFrequencyHours = ref(1)
const billSummaryMinuteOfHour = ref(0)
const billSummarySensorCurrent = ref('')
const billSummarySensorAvg = ref('')
const billSummarySensorEstMin = ref('')
const billSummarySensorEstMax = ref('')
const billSummarySaving = ref(false)
const billSummaryPreviewLoading = ref(false)
const billSummaryPreview = ref('')
const hour12Options = [12, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
const weekdays = [
  { value: 0, label: 'Mon' },
  { value: 1, label: 'Tue' },
  { value: 2, label: 'Wed' },
  { value: 3, label: 'Thu' },
  { value: 4, label: 'Fri' },
  { value: 5, label: 'Sat' },
  { value: 6, label: 'Sun' },
]

const ttsMediaPlayersListValid = computed(() =>
  ttsMediaPlayersList.value
    .map((p) => (p.entity_id === '__custom__' ? (p.entity_id_custom || '').trim() : (p.entity_id || '').trim()))
    .filter(Boolean)
)

const effectiveTtsEngine = computed(() => {
  if (ttsEngine.value && ttsEngine.value !== '__custom__') return ttsEngine.value
  return ttsEngineCustom.value.trim()
})

function getTtsMpEntityId(p: { entity_id: string; entity_id_custom?: string }): string {
  if (p.entity_id === '__custom__' || (!p.entity_id && p.entity_id_custom)) return (p.entity_id_custom || '').trim()
  return (p.entity_id || '').trim()
}

function addTtsMediaPlayer() {
  ttsMediaPlayersList.value.push({ entity_id: '', entity_id_custom: '', volume: 0.7 })
}

function removeTtsMediaPlayer(idx: number) {
  ttsMediaPlayersList.value.splice(idx, 1)
  if (ttsMediaPlayersList.value.length === 0) {
    ttsMediaPlayersList.value.push({ entity_id: '', entity_id_custom: '', volume: 0.7 })
  }
}

const menuItems = [
  { id: 'console' as Page, icon: '📊', label: 'Console', description: 'View logs and system status' },
  { id: 'credentials' as Page, icon: '🔐', label: 'Credentials', description: 'Con Edison login credentials' },
  { id: 'automated' as Page, icon: '⏰', label: 'Automated Scrape', description: 'Schedule automatic data scraping' },
  { id: 'mqtt' as Page, icon: '📡', label: 'MQTT', description: 'Home Assistant MQTT integration' },
  { id: 'payees-payments' as Page, icon: '👥', label: 'Payees & Payments', description: 'Users, bill split, cards, and payment audit' },
  { id: 'tts' as Page, icon: '🔊', label: 'TTS Alerts', description: 'Media player, TTS messages, and wait-for-idle' },
  { id: 'imap' as Page, icon: '📧', label: 'Email / IMAP', description: 'Email parsing for auto-payment detection' },
  { id: 'app-settings' as Page, icon: '⚙️', label: 'App Settings', description: 'Password and app configuration' },
]

async function verifyPassword(pwd: string) {
  try {
    const res = await fetch(`${getApiBase()}/app-settings/verify-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: pwd }),
    })
    if (res.ok) {
      const data = await res.json()
      if (data.valid) {
        isUnlocked.value = true
        passwordError.value = ''
        pinDigits.value = ['', '', '', '']
        return true
      }
      passwordError.value = 'Incorrect PIN'
      return false
    }
    passwordError.value = 'Connection error'
    return false
  } catch {
    passwordError.value = 'Connection error'
    return false
  }
}

function getPinValue() {
  return pinDigits.value.join('')
}

function onPinInput(index: number, ev: Event) {
  const el = ev.target as HTMLInputElement
  const v = el.value.replace(/\D/g, '').slice(-1)
  pinDigits.value[index] = v
  passwordError.value = ''
  if (v && index < 3) {
    nextTick(() => pinRefs.value[index + 1]?.focus())
  } else if (v && index === 3) {
    nextTick(() => handlePasswordSubmit())
  }
}

function onPinPaste(ev: ClipboardEvent) {
  ev.preventDefault()
  const pasted = (ev.clipboardData?.getData('text') || '').replace(/\D/g, '').slice(0, 4)
  for (let i = 0; i < 4; i++) {
    pinDigits.value[i] = pasted[i] || ''
  }
  passwordError.value = ''
  const nextIdx = Math.min(pasted.length, 3)
  nextTick(() => pinRefs.value[nextIdx]?.focus())
}

function handlePinKeydown(ev: KeyboardEvent, index: number) {
  const target = ev.target as HTMLInputElement
  if (ev.key === 'Backspace' && !target.value && index > 0) {
    ev.preventDefault()
    pinDigits.value[index - 1] = ''
    nextTick(() => pinRefs.value[index - 1]?.focus())
  }
}

async function handlePasswordSubmit() {
  const pwd = getPinValue()
  if (pwd.length !== 4) return
  await verifyPassword(pwd)
}

let ttsLogsPollTimer: ReturnType<typeof setInterval> | null = null

watch(currentPage, (page) => {
  if (page === 'tts') {
    loadTtsConfig()
    ttsStatePollTimer = setInterval(fetchTtsEntityStates, 2000)
    ttsLogsPollTimer = setInterval(fetchTtsLogsAndQueue, 5000)
  } else {
    if (ttsStatePollTimer) {
      clearInterval(ttsStatePollTimer)
      ttsStatePollTimer = null
    }
    if (ttsLogsPollTimer) {
      clearInterval(ttsLogsPollTimer)
      ttsLogsPollTimer = null
    }
  }
})

onUnmounted(() => {
  if (ttsStatePollTimer) clearInterval(ttsStatePollTimer)
  if (ttsLogsPollTimer) clearInterval(ttsLogsPollTimer)
})

function cancelLock() {
  pinDigits.value = ['', '', '', '']
  passwordError.value = ''
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('navigateToLedger'))
  }
}

async function loadTtsConfig() {
  try {
    const [configRes, playersRes, entitiesRes, sensorsRes] = await Promise.all([
      fetch(`${getApiBase()}/tts-config`),
      fetch(`${getApiBase()}/ha-media-players`),
      fetch(`${getApiBase()}/ha-tts-entities`),
      fetch(`${getApiBase()}/ha-sensor-entities`),
    ])
    if (playersRes.ok) {
      const p = await playersRes.json()
      ttsMediaPlayersListOptions.value = p.media_players ?? []
    }
    if (entitiesRes.ok) {
      const e = await entitiesRes.json()
      ttsEntities.value = e.tts_entities ?? []
    }
    if (sensorsRes.ok) {
      const s = await sensorsRes.json()
      haSensorEntities.value = s.entities ?? []
    }
    if (configRes.ok) {
      const d = await configRes.json()
      ttsEnabled.value = d.enabled ?? false
      const mps = d.media_players || []
      const opts = ttsMediaPlayersListOptions.value
      ttsMediaPlayersList.value = mps.length
        ? mps.map((mp: { entity_id?: string; volume?: number }) => {
            const eid = (mp.entity_id || '').trim()
            return {
              entity_id: opts.length && opts.includes(eid) ? eid : (eid ? '__custom__' : ''),
              entity_id_custom: opts.length && opts.includes(eid) ? '' : eid,
              volume: Math.max(0, Math.min(1, float(mp.volume, 0.7))),
            }
          })
        : [{ entity_id: '', entity_id_custom: '', volume: 0.7 }]
      const te = (d.tts_engine ?? '').trim()
      ttsEngineCustom.value = te
      if (ttsEntities.value.includes(te)) {
        ttsEngine.value = te
      } else {
        ttsEngine.value = te ? '__custom__' : ''
      }
      ttsCache.value = d.cache !== false
      ttsPrefix.value = d.prefix ?? 'Message from Con Edison.'
      ttsWaitForIdle.value = d.wait_for_idle ?? true
      if (d.messages?.new_bill) ttsMsgNewBill.value = d.messages.new_bill
      if (d.messages?.payment_received) ttsMsgPayment.value = d.messages.payment_received
    }
    fetchTtsEntityStates()
    loadBillSummaryConfig()
  } catch (e) { console.error(e) }
}

async function fetchTtsLogsAndQueue() {
  try {
    const [logsRes, queueRes] = await Promise.all([
      fetch(`${getApiBase()}/tts-logs`),
      fetch(`${getApiBase()}/tts-queue`),
    ])
    if (logsRes.ok) {
      const d = await logsRes.json()
      ttsLogs.value = (d.logs ?? []).slice().reverse()
    }
    if (queueRes.ok) {
      const d = await queueRes.json()
      ttsQueue.value = d.queue ?? []
    }
  } catch (e) { console.error(e) }
}

function hour24To12(h24: number): { hour: number; ampm: 'am' | 'pm' } {
  if (h24 === 0) return { hour: 12, ampm: 'am' }
  if (h24 < 12) return { hour: h24, ampm: 'am' }
  if (h24 === 12) return { hour: 12, ampm: 'pm' }
  return { hour: h24 - 12, ampm: 'pm' }
}
function hour12To24(h12: number, ampm: string): number {
  if (ampm === 'am') return h12 === 12 ? 0 : h12
  return h12 === 12 ? 12 : h12 + 12
}

function formatTtsLogTs(ts: string): string {
  if (!ts) return ''
  try {
    const d = new Date(ts)
    return d.toLocaleString()
  } catch {
    return ts
  }
}

async function loadBillSummaryConfig() {
  try {
    const res = await fetch(`${getApiBase()}/tts-bill-summary-config`)
    if (res.ok) {
      const d = await res.json()
      billSummaryEnabled.value = d.enabled ?? false
      billSummaryDays.value = Array.isArray(d.days_of_week) ? [...d.days_of_week] : [0, 1, 2, 3, 4, 5, 6]
      const start24 = typeof d.start_hour === 'number' ? Math.max(0, Math.min(23, d.start_hour)) : 8
      const end24 = typeof d.end_hour === 'number' ? Math.max(0, Math.min(23, d.end_hour)) : 10
      const start12 = hour24To12(start24)
      const end12 = hour24To12(end24)
      billSummaryStartHour12.value = start12.hour
      billSummaryStartAmPm.value = start12.ampm
      billSummaryEndHour12.value = end12.hour
      billSummaryEndAmPm.value = end12.ampm
      billSummaryFrequencyHours.value = typeof d.frequency_hours === 'number' ? Math.max(1, d.frequency_hours) : 1
      billSummaryMinuteOfHour.value = typeof d.minute_of_hour === 'number' ? Math.max(0, Math.min(59, d.minute_of_hour)) : 0
      billSummarySensorCurrent.value = (d.sensor_current_usage ?? '').trim()
      billSummarySensorAvg.value = (d.sensor_avg_daily ?? '').trim()
      billSummarySensorEstMin.value = (d.sensor_estimate_min ?? '').trim()
      billSummarySensorEstMax.value = (d.sensor_estimate_max ?? '').trim()
    }
  } catch (e) { console.error(e) }
}

async function handleBillSummarySave() {
  billSummarySaving.value = true
  try {
    const res = await fetch(`${getApiBase()}/tts-bill-summary-config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        enabled: billSummaryEnabled.value,
        days_of_week: billSummaryDays.value,
        start_hour: hour12To24(billSummaryStartHour12.value, billSummaryStartAmPm.value),
        end_hour: hour12To24(billSummaryEndHour12.value, billSummaryEndAmPm.value),
        frequency_hours: Math.max(1, Math.min(24, billSummaryFrequencyHours.value)),
        minute_of_hour: Math.max(0, Math.min(59, billSummaryMinuteOfHour.value)),
        sensor_current_usage: billSummarySensorCurrent.value.trim(),
        sensor_avg_daily: billSummarySensorAvg.value.trim(),
        sensor_estimate_min: billSummarySensorEstMin.value.trim(),
        sensor_estimate_max: billSummarySensorEstMax.value.trim(),
      }),
    })
    if (res.ok) ttsMessage.value = { type: 'success', text: 'Bill summary config saved.' }
    else ttsMessage.value = { type: 'error', text: 'Failed to save.' }
  } catch {
    ttsMessage.value = { type: 'error', text: 'Failed to connect' }
  } finally {
    billSummarySaving.value = false
  }
}

async function handleBillSummaryPreview() {
  billSummaryPreviewLoading.value = true
  billSummaryPreview.value = ''
  try {
    const res = await fetch(`${getApiBase()}/tts/bill-summary/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sensor_current_usage: billSummarySensorCurrent.value.trim(),
        sensor_avg_daily: billSummarySensorAvg.value.trim(),
        sensor_estimate_min: billSummarySensorEstMin.value.trim(),
        sensor_estimate_max: billSummarySensorEstMax.value.trim(),
      }),
    })
    const d = await res.json().catch(() => ({}))
    billSummaryPreview.value = d.message ?? '(empty)'
  } catch {
    billSummaryPreview.value = 'Failed to load preview'
  } finally {
    billSummaryPreviewLoading.value = false
  }
}

function float(v: unknown, def: number): number {
  const n = Number(v)
  return isNaN(n) ? def : n
}

async function fetchTtsEntityStates() {
  const ids = ttsMediaPlayersListValid.value
  if (!ids.length) {
    ttsEntityStates.value = {}
    return
  }
  try {
    const res = await fetch(`${getApiBase()}/ha-entity-states?entity_ids=${encodeURIComponent(ids.join(','))}`)
    if (res.ok) {
      ttsEntityStates.value = await res.json()
    }
  } catch { /* ignore */ }
}

async function handleTtsSave() {
  ttsSaving.value = true
  ttsMessage.value = null
  try {
    const media_players = ttsMediaPlayersList.value
      .filter((p) => getTtsMpEntityId(p))
      .map((p) => ({ entity_id: getTtsMpEntityId(p), volume: p.volume ?? 0.7 }))
    const res = await fetch(`${getApiBase()}/tts-config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        enabled: ttsEnabled.value,
        media_players,
        tts_engine: effectiveTtsEngine.value,
        cache: ttsCache.value,
        language: 'en',
        prefix: ttsPrefix.value,
        wait_for_idle: ttsWaitForIdle.value,
        messages: { new_bill: ttsMsgNewBill.value, payment_received: ttsMsgPayment.value },
      }),
    })
    const data = await res.json().catch(() => ({}))
    if (res.ok) {
      ttsMessage.value = { type: 'success', text: 'TTS config saved' }
    } else {
      ttsMessage.value = { type: 'error', text: data.detail || 'Failed' }
    }
  } catch {
    ttsMessage.value = { type: 'error', text: 'Failed to connect' }
  } finally {
    ttsSaving.value = false
  }
}

async function handleTtsTestForPlayer(idx: number) {
  const p = ttsMediaPlayersList.value[idx]
  const entityId = getTtsMpEntityId(p)
  if (!ttsEnabled.value || !entityId || !effectiveTtsEngine.value) return
  ttsTestLoadingByIdx.value = { ...ttsTestLoadingByIdx.value, [idx]: true }
  ttsMessage.value = null
  try {
    const res = await fetch(`${getApiBase()}/tts/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entity_id: entityId, volume: p.volume ?? 0.7 }),
    })
    const data = await res.json().catch(() => ({}))
    ttsMessage.value = res.ok ? { type: 'success', text: data.message || 'Sent' } : { type: 'error', text: data.detail || 'Failed' }
    if (res.ok) {
      fetchTtsEntityStates()
      fetchTtsLogsAndQueue()
      const burst = setInterval(fetchTtsEntityStates, 1000)
      setTimeout(() => clearInterval(burst), 15000)
    }
  } catch {
    ttsMessage.value = { type: 'error', text: 'Failed' }
  } finally {
    ttsTestLoadingByIdx.value = { ...ttsTestLoadingByIdx.value, [idx]: false }
  }
}
</script>

<style scoped>
.ha-lock-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.ha-lock-card { max-width: 360px; margin: 1rem; }
.ha-pin-row {
  display: flex;
  gap: 0.75rem;
  justify-content: center;
  margin: 1.25rem 0;
}
.ha-pin-input {
  width: 56px;
  height: 56px;
  font-size: 1.5rem;
  font-weight: 600;
  text-align: center;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  background: #fafafa;
  color: #212121;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.ha-pin-input:focus {
  outline: none;
  border-color: #03a9f4;
  box-shadow: 0 0 0 3px rgba(3, 169, 244, 0.2);
}
.ha-pin-input.error {
  border-color: #d32f2f;
}
.ha-pin-input.error:focus {
  box-shadow: 0 0 0 3px rgba(211, 47, 47, 0.2);
}
.ha-pin-hint {
  font-size: 0.85rem;
  color: #666;
  margin-top: 1rem;
  line-height: 1.4;
}
.ha-password-error { color: #d32f2f; font-size: 0.85rem; margin-top: 0.5rem; }
.ha-form-actions { display: flex; gap: 0.5rem; }
.ha-button-gray { flex: 1; background: #757575 !important; color: white; }
.ha-form-actions .ha-button-primary { flex: 1; }
.ha-settings-menu { padding: 0.5rem; }
.ha-settings-title { margin: 0 0 1rem 0; font-size: 1.3rem; font-weight: 600; }
.ha-menu-list { display: flex; flex-direction: column; gap: 0.5rem; }
.ha-menu-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  text-align: left;
  transition: all 0.15s ease;
}
.ha-menu-item:hover { background: #f5f5f5; border-color: #03a9f4; }
.ha-menu-icon { font-size: 1.5rem; }
.ha-menu-text { flex: 1; }
.ha-menu-label { font-weight: 600; font-size: 1rem; }
.ha-menu-desc { font-size: 0.8rem; color: #666; }
.ha-menu-arrow { margin-left: auto; color: #999; }
.ha-settings-page {
  display: block;
  min-height: 0;
}
.ha-back-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: none;
  border: none;
  color: #03a9f4;
  cursor: pointer;
  padding: 0.5rem 0;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.ha-tts-card { min-height: 200px; }
.ha-tts-intro { margin-bottom: 1.25rem; color: #555; font-size: 0.95rem; }
.ha-tts-form { display: flex; flex-direction: column; gap: 1rem; }
.ha-form-input-mt { margin-top: 0.5rem; }
.ha-check-label { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; }
.ha-check-label input { width: 18px; height: 18px; }
.ha-tts-details {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
  background: #fafafa;
}
.ha-tts-details summary {
  padding: 0.75rem 1rem;
  font-weight: 600;
  cursor: pointer;
  user-select: none;
}
.ha-tts-details[open] summary { border-bottom: 1px solid #e0e0e0; }
.ha-tts-details-content { padding: 1rem; }
.ha-tts-mp-card {
  padding: 1rem;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  margin-bottom: 0.75rem;
}
.ha-tts-mp-card:last-of-type { margin-bottom: 0; }
.ha-tts-mp-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}
.ha-tts-mp-status {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  text-transform: uppercase;
}
.ha-tts-mp-status.state-idle { background: #e8f5e9; color: #2e7d32; }
.ha-tts-mp-status.state-playing,
.ha-tts-mp-status.state-streaming { background: #e3f2fd; color: #1565c0; }
.ha-tts-mp-status.state-paused { background: #fff3e0; color: #e65100; }
.ha-tts-mp-status.state-unavailable,
.ha-tts-mp-status.state-off,
.ha-tts-mp-status.state-unknown { background: #f5f5f5; color: #757575; }
.ha-btn-sm { padding: 0.25rem 0.5rem; font-size: 1rem; line-height: 1; border: none; border-radius: 4px; cursor: pointer; }
.ha-btn-red { background: #f44336; color: white; }
.ha-btn-red:hover { background: #d32f2f; }
.ha-button-secondary { background: #9e9e9e !important; color: white !important; }
.ha-volume-slider {
  width: 100%;
  height: 8px;
  -webkit-appearance: none;
  appearance: none;
  background: #e0e0e0;
  border-radius: 4px;
}
.ha-volume-slider::-webkit-slider-thumb { -webkit-appearance: none; width: 18px; height: 18px; background: #ff9800; border-radius: 50%; cursor: pointer; }
.ha-volume-slider::-moz-range-thumb { width: 18px; height: 18px; background: #ff9800; border-radius: 50%; cursor: pointer; border: none; }
.ha-tts-buttons { display: flex; flex-wrap: wrap; gap: 0.75rem; margin-top: 0.5rem; }
.ha-tts-test-hint { font-size: 0.8rem; color: #666; margin-top: 0.75rem; }
.ha-btn-test { background: #ff9800 !important; color: white !important; }
.ha-btn-test:disabled { opacity: 0.6; cursor: not-allowed; }
.ha-btn-test-sm { font-size: 0.85rem; padding: 0.4rem 0.75rem; margin-top: 0.5rem; }
.ha-message { margin-top: 1rem; padding: 0.75rem; border-radius: 4px; }
.ha-message.success { background: #e8f5e9; color: #2e7d32; }
.ha-message.error { background: #ffebee; color: #c62828; }

/* TTS Logs */
.ha-tts-queue-section { margin-bottom: 1rem; }
.ha-tts-logs-section { margin-top: 0.5rem; }
.ha-tts-section-label { font-weight: 600; font-size: 0.85rem; margin-bottom: 0.5rem; color: #555; }
.ha-tts-log-entry {
  font-size: 0.8rem;
  padding: 0.4rem 0.5rem;
  border-radius: 4px;
  margin-bottom: 0.25rem;
  background: #f5f5f5;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}
.ha-tts-log-entry.success { background: #e8f5e9; }
.ha-tts-log-entry.error { background: #ffebee; }
.ha-tts-queue-entry { background: #e3f2fd; }
.ha-tts-log-ts { color: #666; font-family: monospace; font-size: 0.75rem; }
.ha-tts-log-source { font-weight: 600; min-width: 8ch; }
.ha-tts-log-status { font-weight: bold; }
.ha-tts-log-msg { flex: 1; min-width: 0; }
.ha-tts-log-error { color: #c62828; font-size: 0.75rem; width: 100%; }
.ha-tts-logs-empty { font-size: 0.9rem; color: #999; padding: 0.5rem 0; }

/* Bill Summary */
.ha-check-row { display: flex; flex-wrap: wrap; gap: 0.5rem 1rem; }
.ha-check-inline { display: flex; align-items: center; gap: 0.35rem; cursor: pointer; font-size: 0.9rem; }
.ha-check-inline input { width: 16px; height: 16px; }
.ha-form-row { display: flex; gap: 1rem; flex-wrap: wrap; }
.ha-time-row { display: flex; gap: 0.5rem; }
.ha-time-row select { min-width: 4rem; }
.ha-form-row > div { flex: 1; min-width: 120px; }
.ha-tts-buttons-sm { margin-top: 0.5rem; }
.ha-tts-preview-box {
  margin-top: 1rem;
  padding: 1rem;
  background: #f5f5f5;
  border-radius: 8px;
  font-size: 0.9rem;
  line-height: 1.5;
  white-space: pre-wrap;
  max-height: 200px;
  overflow-y: auto;
}
</style>
