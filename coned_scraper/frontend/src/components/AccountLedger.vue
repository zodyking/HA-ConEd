<template>
  <div>
    <!-- Screenshot Modal -->
    <div
      v-if="showScreenshotModal && screenshotPath"
      class="ha-modal-overlay"
      @click="showScreenshotModal = false"
    >
      <button class="ha-modal-close" @click="showScreenshotModal = false">✕</button>
      <img
        :src="`${getApiBase()}/screenshot/${screenshotPath.split('/').pop() || screenshotPath}`"
        alt="Account Balance Screenshot"
        class="ha-modal-img"
        @click.stop
      />
    </div>

    <!-- PDF Bill Modal -->
    <PdfViewer
      v-if="showPdfModal && viewingBillId"
      :url="`${getApiBase()}/bill-document/${viewingBillId}`"
      @close="showPdfModal = false; viewingBillId = null"
    />

    <!-- Loading -->
    <div v-if="isLoading" class="ha-loading-state">
      <img :src="ajaxLoader" alt="Loading" class="ha-loading-img" />
      <div class="ha-loading-text">Loading account ledger...</div>
    </div>

    <!-- API Error -->
    <div v-else-if="apiError" class="ha-error-state">{{ apiError }}</div>

    <!-- No Data -->
    <div
      v-else-if="!ledgerData || (!ledgerData.account_balance && ledgerData.bills.length === 0)"
      class="ha-empty-data"
    >
      <img :src="ajaxLoader" alt="Setup Required" class="ha-empty-img" />
      <h2 class="ha-empty-title">No Account Data Yet</h2>
      <p class="ha-empty-desc">
        To get started, please configure your credentials in Settings and run the scraper from the Console.
      </p>
      <button class="ha-empty-btn" @click="$emit('navigate', 'settings')">⚙️ Go to Settings</button>
    </div>

    <!-- Ledger Content -->
    <div v-else class="ha-ledger">
      <!-- Account Summary (top of content, scrolls with page) -->
      <div class="ha-ledger-summary">
      <div class="ha-card ha-card-summary">
        <div class="ha-card-header">
          <span class="ha-card-icon">💰</span>
          <span>Account Summary</span>
        </div>
        <div class="ha-card-content ha-summary-content">
          <!-- Account Overview Row -->
          <div class="ha-summary-row ha-summary-row-two">
            <div class="ha-summary-box ha-balance-box">
              <div class="ha-summary-label">Account Balance</div>
              <div class="ha-summary-value ha-balance-text">{{ ledgerData.account_balance || '—' }}</div>
            </div>
            <div class="ha-summary-box ha-due-box" v-if="latestBillDueDate">
              <div class="ha-summary-label">Due Date</div>
              <div class="ha-summary-value ha-due-text">{{ latestBillDueDate }}</div>
            </div>
          </div>
          
          <!-- Current Billing Period Section -->
          <div class="ha-billing-section" v-if="meterData?.enabled && meterData?.forecast?.usage_to_date">
            <div class="ha-section-header">
              <span class="ha-section-title">Current Billing Period</span>
              <span class="ha-section-dates" v-if="meterData?.forecast?.start_date">
                {{ formatShortDate(meterData.forecast.start_date) }} — {{ formatShortDate(meterData.forecast.end_date) }}
              </span>
            </div>
            
            <div class="ha-stats-grid">
              <div class="ha-stat-item">
                <div class="ha-stat-label">Usage to Date</div>
                <div class="ha-stat-value">{{ meterData.forecast.usage_to_date }} <span class="ha-stat-unit">kWh</span></div>
              </div>
              <div class="ha-stat-item">
                <div class="ha-stat-label">Cost to Date</div>
                <div class="ha-stat-value">${{ meterData.usage_to_date_cost?.toFixed(2) || '—' }}</div>
              </div>
              <div class="ha-stat-item ha-stat-projected">
                <div class="ha-stat-label">Projected Usage</div>
                <div class="ha-stat-value">{{ meterData.forecast.forecasted_usage }} <span class="ha-stat-unit">kWh</span></div>
              </div>
              <div class="ha-stat-item ha-stat-projected">
                <div class="ha-stat-label">Projected Bill</div>
                <div class="ha-stat-value">${{ projectedBillCost }}</div>
              </div>
            </div>
          </div>
          
          <div class="ha-summary-actions">
            <button
              class="ha-summary-btn"
              :class="{ disabled: !screenshotPath }"
              :disabled="!screenshotPath"
              @click="screenshotPath && (showScreenshotModal = true)"
            >
              Account
            </button>
            <button
              class="ha-summary-btn"
              :class="pdfExists ? 'green' : 'orange'"
              @click="pdfExists ? openLatestPdf() : navigateToSettings()"
            >
              {{ pdfExists ? 'Latest Bill' : 'Add Bill' }}
            </button>
          </div>
        </div>
      </div>
      </div>

      <!-- Bill History Ledger -->
      <div class="ha-card ha-card-ledger">
        <div class="ha-card-header">
          <span class="ha-card-icon">📋</span>
          <span>Bill History Ledger</span>
        </div>
        <div class="ha-card-content">
          <template v-if="ledgerData.bills.length > 0">
            <div 
              v-for="(bill, index) in ledgerData.bills" 
              :key="bill.id" 
              class="ha-bill-card"
              :class="{ 'ha-bill-card-latest': index === 0 }"
            >
              <!-- Bill Header - clickable to expand/collapse -->
              <div 
                class="ha-bill-header"
                :class="{ 'ha-bill-header-latest': index === 0 }"
                @click="toggleBillExpanded(bill.id)"
              >
                <div class="ha-bill-header-left">
                  <span class="ha-bill-cycle">{{ bill.month_range || bill.bill_cycle_date }}</span>
                  <span class="ha-bill-total-inline">{{ bill.bill_total || '-' }}</span>
                </div>
                <div class="ha-bill-header-right">
                  <span v-if="index === 0 && bill.due_date" class="ha-bill-due-badge">
                    Due: {{ bill.due_date }}
                  </span>
                  <span class="ha-expand-icon">{{ expandedBills.has(bill.id) ? '▼' : '▶' }}</span>
                </div>
              </div>
              
              <!-- Bill Details (expandable) -->
              <div v-if="expandedBills.has(bill.id)" class="ha-bill-details">
                <div class="ha-bill-entry">
                  <div class="ha-bill-content">
                    <div class="ha-bill-meta">
                      <span class="ha-bill-badge">Bill</span>
                      <div>
                        <div class="ha-bill-title">{{ bill.month_range || 'Bill' }}</div>
                        <div class="ha-bill-date">
                          {{ bill.bill_date ? formatDateShort(bill.bill_date) : bill.bill_cycle_date }}
                        </div>
                      </div>
                    </div>
                    <div class="ha-bill-amount">{{ bill.bill_total || '-' }}</div>
                    <button
                      v-if="bill.pdf_exists"
                      type="button"
                      class="ha-btn-pdf"
                      @click.stop="openBillPdf(bill.id)"
                    >
                      📄 View PDF
                    </button>
                  </div>
                </div>
                
                <!-- Payments Section (collapsible) -->
                <div v-if="bill.payments && bill.payments.length" class="ha-payments-section">
                  <div 
                    class="ha-payments-header"
                    @click.stop="togglePaymentsExpanded(bill.id)"
                  >
                    <span class="ha-payments-label">
                      💳 Payments ({{ bill.payments.length }})
                    </span>
                    <span class="ha-expand-icon-sm">{{ expandedPayments.has(bill.id) ? '▼' : '▶' }}</span>
                  </div>
                  
                  <div v-if="expandedPayments.has(bill.id)" class="ha-payments-list">
                    <div
                      v-for="payment in bill.payments"
                      :key="payment.id"
                      class="ha-payment-entry"
                    >
                      <div class="ha-payment-row">
                        <div class="ha-payment-meta">
                          <span class="ha-payment-badge">Payment</span>
                          <div>
                            <div class="ha-payment-desc">
                              {{ payment.description || 'Payment Received' }}
                              <span v-if="(payment.payee_status === 'confirmed' || payment.payee_status === 'auto_assigned') && payment.payee_name" class="ha-payee-badge">
                                {{ payment.payee_name }}
                              </span>
                              <span
                                v-else-if="payment.payee_status === 'pending'"
                                class="ha-payee-pending"
                                title="Searching for payee info..."
                              >
                                <span class="spinner-mini">⟳</span>
                                Loading...
                              </span>
                              <span
                                v-else
                                class="ha-payee-unverified"
                                title="Unverified - assign payee in Settings → Payments"
                              >
                                Unverified
                              </span>
                            </div>
                            <div class="ha-payment-sub">
                              {{ payment.payment_date }}
                              <span v-if="payment.card_last_four" class="ha-card-four">*{{ payment.card_last_four }}</span>
                            </div>
                          </div>
                        </div>
                        <div class="ha-payment-amount">{{ payment.amount || '-' }}</div>
                      </div>
                    </div>
                  </div>
                </div>
                
                <BillPayeeSummary
                  :bill-id="bill.id"
                  :bill-summaries="billSummaries"
                />
              </div>
            </div>

            <!-- Orphan Payments -->
            <div v-if="ledgerData.orphan_payments?.length" class="ha-bill-card ha-orphan-card">
              <div class="ha-bill-header ha-orphan-header">
                ⚠️ Unlinked Payments - Assign in Settings → Payments
              </div>
              <div
                v-for="payment in ledgerData.orphan_payments"
                :key="payment.id"
                class="ha-payment-entry"
              >
                <div class="ha-payment-row">
                  <div class="ha-payment-meta">
                    <span class="ha-payment-badge">Payment</span>
                    <div>
                      <div class="ha-payment-desc">
                        {{ payment.description || 'Payment Received' }}
                        <span v-if="(payment.payee_status === 'confirmed' || payment.payee_status === 'auto_assigned') && payment.payee_name" class="ha-payee-badge">
                          {{ payment.payee_name }}
                        </span>
                        <span v-else-if="payment.payee_status === 'pending'" class="ha-payee-pending">
                          <span class="spinner-mini">⟳</span>
                          Loading payee...
                        </span>
                        <span v-else class="ha-payee-unverified">
                          Unassigned
                        </span>
                      </div>
                      <div class="ha-payment-sub">
                        {{ payment.payment_date }}
                        <span v-if="payment.card_last_four">*{{ payment.card_last_four }}</span>
                      </div>
                    </div>
                  </div>
                  <div class="ha-payment-amount">{{ payment.amount || '-' }}</div>
                </div>
              </div>
            </div>
          </template>
          <div v-else class="ha-no-bills">
            <img :src="ajaxLoader" alt="Loading" class="ha-no-bills-img" />
            <h3 class="ha-no-bills-title">No Bill History Available</h3>
            <p class="ha-no-bills-desc">Run the scraper to populate bill history data.</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { formatDate } from '../lib/timezone'
