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
              <p class="ha-tts-intro">Configure text-to-speech for Con Edison events. Messages use (prefix), (message).</p>
              <form @submit.prevent="handleTtsSave" class="ha-tts-form">
                <div class="ha-form-group">
                  <label class="ha-check-label">
                    <input v-model="ttsEnabled" type="checkbox" />
                    <span>Enable TTS Alerts</span>
                  </label>
                </div>
                <div class="ha-form-group">
                  <label for="tts-media-player" class="ha-form-label">Media Player</label>
                  <select
                    v-if="ttsMediaPlayers.length"
                    id="tts-media-player"
                    v-model="ttsMediaPlayerSelect"
                    class="ha-form-input"
                    @change="onTtsMediaPlayerChange"
                  >
                    <option value="">Select a media player...</option>
                    <option v-for="p in ttsMediaPlayers" :key="p" :value="p">{{ p }}</option>
                    <option value="__custom__">Other (enter manually)</option>
                  </select>
                  <input
                    v-else
                    id="tts-media-player"
                    v-model="ttsMediaPlayer"
                    type="text"
                    class="ha-form-input"
                    placeholder="media_player.living_room"
                  />
                  <input
                    v-if="ttsMediaPlayers.length && ttsMediaPlayerSelect === '__custom__'"
                    v-model="ttsMediaPlayer"
                    type="text"
                    class="ha-form-input ha-form-input-mt"
                    placeholder="media_player.living_room"
                  />
                </div>
                <div class="ha-form-group">
                  <label for="tts-engine" class="ha-form-label">TTS Engine (Target)</label>
                  <select
                    v-if="ttsEntities.length"
                    id="tts-engine"
                    v-model="ttsEngine"
                    class="ha-form-input"
                  >
                    <option value="">Select TTS engine...</option>
                    <option v-for="e in ttsEntities" :key="e" :value="e">{{ e }}</option>
                    <option value="__custom__">Other (enter manually)</option>
                  </select>
                  <input
                    v-if="ttsEntities.length && ttsEngine === '__custom__'"
                    v-model="ttsEngineCustom"
                    type="text"
                    class="ha-form-input ha-form-input-mt"
                    placeholder="tts.google_translate_en_com"
                  />
                  <input
                    v-else-if="!ttsEntities.length"
                    id="tts-engine"
                    v-model="ttsEngineCustom"
                    type="text"
                    class="ha-form-input"
                    placeholder="tts.google_translate_en_com"
                  />
                  <div class="info-text">Home Assistant TTS entity (e.g. tts.google_translate_en_com)</div>
                </div>
                <div class="ha-form-group">
                  <label class="ha-check-label">
                    <input v-model="ttsCache" type="checkbox" />
                    <span>Cache TTS</span>
                  </label>
                  <div class="info-text">Cache generated audio for reuse</div>
                </div>
                <div class="ha-form-group">
                  <label for="tts-prefix" class="ha-form-label">TTS Prefix</label>
                  <input id="tts-prefix" v-model="ttsPrefix" type="text" class="ha-form-input" placeholder="Message from Con Edison." />
                </div>
                <div class="ha-form-group">
                  <label class="ha-check-label">
                    <input v-model="ttsWaitForIdle" type="checkbox" />
                    <span>Wait for media player idle</span>
                  </label>
                </div>

                <div class="ha-tts-messages-section">
                  <h4 class="ha-tts-section-title">TTS Message Templates</h4>
                  <p class="ha-tts-section-desc">Use <code>{placeholder}</code> for variables (e.g. <code>{amount}</code>, <code>{balance}</code>, <code>{month_range}</code>).</p>
                  <div class="ha-form-group">
                    <label for="tts-msg-new-bill" class="ha-form-label">New Bill Message</label>
                    <input id="tts-msg-new-bill" v-model="ttsMsgNewBill" type="text" class="ha-form-input" placeholder="Your new Con Edison bill for {month_range} is now available." />
                  </div>
                  <div class="ha-form-group">
                    <label for="tts-msg-payment" class="ha-form-label">Payment Received Message</label>
                    <input id="tts-msg-payment" v-model="ttsMsgPayment" type="text" class="ha-form-input" placeholder="Your payment of {amount} has been received. Balance is now {balance}." />
                  </div>
                </div>

                <div class="ha-tts-buttons">
                  <button type="submit" class="ha-button ha-button-primary" :disabled="ttsSaving">{{ ttsSaving ? 'Saving...' : 'Save TTS Config' }}</button>
                  <button type="button" class="ha-button ha-btn-test" :disabled="!ttsEnabled || !effectiveTtsMediaPlayer || !effectiveTtsEngine || ttsTestLoading" @click="handleTtsTest">{{ ttsTestLoading ? 'Sending...' : 'Test TTS' }}</button>
                </div>
                <p class="ha-tts-test-hint">Test TTS plays: <strong>Con Edison.</strong></p>
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
import { ref, computed, nextTick, watch } from 'vue'
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
const ttsMediaPlayer = ref('')
const ttsMediaPlayerSelect = ref('')
const ttsMediaPlayers = ref<string[]>([])
const ttsEngine = ref('')
const ttsEngineCustom = ref('')
const ttsEntities = ref<string[]>([])
const ttsCache = ref(true)
const ttsPrefix = ref('Message from Con Edison.')
const ttsWaitForIdle = ref(true)
const ttsMsgNewBill = ref('Your new Con Edison bill for {month_range} is now available.')
const ttsMsgPayment = ref('Good news — your payment of {amount} has been received. Your account balance is now {balance}.')
const ttsSaving = ref(false)
const ttsTestLoading = ref(false)
const ttsMessage = ref<{ type: 'success' | 'error'; text: string } | null>(null)

