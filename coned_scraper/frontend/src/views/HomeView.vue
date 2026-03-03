<template>
  <div class="ha-container">
    <div class="ha-header">
      <div class="ha-header-content">
        <div class="ha-logo-container">
          <img :src="logoUrl" alt="Con Edison" width="100" height="20" />
        </div>
        <nav class="ha-nav">
          <button
            :class="['ha-nav-button', { active: activeTab === 'account-ledger' }]"
            aria-label="Account Ledger"
            @click="activeTab = 'account-ledger'"
          >
            <span class="ha-nav-icon">📋</span>
            <span>Account Ledger</span>
          </button>
          <button
            :class="['ha-nav-button', { active: activeTab === 'history' }]"
            aria-label="History"
            @click="activeTab = 'history'"
          >
            <span class="ha-nav-icon">📊</span>
            <span>History</span>
          </button>
          <button
            v-if="showSettingsNav"
            :class="['ha-nav-button', { active: activeTab === 'settings' }]"
            aria-label="Settings"
            @click="activeTab = 'settings'"
          >
            <span class="ha-nav-icon">⚙️</span>
            <span>Settings</span>
          </button>
        </nav>
      </div>
    </div>

    <div class="ha-header-bar"></div>

    <div :class="['ha-content', { 'ha-content-ledger': activeTab === 'account-ledger' }]">
      <AccountLedger
        v-if="activeTab === 'account-ledger'"
        @navigate="onNavigate"
      />
      <History v-if="activeTab === 'history'" />
      <Settings v-if="activeTab === 'settings'" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import AccountLedger from '../components/AccountLedger.vue'
import History from '../components/History.vue'
import Settings from '../components/Settings.vue'
import { logoUrl } from '../lib/assets'
import { waitForSettingsNavVisibility } from '../lib/ha-user-admin'

const activeTab = ref<'account-ledger' | 'history' | 'settings'>('account-ledger')
const showSettingsNav = ref(false)

function onNavigate(tab: 'console' | 'settings') {
  activeTab.value = tab === 'console' ? 'settings' : tab
}

function handleNavigateToLedger() {
  activeTab.value = 'account-ledger'
}

watch([showSettingsNav, activeTab], ([nav, tab]) => {
  if (nav === false && tab === 'settings') {
    activeTab.value = 'account-ledger'
  }
})

onMounted(async () => {
  window.addEventListener('navigateToLedger', handleNavigateToLedger)
  showSettingsNav.value = await waitForSettingsNavVisibility()
})
onUnmounted(() => {
  window.removeEventListener('navigateToLedger', handleNavigateToLedger)
})
</script>