import { getApiBase } from '../lib/api-base'
import { ajaxLoader } from '../lib/assets'
import PdfViewer from './PdfViewer.vue'
import BillPayeeSummary from './BillPayeeSummary.vue'

const emit = defineEmits<{ (e: 'navigate', tab: 'console' | 'settings'): void }>()

interface Payment {
  id: number
  bill_id: number | null
  payment_date: string
  description: string
  amount: string
  amount_numeric: number | null
  first_scraped_at: string
  last_scraped_at: string
  scrape_count: number
  scrape_order: number | null
  payee_status: 'confirmed' | 'pending' | 'unverified' | 'auto_timeout'
  payee_user_id: number | null
  payee_name: string | null
  card_last_four: string | null
  verification_method: string | null
}

interface Bill {
  id: number
  bill_cycle_date: string
  bill_date: string | null
  month_range: string
  bill_total: string
  amount_numeric: number | null
  pdf_exists?: boolean
  first_scraped_at: string
  last_scraped_at: string
  scrape_count: number
  payments: Payment[]
}

interface LedgerData {
  account_balance: string | null
  balance_updated_at: string | null
  latest_payment: Payment | null
  latest_bill: Bill | null
  bills: Bill[]
  orphan_payments: Payment[]
  payee_summaries?: Record<number, unknown>
}

