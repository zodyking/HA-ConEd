<template>
  <div class="ha-container">
    <div class="ha-header">
      <div class="ha-header-content">
        <div class="ha-logo-container">
          <img :src="logoUrl" alt="ConEd Logo" width="100" height="20" />
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

    <div class="ha-content">
      <AccountLedger
        v-if="activeTab === 'account-ledger'"
        @navigate="onNavigate"
      />
      <Settings v-if="activeTab === 'settings'" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import AccountLedger from '../components/AccountLedger.vue'
import Settings from '../components/Settings.vue'
import { logoUrl } from '../lib/assets'

const activeTab = ref<'account-ledger' | 'settings'>('account-ledger')

function onNavigate(tab: 'console' | 'settings') {
  activeTab.value = tab === 'console' ? 'settings' : tab
}

function handleNavigateToLedger() {
  activeTab.value = 'account-ledger'
}

onMounted(() => {
  window.addEventListener('navigateToLedger', handleNavigateToLedger)
})
onUnmounted(() => {
  window.removeEventListener('navigateToLedger', handleNavigateToLedger)
})
</script>
