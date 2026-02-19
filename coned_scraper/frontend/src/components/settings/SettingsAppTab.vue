<template>
  <div class="ha-card">
    <div class="ha-card-header">
      <span class="ha-card-icon">⚙️</span>
      <span>App Settings</span>
    </div>
    <div class="ha-card-content">
      <div class="ha-section">
        <label class="ha-form-label">Your Local Time</label>
        <div class="ha-time-display">{{ currentTime || '--:--:--' }}</div>
        <div class="info-text">{{ Intl.DateTimeFormat().resolvedOptions().timeZone }}</div>
      </div>

      <div class="ha-section">
        <h4 class="ha-section-title">📄 Bill PDFs</h4>
        <p class="ha-pdf-desc">Add a PDF for each billing period. Paste the ConEd link, select the period, then download. The app stores and hosts the PDF.</p>

        <div class="ha-form-group">
          <label for="bill-period" class="ha-form-label">Billing Period</label>
          <select id="bill-period" v-model="selectedBillId" class="ha-form-input">
            <option value="">Select a billing period...</option>
            <option v-for="b in bills" :key="b.id" :value="b.id">
              {{ b.month_range || b.bill_cycle_date }} {{ b.pdf_exists ? '✓' : '' }}
            </option>
          </select>
          <div class="info-text">Run the scraper first if the list is empty</div>
        </div>
        <div class="ha-form-group">
          <label class="ha-form-label">PDF Link</label>
          <textarea v-model="pdfUrl" class="ha-form-input" placeholder="Paste the ConEd bill PDF link here" rows="3" />
          <div class="info-text">Get this link by clicking View Current Bill on ConEd website</div>
        </div>
        <button type="button" class="ha-button ha-button-primary ha-btn-green" :disabled="pdfLoading || !pdfUrl.trim() || !selectedBillId" @click="handleDownloadPdf">
          {{ pdfLoading ? 'Downloading...' : '⬇️ Download & Save PDF' }}
        </button>
        <div v-if="pdfMessage" :class="['ha-message', pdfMessage.type]">{{ pdfMessage.text }}</div>

        <div v-if="billsWithPdf.length" class="ha-pdf-actions-row">
          <button type="button" class="ha-btn ha-btn-purple" :disabled="pdfLoading" @click="handleSendMqtt">Send MQTT</button>
        </div>
        <div v-if="billsWithPdf.length" class="ha-pdf-list">
          <div class="ha-pdf-list-title">Stored PDFs</div>
          <div v-for="b in billsWithPdf" :key="b.id" class="ha-pdf-list-row">
            <span class="ha-pdf-period">{{ b.month_range || b.bill_cycle_date }}</span>
            <span v-if="b.size_kb" class="ha-pdf-size">{{ b.size_kb }} KB</span>
            <a :href="`${getApiBase()}/bill-document/${b.id}`" target="_blank" rel="noopener" class="ha-btn ha-btn-blue">View</a>
            <button type="button" class="ha-btn ha-btn-red" :disabled="pdfLoading" @click="handleDeletePdf(b.id)">Delete</button>
          </div>
        </div>
        <div v-if="bills.length && !billsWithPdf.length" class="ha-pdf-none">No PDFs stored yet. Add one above.</div>
      </div>

      <div class="ha-section">
        <h4 class="ha-section-title">🌐 App Base URL (for MQTT)</h4>
        <div class="ha-form-group">
          <label class="ha-form-label">Base URL</label>
          <input v-model="appBaseUrl" type="text" class="ha-form-input" placeholder="https://coned.your-domain.com" />
        </div>
        <button type="button" class="ha-button ha-button-primary" :disabled="isLoading" @click="handleSaveBaseUrl">{{ isLoading ? 'Saving...' : 'Save Base URL' }}</button>
      </div>

      <form @submit.prevent="handleSave" class="ha-section">
        <h4 class="ha-section-title">Change Settings Password</h4>
        <div class="ha-form-group">
          <label for="new-pwd" class="ha-form-label">New Password</label>
          <input id="new-pwd" v-model="newPassword" type="password" class="ha-form-input" placeholder="Leave empty to keep current" autocomplete="new-password" />
          <div class="info-text">Minimum 4 characters</div>
        </div>
        <div v-if="newPassword" class="ha-form-group">
          <label for="confirm-pwd" class="ha-form-label">Confirm New Password</label>
          <input id="confirm-pwd" v-model="confirmPassword" type="password" class="ha-form-input" placeholder="Re-enter" autocomplete="new-password" />
        </div>
        <button type="submit" class="ha-button ha-button-primary" :disabled="isLoading">{{ isLoading ? 'Saving...' : 'Change Password' }}</button>
      </form>
      <div v-if="message" :class="['ha-message', message.type]">{{ message.text }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getApiBase } from '../../lib/api-base'