const ledgerData = ref<LedgerData | null>(null)
const screenshotPath = ref<string | null>(null)
const isLoading = ref(true)
const apiError = ref<string | null>(null)
const showScreenshotModal = ref(false)
const showPdfModal = ref(false)
const viewingBillId = ref<number | null>(null)
const pdfExists = ref(false)
const billSummaries = computed<Record<number, any>>(() => {
  const summaries = ledgerData.value?.payee_summaries
  if (!summaries || typeof summaries !== 'object') return {}
  const out: Record<number, any> = {}
  for (const [k, v] of Object.entries(summaries)) {
    const id = parseInt(String(k), 10)
    if (!isNaN(id) && v) out[id] = v
  }
  return out
})
const expandedBills = ref<Set<number>>(new Set())
const expandedPayments = ref<Set<number>>(new Set())

// Meter tracking state
interface MeterReadingData {
  enabled: boolean
  reading: {
    value: number | null
    unit: string
    fetched_at: string
  } | null
  cost: number | null
  forecast: {
    usage_to_date: number | null
    forecasted_usage: number | null
    start_date: string | null
    end_date: string | null
  } | null
  usage_to_date_cost: number | null
  kwh_cost: number | null
}
const meterData = ref<MeterReadingData | null>(null)

const projectedBillCost = computed(() => {
  if (!meterData.value?.forecast?.forecasted_usage || !meterData.value?.kwh_cost) return '—'
  const cost = meterData.value.forecast.forecasted_usage * meterData.value.kwh_cost
  return cost.toFixed(2)
})

