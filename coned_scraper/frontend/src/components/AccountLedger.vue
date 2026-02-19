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
      <!-- Account Summary (header area - stays above scroll) -->
      <div class="ha-ledger-header">
      <div class="ha-card ha-card-summary">
        <div class="ha-card-header">
          <span class="ha-card-icon">💰</span>
          <span>Account Summary</span>
        </div>
        <div class="ha-card-content ha-summary-content">
          <div class="ha-summary-row">
            <div class="ha-summary-balance-box">
              <div class="ha-summary-label">Balance</div>
              <div class="ha-summary-value ha-balance-text">{{ ledgerData.account_balance || '—' }}</div>
            </div>
            <div class="ha-summary-info">
              <div class="ha-summary-label">Last Payment</div>
              <div class="ha-summary-value ha-payment-text">{{ ledgerData.latest_payment?.amount || '—' }}</div>
              <div class="ha-summary-sub">{{ ledgerData.latest_payment?.payment_date || '' }}</div>
            </div>
            <div class="ha-summary-info">
              <div class="ha-summary-label">Last Bill</div>
              <div class="ha-summary-value ha-bill-text">{{ ledgerData.latest_bill?.bill_total || '—' }}</div>
              <div class="ha-summary-sub">{{ ledgerData.latest_bill?.month_range || '' }}</div>
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

      <!-- Bill History Ledger (scrollable) -->
      <div class="ha-ledger-scroll">
      <div class="ha-card ha-card-ledger">
        <div class="ha-card-header">
          <span class="ha-card-icon">📋</span>
          <span>Bill History Ledger</span>
        </div>
        <div class="ha-card-content">
          <template v-if="ledgerData.bills.length > 0">
            <div v-for="bill in ledgerData.bills" :key="bill.id" class="ha-bill-card">
              <div class="ha-bill-header">
                Bill Cycle: {{ bill.bill_cycle_date }}
                {{ bill.month_range ? ` (${bill.month_range})` : '' }}
              </div>
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
                    class="ha-btn-link"
                    @click="openBillPdf(bill.id)"
                  >
                    📄 View PDF
                  </button>
                </div>
              </div>
              <template v-if="bill.payments && bill.payments.length">
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
                          <span v-if="payment.payee_status === 'confirmed' && payment.payee_name" class="ha-payee-badge">
                            {{ payment.payee_name }}
                          </span>
                          <span
                            v-else-if="payment.payee_status === 'pending'"
                            class="ha-payee-pending"
                            title="Searching for payee info..."
                          >
                            <span class="spinner-mini">⟳</span>
                            Loading payee...
                          </span>
                          <span
                            v-else-if="payment.payee_status === 'unverified'"
                            class="ha-payee-unverified"
                            title="Unassigned - edit in Settings → Payments"
                          >
                            Unassigned
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
              </template>
              <BillPayeeSummary
                :bill-id="bill.id"
                :bill-summaries="billSummaries"
              />
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
                        <span v-if="payment.payee_status === 'confirmed' && payment.payee_name" class="ha-payee-badge">
                          {{ payment.payee_name }}
                        </span>
                        <span v-else-if="payment.payee_status === 'pending'" class="ha-payee-pending">
                          <span class="spinner-mini">⟳</span>
                          Loading payee...
                        </span>
                        <span v-else-if="payment.payee_status === 'unverified'" class="ha-payee-unverified">
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
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
}

const ledgerData = ref<LedgerData | null>(null)
const screenshotPath = ref<string | null>(null)
const isLoading = ref(true)
const apiError = ref<string | null>(null)
const showScreenshotModal = ref(false)
const showPdfModal = ref(false)
const viewingBillId = ref<number | null>(null)
const pdfExists = ref(false)
const billSummaries = ref<Record<number, any>>({})

function formatDateShort(date: string) {
  return formatDate(date, { year: 'numeric', month: 'short', day: 'numeric' })
}

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

async function loadAllBillSummaries() {
  try {
    const res = await fetch(`${getApiBase()}/bills/all-summaries`)
    if (res.ok) {
      const data = await res.json()
      const summaries: Record<number, any> = {}
      for (const [key, value] of Object.entries(data.summaries || {})) {
        summaries[parseInt(key)] = value
      }
      billSummaries.value = summaries
    }
  } catch {
    // ignore
  }
}

let interval: ReturnType<typeof setInterval>
onMounted(() => {
  loadLedgerData()
  checkPdfExists()
  loadAllBillSummaries()
  interval = setInterval(() => {
    loadLedgerData()
    loadAllBillSummaries()
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
.ha-summary-balance-box {
  text-align: center;
  padding: 0.4rem 0.75rem;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-radius: 6px;
  flex: 0 0 auto;
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
</style>
