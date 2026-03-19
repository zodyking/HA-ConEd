<template>
  <div class="ha-payment-verification">
    <div class="ha-card ha-section-card">
      <div class="ha-card-header">
        <span class="ha-card-icon">✓</span>
        <span>Notification-Based Assignment</span>
      </div>
      <div class="ha-card-content">
        <div class="ha-form-group">
          <label class="ha-toggle-label">
            <input v-model="notificationClaimsEnabled" type="checkbox" :disabled="saving" />
            <span>Enable payment claim notifications</span>
          </label>
          <div class="ha-helper">Send "Did you make this payment?" notifications to payees with notification devices.</div>
        </div>
        <div class="ha-form-group">
          <label class="ha-toggle-label">
            <input v-model="autoSendClaimsAfterScrape" type="checkbox" :disabled="saving" />
            <span>Auto-send claims after scrape</span>
          </label>
          <div class="ha-helper">Send claim requests when new unverified payments are detected during a scrape (vs manual only).</div>
        </div>
        <div class="ha-form-group">
          <label class="ha-form-label">Resend delay when all say No (hours)</label>
          <input v-model.number="claimResendDelayHours" type="number" min="1" max="72" class="ha-form-input ha-number-input" :disabled="saving" />
          <div class="ha-helper">Hours to wait before resending claim notifications when all payees responded No.</div>
        </div>
        <div class="ha-form-group">
          <label class="ha-toggle-label">
            <input v-model="autoAssignSingleNonResponder" type="checkbox" :disabled="saving" />
            <span>Auto-assign when only one payee hasn't responded</span>
          </label>
          <div class="ha-helper">When only one payee has not responded and all others said No, automatically assign the payment to them.</div>
        </div>
        <p class="ha-helper">ConEd Connect integration automatically handles Yes/No taps. No automation needed.</p>
      </div>
    </div>

    <div class="ha-card ha-section-card">
      <div class="ha-card-header">
        <span class="ha-card-icon">📋</span>
        <span>Disputes</span>
      </div>
      <div class="ha-card-content">
        <div class="ha-form-group">
          <label class="ha-toggle-label">
            <input v-model="petitionsEnabled" type="checkbox" :disabled="saving" />
            <span>Allow petitions</span>
          </label>
          <div class="ha-helper">Allow payees to petition payments assigned to others (claim they made the payment).</div>
        </div>
      </div>
    </div>

    <button type="button" class="ha-button ha-button-primary" :disabled="saving" @click="handleSave">
      {{ saving ? 'Saving...' : 'Save' }}
    </button>

    <div v-if="message" :class="['ha-message', message.type]">{{ message.text }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getApiBase } from '../../lib/api-base'

const notificationClaimsEnabled = ref(true)
const autoSendClaimsAfterScrape = ref(true)
const claimResendDelayHours = ref(24)
const autoAssignSingleNonResponder = ref(true)
const petitionsEnabled = ref(true)
const saving = ref(false)
const message = ref<{ type: 'success' | 'error'; text: string } | null>(null)

async function load() {
  try {
    const res = await fetch(`${getApiBase()}/payment-verification-settings`)
    if (res.ok) {
      const d = await res.json()
      notificationClaimsEnabled.value = d.notification_claims_enabled !== false
      autoSendClaimsAfterScrape.value = d.auto_send_claims_after_scrape !== false
      claimResendDelayHours.value = Math.max(1, Math.min(72, parseInt(String(d.claim_resend_delay_hours), 10) || 24))
      autoAssignSingleNonResponder.value = d.auto_assign_single_non_responder !== false
      petitionsEnabled.value = d.petitions_enabled !== false
    }
  } catch {
    message.value = { type: 'error', text: 'Failed to load settings' }
  }
}

async function handleSave() {
  saving.value = true
  message.value = null
  try {
    const hours = Math.max(1, Math.min(72, claimResendDelayHours.value || 24))
    const res = await fetch(`${getApiBase()}/payment-verification-settings`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        notification_claims_enabled: notificationClaimsEnabled.value,
        auto_send_claims_after_scrape: autoSendClaimsAfterScrape.value,
        claim_resend_delay_hours: hours,
        auto_assign_single_non_responder: autoAssignSingleNonResponder.value,
        petitions_enabled: petitionsEnabled.value,
      }),
    })
    if (res.ok) {
      claimResendDelayHours.value = hours
      message.value = { type: 'success', text: 'Settings saved' }
    } else {
      const e = await res.json().catch(() => ({}))
      message.value = { type: 'error', text: e.detail || 'Failed to save' }
    }
  } catch {
    message.value = { type: 'error', text: 'Failed to connect' }
  } finally {
    saving.value = false
  }
}

onMounted(() => load())
</script>

<style scoped>
.ha-payment-verification { display: flex; flex-direction: column; gap: 1.5rem; }
.ha-section-card .ha-card-content { padding: 1rem 1.25rem; }
.ha-form-group { margin-bottom: 1rem; }
.ha-form-group:last-child { margin-bottom: 0; }
.ha-toggle-label { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; font-weight: 500; }
.ha-toggle-label input { cursor: pointer; }
.ha-form-label { display: block; font-weight: 500; margin-bottom: 0.35rem; }
.ha-form-input { padding: 0.5rem 0.75rem; border: 1px solid #e0e0e0; border-radius: 6px; font-size: 1rem; }
.ha-number-input { width: 80px; }
.ha-helper { font-size: 0.8rem; color: #666; margin-top: 0.25rem; margin-left: 1.5rem; }
.ha-message { margin-top: 0.5rem; padding: 0.75rem; border-radius: 4px; }
.ha-message.success { background: #e8f5e9; color: #2e7d32; }
.ha-message.error { background: #ffebee; color: #c62828; }
</style>