function formatBillingDate(dateStr: string | null): string {
  if (!dateStr) return '—'
  try {
    const date = new Date(dateStr + 'T00:00:00')
    return date.toLocaleDateString('en-US', { 
      weekday: 'long', 
      month: 'long', 
      day: 'numeric', 
      year: 'numeric' 
    })
  } catch {
    return dateStr
  }
}

function formatShortDate(dateStr: string | null): string {
  if (!dateStr) return '—'
  try {
    const date = new Date(dateStr + 'T00:00:00')
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric' 
    })
  } catch {
    return dateStr
  }
}

function toggleBillExpanded(billId: number) {
  if (expandedBills.value.has(billId)) {
    expandedBills.value.delete(billId)
  } else {
    expandedBills.value.add(billId)
  }
  expandedBills.value = new Set(expandedBills.value) // trigger reactivity
}

function togglePaymentsExpanded(billId: number) {
  if (expandedPayments.value.has(billId)) {
    expandedPayments.value.delete(billId)
  } else {
    expandedPayments.value.add(billId)
  }
  expandedPayments.value = new Set(expandedPayments.value) // trigger reactivity
}

function initializeExpandedState() {
  // Expand the first (latest) bill and its payments by default
  if (ledgerData.value && ledgerData.value.bills.length > 0) {
    const latestBillId = ledgerData.value.bills[0].id
    expandedBills.value.add(latestBillId)
    expandedPayments.value.add(latestBillId)
    expandedBills.value = new Set(expandedBills.value)
    expandedPayments.value = new Set(expandedPayments.value)
  }
}

function formatDateShort(date: string) {
  return formatDate(date, { year: 'numeric', month: 'short', day: 'numeric' })
}

const latestBillDueDate = computed(() => {
  if (ledgerData.value && ledgerData.value.bills.length > 0) {
    return ledgerData.value.bills[0].due_date || null
  }
  return null
})

