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

      <!-- Console -->
      <template v-else>
        <button type="button" class="ha-back-btn" @click="currentPage = 'menu'">← Back to Settings</button>
        <div class="ha-settings-tab-area">
        <Dashboard v-if="currentPage === 'console'" />
        <SettingsCredentialsTab v-else-if="currentPage === 'credentials'" />
        <SettingsAutomatedTab v-else-if="currentPage === 'automated'" />
        <SettingsMqttTab v-else-if="currentPage === 'mqtt'" />
        <SettingsAppTab v-else-if="currentPage === 'app-settings'" />
        <SettingsPayeesPaymentsTab v-else-if="currentPage === 'payees-payments'" />
        <SettingsTtsTab v-else-if="currentPage === 'tts'" />
        <SettingsImapTab v-else-if="currentPage === 'imap'" />
        </div>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { getApiBase } from '../lib/api-base'
import Dashboard from './Dashboard.vue'
import SettingsCredentialsTab from './settings/SettingsCredentialsTab.vue'
import SettingsAutomatedTab from './settings/SettingsAutomatedTab.vue'
import SettingsMqttTab from './settings/SettingsMqttTab.vue'
import SettingsAppTab from './settings/SettingsAppTab.vue'
import SettingsPayeesPaymentsTab from './settings/SettingsPayeesPaymentsTab.vue'
import SettingsTtsTab from './settings/SettingsTtsTab.vue'
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

function cancelLock() {
  pinDigits.value = ['', '', '', '']
  passwordError.value = ''
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('navigateToLedger'))
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
.ha-settings-tab-area {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
</style>
