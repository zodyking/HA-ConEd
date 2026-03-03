<template>
  <div class="ha-card">
    <div class="ha-card-header">
      <span class="ha-card-icon">📄</span>
      <span>Bill Settings</span>
    </div>
    <div class="ha-card-content">
      <div class="ha-section">
        <h4 class="ha-section-title">Bill PDFs</h4>
        <p class="ha-pdf-desc">Add a PDF for each billing period. Paste the ConEd link, then download. The app stores and hosts the PDF.</p>

        <div class="ha-form-group" style="margin-bottom: 1rem;">
          <label class="ha-checkbox-label" style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
            <input v-model="autoDownloadPdfs" type="checkbox" @change="handleAutoDownloadPdfsChange" />
            <span>Auto-download PDFs during scrape</span>
          </label>
        </div>

        <div v-if="!bills.length" class="info-text">Run the scraper first to load billing periods</div>
        <div v-for="b in bills" :key="b.id" class="ha-pdf-cycle-block">
          <div class="ha-pdf-cycle-header">
            <span class="ha-pdf-cycle-period">{{ b.month_range || b.bill_cycle_date }}{{ b.pdf_exists ? ' ✓' : '' }}</span>
            <span v-if="b.pdf_exists" class="ha-pdf-cycle-actions">
              <a :href="`${getApiBase()}/bill-document/${b.id}`" target="_blank" rel="noopener" class="ha-btn ha-btn-blue">View</a>
              <button type="button" class="ha-btn ha-btn-red" :disabled="pdfLoading" @click="handleDeletePdf(b.id)">Delete</button>
            </span>
          </div>
          <div v-if="!b.pdf_exists" class="ha-pdf-cycle-form">
            <input
              v-model="pdfUrls[b.id]"
              type="text"
              class="ha-form-input ha-pdf-url-input"
              placeholder="Paste ConEd PDF link here"
            />
            <button
              type="button"
              class="ha-button ha-button-primary ha-btn-green"
              :disabled="pdfLoading || !(pdfUrls[b.id] || '').trim()"
              @click="handleDownloadPdfForBill(b.id)"
            >
              {{ pdfLoading ? 'Downloading...' : '⬇️ Download & Save' }}
            </button>
          </div>
        </div>

        <div v-if="billsWithPdf.length" class="ha-pdf-actions-row">
          <button type="button" class="ha-btn ha-btn-purple" :disabled="pdfLoading" @click="handleSendMqtt">Send MQTT</button>
          <button type="button" class="ha-btn ha-btn-blue" :disabled="reparseLoading" @click="handleReparseAll">
            {{ reparseLoading ? 'Parsing...' : '🔄 Re-parse All PDFs' }}
          </button>
        </div>
        <div class="info-text" v-if="billsWithPdf.length">PDF URLs use your Home Assistant external URL</div>
        <div v-if="pdfMessage" :class="['ha-message', pdfMessage.type]">{{ pdfMessage.text }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getApiBase } from '../../lib/api-base'

interface Bill {
  id: number
  month_range: string
  bill_cycle_date: string
  pdf_exists?: boolean
  pdf_source_url?: string | null
}

const pdfUrls = ref<Record<number, string>>({})
const pdfLoading = ref(false)
const pdfMessage = ref<{ type: 'success' | 'error'; text: string } | null>(null)
const bills = ref<Bill[]>([])
const billStatuses = ref<Record<number, { size_kb: number }>>({})
const reparseLoading = ref(false)
const autoDownloadPdfs = ref(true)

const billsWithPdf = computed(() =>
  bills.value.filter((b) => b.pdf_exists).map((b) => ({
    ...b,
    size_kb: billStatuses.value[b.id]?.size_kb ?? 0,
  }))
)

async function loadAppSettings() {
  try {
    const res = await fetch(`${getApiBase()}/app-settings`)
    if (res.ok) {
      const data = await res.json()
      autoDownloadPdfs.value = data.auto_download_pdfs !== false
    }
  } catch {
    autoDownloadPdfs.value = true
  }
}

