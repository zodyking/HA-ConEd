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
          <!-- Normal PIN Entry -->
          <form v-if="!showAdminReset" @submit.prevent="handlePasswordSubmit">
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
            </div>
            <div class="ha-form-actions">
              <button type="button" class="ha-button ha-button-gray" @click="cancelLock">Cancel</button>
              <button type="submit" class="ha-button ha-button-primary" :disabled="pinDigits.some(d => !d)">Unlock Settings</button>
            </div>
          </form>

          <!-- Admin Reset Link (only for HA addon users) -->
          <div v-if="isHaAdmin && !showAdminReset" class="ha-admin-reset-link">
            <button type="button" class="ha-link-btn" @click="showAdminReset = true">
              🔑 Forgot PIN? Reset
            </button>
          </div>

          <!-- Admin Password Reset Form -->
          <div v-if="showAdminReset" class="ha-admin-reset-form">
            <h3 class="ha-reset-title">🔑 Reset PIN</h3>
            <p class="ha-reset-desc">Set a new 4-digit PIN for settings access.</p>
            <div class="ha-form-group">
              <label class="ha-form-label">New 4-digit PIN</label>
              <div class="ha-pin-row">
                <input
                  v-for="(_, i) in 4"
                  :key="'new-' + i"
                  :ref="el => { if (el) newPinRefs[i] = el as HTMLInputElement }"
                  v-model="newPinDigits[i]"
                  type="password"
                  inputmode="numeric"
                  maxlength="1"
                  autocomplete="new-password"
                  class="ha-pin-input"
                  :class="{ error: adminResetError }"
                  @input="onNewPinInput(i, $event)"
                  @keydown="handleNewPinKeydown($event, i)"
                />
              </div>
            </div>
            <div class="ha-form-group">
              <label class="ha-form-label">Confirm PIN</label>
              <div class="ha-pin-row">
                <input
                  v-for="(_, i) in 4"
                  :key="'confirm-' + i"
                  :ref="el => { if (el) confirmPinRefs[i] = el as HTMLInputElement }"
                  v-model="confirmPinDigits[i]"
                  type="password"
                  inputmode="numeric"
                  maxlength="1"
                  autocomplete="new-password"
                  class="ha-pin-input"
                  :class="{ error: adminResetError }"
                  @input="onConfirmPinInput(i, $event)"
                  @keydown="handleConfirmPinKeydown($event, i)"
                />
              </div>
            </div>
            <div v-if="adminResetError" class="ha-password-error">{{ adminResetError }}</div>
            <div v-if="adminResetSuccess" class="ha-success-message">{{ adminResetSuccess }}</div>
            <div class="ha-form-actions">
              <button type="button" class="ha-button ha-button-gray" @click="cancelAdminReset">Back</button>
              <button
                type="button"
                class="ha-button ha-button-primary"
                :disabled="adminResetLoading || newPinDigits.some(d => !d) || confirmPinDigits.some(d => !d)"
                @click="handleAdminReset"
              >
                {{ adminResetLoading ? 'Resetting...' : 'Reset PIN' }}
              </button>
            </div>
          </div>
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

      <!-- Subpages -->
      <div v-else class="ha-settings-subpage">
        <button type="button" class="ha-back-btn" @click="currentPage = 'menu'">← Back to Settings</button>
        <Dashboard v-if="currentPage === 'console'" />
        <SettingsCredentialsTab v-else-if="currentPage === 'credentials'" />
        <SettingsAutomatedTab v-else-if="currentPage === 'automated'" />
        <SettingsMqttTab v-else-if="currentPage === 'mqtt'" />
        <SettingsBillTab v-else-if="currentPage === 'bill-settings'" />
        <SettingsAppTab v-else-if="currentPage === 'app-settings'" />
        <SettingsPayeesPaymentsTab v-else-if="currentPage === 'payees-payments'" />
        <SettingsTtsTab v-else-if="currentPage === 'tts'" />
        <SettingsImapTab v-else-if="currentPage === 'imap'" />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { getApiBase } from '../lib/api-base'
import Dashboard from './Dashboard.vue'
import SettingsCredentialsTab from './settings/SettingsCredentialsTab.vue'
import SettingsAutomatedTab from './settings/SettingsAutomatedTab.vue'
import SettingsMqttTab from './settings/SettingsMqttTab.vue'
import SettingsBillTab from './settings/SettingsBillTab.vue'
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
  | 'bill-settings'
  | 'app-settings'
  | 'payees-payments'
  | 'tts'
  | 'imap'

const currentPage = ref<Page>('menu')
const isUnlocked = ref(false)
const pinDigits = ref<string[]>(['', '', '', ''])
const pinRefs = ref<(HTMLInputElement | null)[]>([])
const passwordError = ref('')

// Admin reset state
const isHaAdmin = ref(false)
const showAdminReset = ref(false)
const newPinDigits = ref<string[]>(['', '', '', ''])
const confirmPinDigits = ref<string[]>(['', '', '', ''])
const newPinRefs = ref<(HTMLInputElement | null)[]>([])
const confirmPinRefs = ref<(HTMLInputElement | null)[]>([])
const adminResetError = ref('')
const adminResetSuccess = ref('')
const adminResetLoading = ref(false)

