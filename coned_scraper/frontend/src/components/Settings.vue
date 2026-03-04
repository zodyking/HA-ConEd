<template>
  <div class="ha-settings">
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
        <SettingsBillTab v-else-if="currentPage === 'bill-settings'" />
        <SettingsAppTab v-else-if="currentPage === 'app-settings'" />
        <SettingsPayeesPaymentsTab v-else-if="currentPage === 'payees-payments'" />
        <SettingsTtsTab v-else-if="currentPage === 'tts'" />
        <SettingsNotificationsTab v-else-if="currentPage === 'notifications'" />
        <SettingsImapTab v-else-if="currentPage === 'imap'" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Dashboard from './Dashboard.vue'
import SettingsCredentialsTab from './settings/SettingsCredentialsTab.vue'
import SettingsAutomatedTab from './settings/SettingsAutomatedTab.vue'
import SettingsBillTab from './settings/SettingsBillTab.vue'
import SettingsAppTab from './settings/SettingsAppTab.vue'
import SettingsPayeesPaymentsTab from './settings/SettingsPayeesPaymentsTab.vue'
import SettingsTtsTab from './settings/SettingsTtsTab.vue'
import SettingsImapTab from './settings/SettingsImapTab.vue'
import SettingsNotificationsTab from './settings/SettingsNotificationsTab.vue'

type Page =
  | 'menu'
  | 'console'
  | 'credentials'
  | 'automated'
  | 'bill-settings'
  | 'app-settings'
  | 'payees-payments'
  | 'tts'
  | 'imap'
  | 'notifications'

const currentPage = ref<Page>('menu')

const menuItems = [
  { id: 'console' as Page, icon: '📊', label: 'Console', description: 'View logs and system status' },
  { id: 'credentials' as Page, icon: '🔐', label: 'Credentials & Meter', description: 'Con Edison login and meter tracking' },
  { id: 'automated' as Page, icon: '⏰', label: 'Automated Scrape', description: 'Schedule automatic data scraping' },
  { id: 'bill-settings' as Page, icon: '📄', label: 'Bill Settings', description: 'Bill PDFs, auto-download, re-parse' },
  { id: 'payees-payments' as Page, icon: '👥', label: 'Payees & Payments', description: 'Users, bill split, cards, and payment audit' },
  { id: 'notifications' as Page, icon: '🔔', label: 'Notifications', description: 'Mobile push notifications for bill events' },
  { id: 'tts' as Page, icon: '🔊', label: 'TTS Alerts', description: 'Media player, TTS messages, and wait-for-idle' },
  { id: 'imap' as Page, icon: '📧', label: 'Email / IMAP', description: 'Email parsing for auto-payment detection' },
  { id: 'app-settings' as Page, icon: '⚙️', label: 'App Settings', description: 'App configuration' },
]
</script>

<style scoped>
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
</style>