async function loadLedgerData() {
  try {
    const api = getApiBase()
    const response = await fetch(`${api}/ledger`)
    if (response.ok) {
      const data = await response.json()
      ledgerData.value = data
      apiError.value = null
    } else {
      const legacyResponse = await fetch(`${api}/scraped-data?limit=1`)
      if (legacyResponse.ok) {
        const legacyData = await legacyResponse.json()
        if (legacyData.data?.[0]) {
          const scraped = legacyData.data[0]
          ledgerData.value = {
            account_balance: scraped.data?.account_balance || null,
            balance_updated_at: scraped.timestamp,
            latest_payment: null,
            latest_bill: null,
            bills: [],
            orphan_payments: [],
          }
          screenshotPath.value = scraped.screenshot_path || null
        }
      } else {
        apiError.value = 'Failed to load ledger data'
      }
    }
    const screenshotRes = await fetch(`${api}/scraped-data?limit=1`)
    if (screenshotRes.ok) {
      const screenshotData = await screenshotRes.json()
      if (screenshotData.data?.[0]?.screenshot_path) {
        screenshotPath.value = screenshotData.data[0].screenshot_path
      }
    }
  } catch {
    apiError.value = "Cannot connect to Python service. Make sure it's running on port 8000."
  } finally {
    isLoading.value = false
    initializeExpandedState()
  }
}

async function checkPdfExists() {
  try {
    const res = await fetch(`${getApiBase()}/latest-bill-pdf/status`)
    if (res.ok) {
      const data = await res.json()
      pdfExists.value = data.exists
    }
  } catch {
    pdfExists.value = false
  }
}

async function loadMeterData() {
  try {
    const res = await fetch(`${getApiBase()}/meter-reading`)
    if (res.ok) {
      const data = await res.json()
      meterData.value = data
    }
  } catch {
    meterData.value = null
  }
}

function openLatestPdf() {
  const b = ledgerData.value?.bills?.find((x: { pdf_exists?: boolean }) => x.pdf_exists)
  if (b) {
    viewingBillId.value = b.id
    showPdfModal.value = true
  }
}

function openBillPdf(billId: number) {
  viewingBillId.value = billId
  showPdfModal.value = true
}

function navigateToSettings() {
  emit('navigate', 'settings')
}

let interval: ReturnType<typeof setInterval>
onMounted(() => {
  loadLedgerData()
  loadMeterData()
  checkPdfExists()
  interval = setInterval(() => {
    loadLedgerData()
  }, 30000)
})
onUnmounted(() => clearInterval(interval))
</script>