interface Bill {
  id: number
  month_range: string
  bill_cycle_date: string
  pdf_exists?: boolean
}

const currentTime = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const isLoading = ref(false)
const message = ref<{ type: 'success' | 'error'; text: string } | null>(null)
const pdfUrl = ref('')
const pdfLoading = ref(false)
const pdfMessage = ref<{ type: 'success' | 'error'; text: string } | null>(null)
const appBaseUrl = ref('')
const bills = ref<Bill[]>([])
const selectedBillId = ref<number | ''>('')
const billStatuses = ref<Record<number, { size_kb: number }>>({})

const billsWithPdf = computed(() =>
  bills.value.filter((b) => b.pdf_exists).map((b) => ({
    ...b,
    size_kb: billStatuses.value[b.id]?.size_kb ?? 0,
  }))
)

async function loadBills() {
  try {
    const res = await fetch(`${getApiBase()}/ledger`)
    if (res.ok) {
      const data = await res.json()
      bills.value = data.bills || []
      if (bills.value.length && !selectedBillId.value) {
        selectedBillId.value = bills.value[0].id
      }
    } else {
      const billsRes = await fetch(`${getApiBase()}/bills`)
      if (billsRes.ok) {
        const data = await billsRes.json()
        bills.value = (data.bills || []).map((b: Bill) => ({ ...b, pdf_exists: false }))
      }
    }
  } catch { /* ignore */ }
}

async function loadBillStatuses() {
  const next: Record<number, { size_kb: number }> = {}
  for (const b of bills.value.filter((x) => x.pdf_exists)) {
    try {
      const res = await fetch(`${getApiBase()}/bills/${b.id}/pdf/status`)
      if (res.ok) {
        const data = await res.json()
        next[b.id] = { size_kb: data.size_kb ?? 0 }
      }
    } catch { /* ignore */ }
  }
  billStatuses.value = next
}

async function handleDownloadPdf() {
  const billId = selectedBillId.value
  if (!billId || !pdfUrl.value.trim()) {
    pdfMessage.value = { type: 'error', text: 'Select a period and enter a PDF URL' }
    return
  }
  pdfLoading.value = true
  pdfMessage.value = null
  try {
    const res = await fetch(`${getApiBase()}/bills/${billId}/pdf/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: pdfUrl.value.trim() }),
    })
    const data = await res.json().catch(() => ({}))
    if (res.ok) {
      pdfMessage.value = { type: 'success', text: data.message || 'PDF saved' }
      pdfUrl.value = ''
      await loadBills()
      await loadBillStatuses()
    } else {
      pdfMessage.value = { type: 'error', text: data.detail || 'Failed to download' }
    }
  } catch {
    pdfMessage.value = { type: 'error', text: 'Failed to connect' }
  } finally {
    pdfLoading.value = false
  }
}

async function handleDeletePdf(billId: number) {
  pdfLoading.value = true
  pdfMessage.value = null
  try {
    const res = await fetch(`${getApiBase()}/bills/${billId}/pdf`, { method: 'DELETE' })
    if (res.ok) {
      pdfMessage.value = { type: 'success', text: 'PDF deleted' }
      await loadBills()
      await loadBillStatuses()
    } else {
      pdfMessage.value = { type: 'error', text: 'Failed to delete' }
    }
  } catch {
    pdfMessage.value = { type: 'error', text: 'Failed to connect' }
  } finally {
    pdfLoading.value = false
  }
}

async function handleSendMqtt() {
  pdfLoading.value = true
  pdfMessage.value = null
  try {
    const res = await fetch(`${getApiBase()}/latest-bill-pdf/send-mqtt`, { method: 'POST' })
    const data = await res.json()
    pdfMessage.value = res.ok ? { type: 'success', text: data.message || 'PDF URL sent to MQTT' } : { type: 'error', text: data.detail || 'Failed' }
  } catch {
    pdfMessage.value = { type: 'error', text: 'Failed' }
  } finally {
    pdfLoading.value = false
  }
}

async function handleSaveBaseUrl() {
  isLoading.value = true
  message.value = null
  try {
    const cur = await fetch(`${getApiBase()}/app-settings`).then((r) => r.json())
    const res = await fetch(`${getApiBase()}/app-settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ time_offset_hours: cur.time_offset_hours || 0, settings_password: cur.settings_password || '0000', app_base_url: appBaseUrl.value.trim() }),
    })
    message.value = res.ok ? { type: 'success', text: 'App Base URL saved!' } : { type: 'error', text: 'Failed' }
  } catch {
    message.value = { type: 'error', text: 'Failed to connect' }
  } finally {
    isLoading.value = false
  }
}