const menuItems = [
  { id: 'console' as Page, icon: '📊', label: 'Console', description: 'View logs and system status' },
  { id: 'credentials' as Page, icon: '🔐', label: 'Credentials & Meter', description: 'Con Edison login and meter tracking' },
  { id: 'automated' as Page, icon: '⏰', label: 'Automated Scrape', description: 'Schedule automatic data scraping' },
  { id: 'mqtt' as Page, icon: '📡', label: 'MQTT', description: 'Home Assistant MQTT integration' },
  { id: 'bill-settings' as Page, icon: '📄', label: 'Bill Settings', description: 'Bill PDFs, auto-download, re-parse' },
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
  showAdminReset.value = false
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('navigateToLedger'))
  }
}

// Admin reset functions
async function checkHaAdmin() {
  try {
    const res = await fetch(`${getApiBase()}/app-settings/check-ha-admin`)
    if (res.ok) {
      const data = await res.json()
      isHaAdmin.value = data.is_admin === true
    }
  } catch {
    isHaAdmin.value = false
  }
}

function onNewPinInput(index: number, ev: Event) {
  const el = ev.target as HTMLInputElement
  const v = el.value.replace(/\D/g, '').slice(-1)
  newPinDigits.value[index] = v
  adminResetError.value = ''
  adminResetSuccess.value = ''
  if (v && index < 3) {
    nextTick(() => newPinRefs.value[index + 1]?.focus())
  } else if (v && index === 3) {
    nextTick(() => confirmPinRefs.value[0]?.focus())
  }
}

function handleNewPinKeydown(ev: KeyboardEvent, index: number) {
  const target = ev.target as HTMLInputElement
  if (ev.key === 'Backspace' && !target.value && index > 0) {
    ev.preventDefault()
    newPinDigits.value[index - 1] = ''
    nextTick(() => newPinRefs.value[index - 1]?.focus())
  }
}

function onConfirmPinInput(index: number, ev: Event) {
  const el = ev.target as HTMLInputElement
  const v = el.value.replace(/\D/g, '').slice(-1)
  confirmPinDigits.value[index] = v
  adminResetError.value = ''
  adminResetSuccess.value = ''
  if (v && index < 3) {
    nextTick(() => confirmPinRefs.value[index + 1]?.focus())
  }
}

function handleConfirmPinKeydown(ev: KeyboardEvent, index: number) {
  const target = ev.target as HTMLInputElement
  if (ev.key === 'Backspace' && !target.value && index > 0) {
    ev.preventDefault()
    confirmPinDigits.value[index - 1] = ''
    nextTick(() => confirmPinRefs.value[index - 1]?.focus())
  }
}

function cancelAdminReset() {
  showAdminReset.value = false
  newPinDigits.value = ['', '', '', '']
  confirmPinDigits.value = ['', '', '', '']
  adminResetError.value = ''
  adminResetSuccess.value = ''
}

async function handleAdminReset() {
  const newPin = newPinDigits.value.join('')
  const confirmPin = confirmPinDigits.value.join('')

  if (newPin.length !== 4) {
    adminResetError.value = 'PIN must be 4 digits'
    return
  }
  if (newPin !== confirmPin) {
    adminResetError.value = 'PINs do not match'
    return
  }

  adminResetLoading.value = true
  adminResetError.value = ''
  adminResetSuccess.value = ''

  try {
    const res = await fetch(`${getApiBase()}/app-settings/ha-admin-reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ new_password: newPin }),
    })
    const data = await res.json().catch(() => ({}))
    if (res.ok) {
      adminResetSuccess.value = 'PIN reset successfully! You can now unlock with the new PIN.'
      newPinDigits.value = ['', '', '', '']
      confirmPinDigits.value = ['', '', '', '']
      setTimeout(() => {
        showAdminReset.value = false
        adminResetSuccess.value = ''
      }, 2000)
    } else {
      adminResetError.value = data.detail || 'Failed to reset PIN'
    }
  } catch {
    adminResetError.value = 'Connection error'
  } finally {
    adminResetLoading.value = false
  }
}

onMounted(() => {
  checkHaAdmin()
})
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
.ha-settings-subpage {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.ha-settings-subpage > .ha-card {
  flex-shrink: 0;
}

/* Admin Reset Styles */
.ha-admin-reset-link {
  margin-top: 1rem;
  text-align: center;
  border-top: 1px solid #e0e0e0;
  padding-top: 1rem;
}
.ha-link-btn {
  background: none;
  border: none;
  color: #ff9800;
  cursor: pointer;
  font-size: 0.85rem;
  text-decoration: underline;
  padding: 0.5rem;
}
.ha-link-btn:hover {
  color: #e65100;
}
.ha-admin-reset-form {
  padding: 0.5rem 0;
}
.ha-reset-title {
  margin: 0 0 0.5rem 0;
  font-size: 1rem;
  font-weight: 600;
  color: #e65100;
}
.ha-reset-desc {
  font-size: 0.85rem;
  color: #666;
  margin-bottom: 1rem;
}
.ha-success-message {
  color: #2e7d32;
  font-size: 0.85rem;
  margin-top: 0.5rem;
  background: #e8f5e9;
  padding: 0.5rem;
  border-radius: 4px;
}
</style>