<style scoped>
.ha-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 1rem;
}
.ha-modal-header { display: flex; justify-content: space-between; align-items: center; padding: 1rem 1.25rem; border-bottom: 1px solid #e0e0e0; font-weight: 600; }
.ha-modal-body { padding: 1.25rem; }
.ha-modal-footer { display: flex; justify-content: flex-end; gap: 0.5rem; padding: 1rem 1.25rem; border-top: 1px solid #e0e0e0; }
.ha-modal-desc { font-size: 0.9rem; color: #666; margin: 0 0 1rem 0; }
.ha-modal-close { background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #666; padding: 0 0.25rem; }
.ha-btn-link { background: none; border: none; color: #1976d2; cursor: pointer; font-size: 0.85rem; padding: 0.25rem 0; text-decoration: underline; margin-left: 0.5rem; }
.ha-btn { padding: 0.5rem 1rem; border: none; border-radius: 6px; cursor: pointer; font-size: 0.85rem; }
.ha-btn-gray { background: #e0e0e0; color: #333; }
.ha-btn-primary { background: #1976d2; color: white; }
.ha-message { margin-top: 0.75rem; padding: 0.5rem; border-radius: 4px; font-size: 0.9rem; }
.ha-message.success { background: #e8f5e9; color: #2e7d32; }
.ha-message.error { background: #ffebee; color: #c62828; }
.ha-modal-overlay .ha-modal { margin: auto; }
.ha-modal-close {
  position: relative;
  top: 0;
  right: 0;
  background: white;
  border: none;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  font-size: 1.5rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  z-index: 10000;
}
.ha-modal-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: 4px;
}
.ha-loading-state,
.ha-empty-data,
.ha-no-bills {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  padding: 4rem 2rem;
  text-align: center;
}
.ha-loading-img {
  width: 64px;
  height: 64px;
  margin-bottom: 1.5rem;
}
.ha-loading-text,
.ha-empty-desc {
  color: #666;
  font-size: 1rem;
  margin-top: 1rem;
}
.ha-error-state {
  padding: 2rem;
  text-align: center;
  color: #d32f2f;
}
.ha-empty-img {
  width: 80px;
  height: 80px;
  margin-bottom: 2rem;
  opacity: 0.8;
}
.ha-empty-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #333;
  margin-bottom: 1rem;
}
.ha-empty-desc {
  max-width: 500px;
  line-height: 1.6;
  margin-bottom: 2rem;
}
.ha-empty-btn {
  padding: 0.75rem 1.5rem;
  background: #03a9f4;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  font-weight: 500;
}
.ha-summary-content {
  padding: 0.5rem !important;
}
.ha-summary-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.4rem;
}
.ha-summary-row-two {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}
.ha-summary-box {
  text-align: center;
  padding: 0.6rem 0.75rem;
  border-radius: 6px;
  flex: 1;
}
.ha-balance-box {
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
}
.ha-balance-box .ha-balance-text {
  color: #0277bd;
}
.ha-summary-label {
  font-size: 0.5rem;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
.ha-summary-value { font-size: 0.75rem; font-weight: 600; }
.ha-balance-text { font-size: 1.25rem; font-weight: 700; color: #03a9f4; }
.ha-payment-text { color: #4caf50; }
.ha-bill-text { color: #f44336; }
.ha-summary-sub { font-size: 0.55rem; color: #666; }
.ha-summary-info { text-align: center; flex: 1; }
.ha-summary-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.4rem;
}
.ha-summary-btn {
  padding: 0.4rem;
  border: none;
  cursor: pointer;
  color: white;
  border-radius: 4px;
  font-size: 0.65rem;
  font-weight: 500;
}
.ha-summary-btn.disabled { background: #ccc; cursor: not-allowed; }
.ha-summary-btn.green { background: #4caf50; }
.ha-summary-btn.orange { background: #ff9800; }
.ha-summary-btn:not(.disabled):not([disabled]) { background: #03a9f4; }
.ha-bill-meta { display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; }
.ha-bill-title { font-weight: 600; margin-bottom: 0.15rem; font-size: 0.8rem; }
.ha-bill-date { font-size: 0.7rem; color: #666; }
.ha-payment-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.ha-payment-meta { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.ha-payment-desc { font-weight: 500; margin-bottom: 0.1rem; font-size: 0.75rem; display: flex; align-items: center; gap: 0.4rem; }
.ha-payee-badge { font-size: 0.6rem; background: #e3f2fd; color: #1565c0; padding: 0.1rem 0.3rem; border-radius: 3px; }
.ha-payee-pending { font-size: 0.6rem; background: #e8f5e9; color: #2e7d32; padding: 0.1rem 0.3rem; border-radius: 3px; display: inline-flex; align-items: center; gap: 0.3rem; }
.ha-payee-unverified { font-size: 0.6rem; background: #fff3e0; color: #e65100; padding: 0.1rem 0.3rem; border-radius: 3px; }
.ha-payment-sub { font-size: 0.65rem; color: #666; }
.ha-card-four { margin-left: 0.5rem; color: #999; }
.ha-orphan-card { border-left-color: #ff9800; }
.ha-orphan-header { background: #fff3e0; color: #e65100; }
.ha-no-bills { min-height: 300px; }
.ha-no-bills-img { width: 120px; height: 120px; margin-bottom: 2rem; }
.ha-no-bills-title { font-size: 1.25rem; font-weight: 600; color: #333; margin-bottom: 1rem; }
.ha-no-bills-desc { color: #666; font-size: 1rem; max-width: 500px; line-height: 1.6; margin-bottom: 1.5rem; }

/* Due Date in Summary - Con Edison Orange */
.ha-due-box {
  background: #fff8f3;
  border: 1px solid #f37321;
}
.ha-due-box .ha-summary-label {
  color: #c55a1a;
}
.ha-due-text {
  color: #f37321;
  font-weight: 700;
  font-size: 1.1rem;
}

/* Account Balance - Blue matching header */
.ha-balance-box {
  background: #f0f9ff;
  border: 1px solid #0088cc;
}
.ha-balance-box .ha-summary-label {
  color: #006699;
}
.ha-balance-text {
  color: #0088cc;
  font-weight: 700;
  font-size: 1.25rem;
}

/* Current Billing Period Section */
.ha-billing-section {
  margin-top: 0.75rem;
  background: #fafafa;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  overflow: hidden;
}

.ha-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
  background: linear-gradient(135deg, #0088cc 0%, #00a3e0 100%);
  color: white;
}

.ha-section-title {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.ha-section-dates {
  font-size: 0.7rem;
  font-weight: 500;
  opacity: 0.95;
}

/* Stats Grid */
.ha-stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  background: #e5e5e5;
}

.ha-stat-item {
  background: white;
  padding: 0.6rem 0.5rem;
  text-align: center;
}

.ha-stat-label {
  font-size: 0.55rem;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  color: #666;
  margin-bottom: 0.2rem;
}

.ha-stat-value {
  font-size: 1rem;
  font-weight: 700;
  color: #0088cc;
}

.ha-stat-unit {
  font-size: 0.7rem;
  font-weight: 500;
  color: #888;
}

/* Projected items - same blue style */
.ha-stat-projected {
  background: #f0f9ff;
}

.ha-stat-projected .ha-stat-label {
  color: #006699;
}

.ha-stat-projected .ha-stat-value {
  color: #0088cc;
}

/* Responsive adjustments */
@media (max-width: 600px) {
  .ha-stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .ha-stat-value {
    font-size: 0.9rem;
  }
  
  .ha-section-header {
    flex-direction: column;
    gap: 0.2rem;
    text-align: center;
  }
}

@media (max-width: 400px) {
  .ha-stat-item {
    padding: 0.5rem 0.3rem;
  }
  
  .ha-stat-value {
    font-size: 0.85rem;
  }
  
  .ha-stat-label {
    font-size: 0.5rem;
  }
}

/* Bill Card - Collapsible */
.ha-bill-card-latest {
  border-left: 3px solid #03a9f4;
}

.ha-bill-header {
  cursor: pointer;
  user-select: none;
  transition: background-color 0.2s;
}
.ha-bill-header:hover {
  background: #e8e8e8;
}

.ha-bill-header-latest {
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
}
.ha-bill-header-latest:hover {
  background: linear-gradient(135deg, #bbdefb 0%, #90caf9 100%);
}

.ha-bill-header-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.ha-bill-cycle {
  font-weight: 600;
  color: #333;
}

.ha-bill-total-inline {
  font-weight: 700;
  color: #03a9f4;
  font-size: 0.85rem;
}

.ha-bill-header-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.ha-bill-due-badge {
  background: #ff9800;
  color: white;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.65rem;
  font-weight: 600;
}

.ha-expand-icon {
  color: #666;
  font-size: 0.7rem;
  transition: transform 0.2s;
}

.ha-expand-icon-sm {
  color: #888;
  font-size: 0.6rem;
}

.ha-bill-details {
  border-top: 1px solid #e0e0e0;
}

/* Payments Section */
.ha-payments-section {
  border-top: 1px solid #e0e0e0;
}

.ha-payments-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.75rem;
  background: #fafafa;
  cursor: pointer;
  user-select: none;
  transition: background-color 0.2s;
}
.ha-payments-header:hover {
  background: #f0f0f0;
}

.ha-payments-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #555;
}

.ha-payments-list {
  background: #f9f9f9;
}

/* PDF Button */
.ha-btn-pdf {
  background: #03a9f4;
  color: white;
  border: none;
  padding: 0.3rem 0.6rem;
  border-radius: 4px;
  font-size: 0.7rem;
  cursor: pointer;
  transition: background-color 0.2s;
}
.ha-btn-pdf:hover {
  background: #0288d1;
}
</style>