const effectiveTtsMediaPlayer = computed(() => {
  if (ttsMediaPlayerSelect.value === '__custom__') return ttsMediaPlayer.value.trim()
  if (ttsMediaPlayerSelect.value) return ttsMediaPlayerSelect.value
  return ttsMediaPlayer.value.trim()
})

const effectiveTtsEngine = computed(() => {
  if (ttsEngine.value && ttsEngine.value !== '__custom__') return ttsEngine.value
  return ttsEngineCustom.value.trim()
})

function onTtsMediaPlayerChange() {
  if (ttsMediaPlayerSelect.value !== '__custom__') {
    ttsMediaPlayer.value = ttsMediaPlayerSelect.value
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

watch(currentPage, (page) => {
  if (page === 'tts') loadTtsConfig()
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
    const [configRes, playersRes, entitiesRes] = await Promise.all([
      fetch(`${getApiBase()}/tts-config`),
      fetch(`${getApiBase()}/ha-media-players`),
      fetch(`${getApiBase()}/ha-tts-entities`),
    ])
    if (playersRes.ok) {
      const p = await playersRes.json()
      ttsMediaPlayers.value = p.media_players ?? []
    }
    if (entitiesRes.ok) {
      const e = await entitiesRes.json()
      ttsEntities.value = e.tts_entities ?? []
    }
    if (configRes.ok) {
      const d = await configRes.json()
      ttsEnabled.value = d.enabled ?? false
      const mp = (d.media_player ?? '').trim()
      ttsMediaPlayer.value = mp
      if (ttsMediaPlayers.value.includes(mp)) {
        ttsMediaPlayerSelect.value = mp
      } else {
        ttsMediaPlayerSelect.value = mp ? '__custom__' : ''
      }
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
  } catch (e) { console.error(e) }
}

async function handleTtsSave() {
  ttsSaving.value = true
  ttsMessage.value = null
  try {
    const res = await fetch(`${getApiBase()}/tts-config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        enabled: ttsEnabled.value,
        media_player: effectiveTtsMediaPlayer.value,
        tts_engine: effectiveTtsEngine.value,
        cache: ttsCache.value,
        volume: 0.7,
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

async function handleTtsTest() {
  if (!ttsEnabled.value || !ttsMediaPlayer.value.trim()) return
  ttsTestLoading.value = true
  ttsMessage.value = null
  try {
    const res = await fetch(`${getApiBase()}/tts/test`, { method: 'POST' })
    const data = await res.json().catch(() => ({}))
    ttsMessage.value = res.ok ? { type: 'success', text: data.message || 'Sent' } : { type: 'error', text: data.detail || 'Failed' }
  } catch {
    ttsMessage.value = { type: 'error', text: 'Failed' }
  } finally {
    ttsTestLoading.value = false
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
.ha-tts-messages-section {
  margin-top: 1rem;
  padding-top: 1.25rem;
  border-top: 1px solid #e0e0e0;
}
.ha-tts-section-title { font-size: 1rem; font-weight: 600; margin: 0 0 0.5rem 0; color: #333; }
.ha-tts-section-desc { font-size: 0.85rem; color: #666; margin-bottom: 1rem; }
.ha-tts-section-desc code { background: #f0f0f0; padding: 0.1em 0.3em; border-radius: 3px; font-size: 0.9em; }
.ha-tts-buttons { display: flex; flex-wrap: wrap; gap: 0.75rem; margin-top: 0.5rem; }
.ha-tts-test-hint { font-size: 0.8rem; color: #666; margin-top: 0.75rem; }
.ha-btn-test { background: #ff9800 !important; color: white !important; }
.ha-btn-test:disabled { opacity: 0.6; cursor: not-allowed; }
.ha-message { margin-top: 1rem; padding: 0.75rem; border-radius: 4px; }
.ha-message.success { background: #e8f5e9; color: #2e7d32; }
.ha-message.error { background: #ffebee; color: #c62828; }
</style>