async function handleSave() {
  if (newPassword.value && newPassword.value !== confirmPassword.value) {
    message.value = { type: 'error', text: 'Passwords do not match' }
    return
  }
  if (newPassword.value && newPassword.value.length < 4) {
    message.value = { type: 'error', text: 'Password must be at least 4 characters' }
    return
  }
  isLoading.value = true
  message.value = null
  try {
    const cur = await fetch(`${getApiBase()}/app-settings`).then((r) => r.json())
    const res = await fetch(`${getApiBase()}/app-settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ time_offset_hours: cur.time_offset_hours || 0, settings_password: newPassword.value || cur.settings_password || '0000' }),
    })
    if (res.ok) {
      const didChange = !!newPassword.value
      message.value = { type: 'success', text: 'Password changed!' }
      newPassword.value = ''
      confirmPassword.value = ''
      if (didChange) setTimeout(() => window.location.reload(), 2000)
    } else {
      const err = await res.json().catch(() => ({}))
      message.value = { type: 'error', text: err.detail || 'Failed' }
    }
  } catch {
    message.value = { type: 'error', text: 'Failed to connect' }
  } finally {
    isLoading.value = false
  }
}

let timeInterval: ReturnType<typeof setInterval>
onMounted(() => {
  fetch(`${getApiBase()}/app-settings`)
    .then((r) => r.json())
    .then((d) => {
      appBaseUrl.value = d.app_base_url || ''
    })
    .catch(() => {})
  loadBills().then(() => loadBillStatuses())
  timeInterval = setInterval(() => {
    currentTime.value = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true })
  }, 1000)
})
onUnmounted(() => clearInterval(timeInterval))
</script>

<style scoped>
.ha-section { margin-top: 2rem; padding-top: 2rem; border-top: 1px solid #e0e0e0; }
.ha-section:first-child { margin-top: 0; padding-top: 0; border-top: none; }
.ha-time-display { padding: 0.75rem 1.25rem; background: #1a1a2e; border-radius: 8px; font-family: monospace; font-size: 1.5rem; font-weight: bold; color: #4ade80; min-width: 150px; text-align: center; margin: 0.5rem 0; }
.ha-section-title { font-size: 1.1rem; font-weight: 600; margin-bottom: 1rem; color: #333; }
.ha-pdf-desc { font-size: 0.9rem; color: #555; margin-bottom: 1rem; line-height: 1.5; }
.ha-pdf-actions-row { margin-top: 0.75rem; }
.ha-btn-purple { background: #9c27b0; }
.ha-pdf-list { margin-top: 1.25rem; padding: 1rem; background: #f5f5f5; border-radius: 8px; }
.ha-pdf-list-title { font-weight: 600; margin-bottom: 0.75rem; font-size: 0.9rem; }
.ha-pdf-list-row { display: flex; align-items: center; gap: 0.75rem; padding: 0.5rem 0; border-bottom: 1px solid #e0e0e0; flex-wrap: wrap; }
.ha-pdf-list-row:last-child { border-bottom: none; }
.ha-pdf-period { flex: 1; min-width: 120px; font-weight: 500; }
.ha-pdf-size { font-size: 0.8rem; color: #666; }
.ha-pdf-none { font-size: 0.9rem; color: #999; margin-top: 1rem; }
.ha-btn { padding: 0.4rem 0.75rem; border: none; border-radius: 4px; font-size: 0.8rem; cursor: pointer; text-decoration: none; color: white; }
.ha-btn-blue { background: #03a9f4; }
.ha-btn-red { background: #f44336; }
.ha-btn-green { width: 100%; padding: 0.75rem; background: #4caf50 !important; margin-top: 0.5rem; }
.ha-message { margin-top: 0.75rem; padding: 0.75rem; border-radius: 4px; }
.ha-message.success { background: #e8f5e9; color: #2e7d32; }
.ha-message.error { background: #ffebee; color: #c62828; }
</style>
