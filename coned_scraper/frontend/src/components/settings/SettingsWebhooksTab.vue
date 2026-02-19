<template>
  <div class="ha-card">
    <div class="ha-card-header">
      <span class="ha-card-icon">🔗</span>
      <span>Home Assistant Webhooks</span>
    </div>
    <div class="ha-card-content">
      <div class="info-text" style="margin-bottom: 1.5rem">
        Configure separate webhook URLs for each event type. Each scrape will POST JSON data to the configured URLs.
      </div>
      <form @submit.prevent="handleSave">
        <div class="ha-form-group">
          <label for="latest-bill-url" class="ha-form-label">📄 Latest Bill Webhook</label>
          <input id="latest-bill-url" v-model="latestBillUrl" type="url" class="ha-form-input ha-input-mono" placeholder="https://homeassistant.local/api/webhook/YOUR_WEBHOOK_ID" />
          <div class="info-text">Sends latest bill amount, billing cycle date, and month range</div>
        </div>
        <div class="ha-form-group">
          <label for="previous-bill-url" class="ha-form-label">📋 Previous Bill Webhook</label>
          <input id="previous-bill-url" v-model="previousBillUrl" type="url" class="ha-form-input ha-input-mono" placeholder="https://homeassistant.local/api/webhook/YOUR_WEBHOOK_ID" />
          <div class="info-text">Sends previous bill amount, billing cycle date, and month range</div>
        </div>
        <div class="ha-form-group">
          <label for="account-balance-url" class="ha-form-label">💰 Account Balance Webhook</label>
          <input id="account-balance-url" v-model="accountBalanceUrl" type="url" class="ha-form-input ha-input-mono" placeholder="https://homeassistant.local/api/webhook/YOUR_WEBHOOK_ID" />
          <div class="info-text">Sends current account balance</div>
        </div>
        <div class="ha-form-group">
          <label for="last-payment-url" class="ha-form-label">💳 Last Payment Webhook</label>
          <input id="last-payment-url" v-model="lastPaymentUrl" type="url" class="ha-form-input ha-input-mono" placeholder="https://homeassistant.local/api/webhook/YOUR_WEBHOOK_ID" />
          <div class="info-text">Sends last payment amount and date</div>
        </div>
        <div class="ha-form-actions">
          <button type="submit" class="ha-button ha-button-primary" :disabled="isLoading">{{ isLoading ? 'Saving...' : 'Save Webhook URLs' }}</button>
          <button type="button" class="ha-button" :disabled="isLoading" @click="handleTest">{{ isLoading ? '...' : 'Test Webhooks' }}</button>
        </div>
      </form>
      <div v-if="message" :class="['ha-message', message.type]">{{ message.text }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getApiBase } from '../../lib/api-base'

const latestBillUrl = ref('')
const previousBillUrl = ref('')
const accountBalanceUrl = ref('')
const lastPaymentUrl = ref('')
const isLoading = ref(false)
const message = ref<{ type: 'success' | 'error'; text: string } | null>(null)

async function loadWebhooks() {
  try {
    const res = await fetch(`${getApiBase()}/webhooks`)
    if (res.ok) {
      const data = await res.json()
      latestBillUrl.value = data.latest_bill || ''
      previousBillUrl.value = data.previous_bill || ''
      accountBalanceUrl.value = data.account_balance || ''
      lastPaymentUrl.value = data.last_payment || ''
    }
  } catch (e) {
    console.error(e)
  }
}

async function handleSave() {
  isLoading.value = true
  message.value = null
  try {
    const payload = { latest_bill: latestBillUrl.value.trim(), previous_bill: previousBillUrl.value.trim(), account_balance: accountBalanceUrl.value.trim(), last_payment: lastPaymentUrl.value.trim() }
    const res = await fetch(`${getApiBase()}/webhooks`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
    if (res.ok) {
      const data = await res.json()
      message.value = { type: 'success', text: `Webhook URLs saved successfully! (${data.configured_count ?? 0} configured)` }
      await loadWebhooks()
    } else {
      let errMsg = 'Failed to save webhook URLs'
      try {
        const err = await res.json()
        if (err.detail) errMsg = Array.isArray(err.detail) ? err.detail.map((e: any) => `${e.loc?.join?.('.')}: ${e.msg}`).join(', ') : err.detail
      } catch { errMsg = `HTTP ${res.status}: ${res.statusText}` }
      message.value = { type: 'error', text: errMsg }
    }
  } catch (e) {
    message.value = { type: 'error', text: `Failed to connect to API: ${e instanceof Error ? e.message : 'Unknown'}` }
  } finally {
    isLoading.value = false
  }
}

async function handleTest() {
  isLoading.value = true
  message.value = null
  try {
    const res = await fetch(`${getApiBase()}/webhooks/test`, { method: 'POST' })
    if (res.ok) {
      const data = await res.json()
      message.value = { type: 'success', text: `Test webhooks sent! (${data.webhooks_sent?.join(', ') || 'none'})` }
    } else {
      const err = await res.json().catch(() => ({}))
      message.value = { type: 'error', text: err.detail || 'Failed to send test webhooks' }
    }
  } catch {
    message.value = { type: 'error', text: 'Failed to connect to API' }
  } finally {
    isLoading.value = false
  }
}

onMounted(loadWebhooks)
</script>

<style scoped>
.ha-input-mono { font-family: monospace; font-size: 0.9rem; }
.ha-form-actions { display: flex; gap: 1rem; margin-top: 1rem; }
.ha-message { margin-top: 1rem; padding: 0.75rem; border-radius: 4px; }
.ha-message.success { background: #e8f5e9; color: #2e7d32; }
.ha-message.error { background: #ffebee; color: #c62828; }
</style>