async function handleAutoDownloadPdfsChange() {
  try {
    const res = await fetch(`${getApiBase()}/app-settings`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ auto_download_pdfs: autoDownloadPdfs.value })
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      pdfMessage.value = { type: 'error', text: err.detail || 'Failed to save' }
    }
  } catch {
    pdfMessage.value = { type: 'error', text: 'Failed to connect' }
  }
}

async function loadBills() {
  try {
    const res = await fetch(`${getApiBase()}/ledger`)
    if (res.ok) {
      const data = await res.json()
      bills.value = data.bills || []
      const next: Record<number, string> = {}
      for (const b of bills.value) {
        next[b.id] = pdfUrls.value[b.id] ?? (b.pdf_source_url || '')
      }
      pdfUrls.value = next
    } else {
      const billsRes = await fetch(`${getApiBase()}/bills`)
      if (billsRes.ok) {
        const data = await billsRes.json()
        bills.value = (data.bills || []).map((b: Bill) => ({ ...b, pdf_exists: false }))
        const next: Record<number, string> = {}
        for (const b of bills.value) {
          next[b.id] = pdfUrls.value[b.id] ?? ''
        }
        pdfUrls.value = next
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

async function handleDownloadPdfForBill(billId: number) {
  const url = (pdfUrls.value[billId] || '').trim()
  if (!url) {
    pdfMessage.value = { type: 'error', text: 'Enter a PDF URL' }
    return
  }
  pdfLoading.value = true
  pdfMessage.value = null
  try {
    const res = await fetch(`${getApiBase()}/bills/${billId}/pdf/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    })
    const data = await res.json().catch(() => ({}))
    if (res.ok) {
      pdfMessage.value = { type: 'success', text: data.message || 'PDF saved' }
      pdfUrls.value = { ...pdfUrls.value, [billId]: '' }
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

async function handleReparseAll() {
  reparseLoading.value = true
  pdfMessage.value = null
  try {
    const res = await fetch(`${getApiBase()}/bill-details/reparse-all`, { method: 'POST' })
    const data = await res.json()
    if (res.ok) {
      pdfMessage.value = { type: 'success', text: data.message || 'All PDFs re-parsed' }
    } else {
      pdfMessage.value = { type: 'error', text: data.detail || 'Failed to re-parse' }
    }
  } catch {
    pdfMessage.value = { type: 'error', text: 'Failed to connect' }
  } finally {
    reparseLoading.value = false
  }
}

onMounted(() => {
  loadAppSettings()
  loadBills().then(() => loadBillStatuses())
})
</script>

<style scoped>
.ha-section { margin-top: 0; padding-top: 0; }
.ha-section-title { font-size: 1.1rem; font-weight: 600; margin-bottom: 1rem; color: #333; }
.ha-pdf-desc { font-size: 0.9rem; color: #555; margin-bottom: 1rem; line-height: 1.5; }
.ha-pdf-cycle-block { margin-bottom: 1rem; padding: 1rem; background: #f9f9f9; border-radius: 8px; border: 1px solid #e0e0e0; }
.ha-pdf-cycle-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.5rem; }
.ha-pdf-cycle-period { font-weight: 600; color: #333; }
.ha-pdf-cycle-actions { display: flex; gap: 0.5rem; }
.ha-pdf-cycle-form { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; }
.ha-pdf-url-input { flex: 1; min-width: 200px; }
.ha-pdf-actions-row { margin-top: 0.75rem; }
.ha-btn-purple { background: #9c27b0; }
.ha-btn { padding: 0.4rem 0.75rem; border: none; border-radius: 4px; font-size: 0.8rem; cursor: pointer; text-decoration: none; color: white; }
.ha-btn-blue { background: #03a9f4; }
.ha-btn-red { background: #f44336; }
.ha-btn-green { width: 100%; padding: 0.75rem; background: #4caf50 !important; margin-top: 0.5rem; }
.ha-message { margin-top: 0.75rem; padding: 0.75rem; border-radius: 4px; }
.ha-message.success { background: #e8f5e9; color: #2e7d32; }
.ha-message.error { background: #ffebee; color: #c62828; }
</style>
