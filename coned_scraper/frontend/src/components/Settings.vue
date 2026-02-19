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
              <label for="settings-password" class="ha-form-label">Enter Settings Password</label>
              <input
                id="settings-password"
                v-model="passwordInput"
                type="password"
                class="ha-form-input"
                placeholder="Default: 0000"
                required
              />
              <div v-if="passwordError" class="ha-password-error">{{ passwordError }}</div>
              <div class="info-text">Default password is <strong>0000</strong>. Change it in App Settings after unlocking.</div>
            </div>
            <div class="ha-form-actions">
              <button type="button" class="ha-button ha-button-gray" @click="cancelLock">Cancel</button>
              <button type="submit" class="ha-button ha-button-primary">Unlock Settings</button>
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

        <Dashboard v-if="currentPage === 'console'" />
        <SettingsCredentialsTab v-else-if="currentPage === 'credentials'" />
        <SettingsAutomatedTab v-else-if="currentPage === 'automated'" />
        <SettingsWebhooksTab v-else-if="currentPage === 'webhooks'" />
        <SettingsMqttTab v-else-if="currentPage === 'mqtt'" />
        <SettingsAppTab v-else-if="currentPage === 'app-settings'" />
        <SettingsPayeesTab v-else-if="currentPage === 'payees'" />
        <SettingsPaymentsTab v-else-if="currentPage === 'payments'" />
        <SettingsImapTab v-else-if="currentPage === 'imap'" />
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { getApiBase } from '../lib/api-base'
import Dashboard from './Dashboard.vue'
import SettingsCredentialsTab from './settings/SettingsCredentialsTab.vue'
import SettingsAutomatedTab from './settings/SettingsAutomatedTab.vue'
import SettingsWebhooksTab from './settings/SettingsWebhooksTab.vue'
import SettingsMqttTab from './settings/SettingsMqttTab.vue'
import SettingsAppTab from './settings/SettingsAppTab.vue'
import SettingsPayeesTab from './settings/SettingsPayeesTab.vue'
import SettingsPaymentsTab from './settings/SettingsPaymentsTab.vue'
import SettingsImapTab from './settings/SettingsImapTab.vue'

type Page =
  | 'menu'
  | 'console'
  | 'credentials'
  | 'automated'
  | 'webhooks'
  | 'mqtt'
  | 'app-settings'
  | 'payees'
  | 'payments'
  | 'imap'

const currentPage = ref<Page>('menu')
const isUnlocked = ref(false)
const passwordInput = ref('')
const passwordError = ref('')

const menuItems = [
  { id: 'console' as Page, icon: '📊', label: 'Console', description: 'View logs and system status' },
  { id: 'credentials' as Page, icon: '🔐', label: 'Credentials', description: 'Con Edison login credentials' },
  { id: 'automated' as Page, icon: '⏰', label: 'Automated Scrape', description: 'Schedule automatic data scraping' },
  { id: 'webhooks' as Page, icon: '🔗', label: 'Webhooks', description: 'Configure webhook notifications' },
  { id: 'mqtt' as Page, icon: '📡', label: 'MQTT', description: 'Home Assistant MQTT integration' },
  { id: 'payees' as Page, icon: '👥', label: 'Payees', description: 'Manage users and responsibility %' },
  { id: 'payments' as Page, icon: '💳', label: 'Payments', description: 'Audit and manage payments' },
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
        return true
      }
      passwordError.value = 'Incorrect password'
      return false
    }
    passwordError.value = 'Failed to verify password'
    return false
  } catch {
    passwordError.value = 'Connection error'
    return false
  }
}

async function handlePasswordSubmit() {
  await verifyPassword(passwordInput.value)
}

function cancelLock() {
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
.ha-lock-card { max-width: 400px; margin: 1rem; }
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
</style>
