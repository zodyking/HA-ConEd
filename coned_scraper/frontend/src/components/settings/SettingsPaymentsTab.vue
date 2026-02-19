<template>
  <div class="ha-card">
    <!-- Payee Audit Modal -->
    <div v-if="auditPayment" class="ha-modal-overlay" @click.self="auditPayment = null">
      <div class="ha-modal ha-payee-audit-modal">
        <div class="ha-modal-header">
          <span>Assign Payee</span>
          <button type="button" class="ha-modal-close" @click="auditPayment = null">×</button>
        </div>
        <div class="ha-modal-body">
          <div class="ha-audit-payment-info">
            <strong>{{ auditPayment.amount }}</strong> • {{ auditPayment.payment_date }}
          </div>
          <div class="ha-form-group">
            <label class="ha-form-label">Payee</label>
            <select v-model="auditPayeeId" class="ha-form-input">
              <option value="">Unassigned</option>
              <option v-for="p in payeeUsers" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
          </div>
        </div>
        <div class="ha-modal-footer">
          <button type="button" class="ha-btn ha-btn-gray" @click="auditPayment = null">Cancel</button>
          <button type="button" class="ha-btn ha-btn-primary" @click="savePayeeAudit">Save</button>
        </div>
      </div>
    </div>
    <div class="ha-card-header">
      <span class="ha-card-icon">💳</span>
      <span>Payments Audit</span>
    </div>
    <div class="ha-card-content">
      <div class="ha-wipe-section">
        <div>
          <div class="ha-wipe-title">⚠️ Database Management</div>
          <div class="ha-wipe-desc">Clear all bills and payments. This cannot be undone.</div>
        </div>
        <div v-if="!showWipeConfirm">
          <button type="button" class="ha-btn ha-btn-red" @click="showWipeConfirm = true">Wipe Database</button>
        </div>
        <div v-else class="ha-wipe-confirm">
          <button type="button" class="ha-btn ha-btn-danger" @click="handleWipe">Confirm Wipe</button>
          <button type="button" class="ha-btn ha-btn-gray" @click="showWipeConfirm = false">Cancel</button>
        </div>
      </div>
      <div class="ha-stats">{{ bills.length }} bill(s) • {{ totalPayments }} payment(s)</div>
      <div v-if="isLoading" class="ha-loading">Loading...</div>
      <template v-else-if="bills.length || orphanPayments.length">
        <div v-for="bill in bills" :key="bill.id" class="ha-bill-block">
          <div class="ha-bill-header">
            <span class="ha-bill-badge">BILL</span>
            <span>{{ bill.month_range }}</span>
            <span class="ha-bill-total">{{ bill.bill_total }}</span>
          </div>
          <div v-for="(pay, i) in bill.payments" :key="pay.id" class="ha-payment-row ha-payment-clickable" draggable @dragstart="onDragStart($event, pay)" @click="openPayeeAudit(pay)">
            <span class="ha-drag">⋮⋮</span>
            <span class="ha-pay-amount">{{ pay.amount }}</span>
            <span class="ha-pay-date">{{ pay.payment_date }}</span>
            <span v-if="pay.payee_name" class="ha-payee">{{ pay.payee_name }}</span>
            <select :value="pay.bill_id ?? ''" @change="onChangeBill(pay.id, $event)" @click.stop>
              <option v-for="b in allBills" :key="b.id" :value="b.id">{{ b.month_range }}</option>
              <option value="">Unlinked</option>
            </select>
          </div>
        </div>
        <div v-if="orphanPayments.length" class="ha-orphan-block">
          <div class="ha-orphan-header">⚠️ Unlinked Payments</div>
          <div v-for="pay in orphanPayments" :key="pay.id" class="ha-payment-row ha-payment-clickable" @click="openPayeeAudit(pay)">
            <span class="ha-pay-amount">{{ pay.amount }}</span>
            <span class="ha-pay-date">{{ pay.payment_date }}</span>
            <select :value="pay.bill_id ?? ''" @change="onChangeBill(pay.id, $event)" @click.stop>
              <option v-for="b in allBills" :key="b.id" :value="b.id">{{ b.month_range }}</option>
              <option value="">Unlinked</option>
            </select>
          </div>
        </div>
      </template>
      <div v-else class="ha-empty">No data. Run the scraper.</div>
      <div v-if="message" :class="['ha-message', message.type]">{{ message.text }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getApiBase } from '../../lib/api-base'

interface Payment { id: number; payment_date: string; amount: string; description: string; bill_id: number | null; bill_month: string | null; bill_cycle: string | null; payee_name: string | null; payee_user_id: number | null; payee_status: string }
interface Bill { id: number; bill_cycle_date: string; month_range: string; bill_total: string; payments: Payment[] }
interface PayeeUser { id: number; name: string }

const bills = ref<Bill[]>([])
const orphanPayments = ref<Payment[]>([])
const allBills = ref<{ id: number; month_range: string }[]>([])
const payeeUsers = ref<PayeeUser[]>([])
const isLoading = ref(false)
const showWipeConfirm = ref(false)
const auditPayment = ref<Payment | null>(null)
const auditPayeeId = ref<number | string>('')
const message = ref<{ type: 'success' | 'error'; text: string } | null>(null)

const totalPayments = computed(() => {
  let n = orphanPayments.value.length
  bills.value.forEach((b) => (n += b.payments?.length || 0))
  return n
})

async function loadData() {
  isLoading.value = true
  try {
    const [payRes, billsRes] = await Promise.all([
      fetch(`${getApiBase()}/payee-users`),
      fetch(`${getApiBase()}/bills-with-payments`),
    ])
    if (payRes.ok) {
      const payData = await payRes.json()
      payeeUsers.value = payData.users || payData || []
    }
    if (billsRes.ok) {
      const d = await billsRes.json()
      bills.value = d.bills || []
      orphanPayments.value = d.orphan_payments || []
      allBills.value = (d.bills || []).map((b: Bill) => ({ id: b.id, month_range: b.month_range }))
    }
  } catch (e) { console.error(e) }
  finally { isLoading.value = false }
}

function openPayeeAudit(pay: Payment) {
  auditPayment.value = pay
  auditPayeeId.value = pay.payee_user_id ?? ''
}

async function savePayeeAudit() {
  if (!auditPayment.value) return
  const paymentId = auditPayment.value.id
  const userId = auditPayeeId.value
  try {
    if (userId === '' || userId === null) {
      const res = await fetch(`${getApiBase()}/payments/${paymentId}/attribution`, { method: 'DELETE' })
      if (res.ok) { await loadData(); message.value = { type: 'success', text: 'Payee cleared' }; auditPayment.value = null }
      else message.value = { type: 'error', text: 'Failed to clear payee' }
    } else {
      const res = await fetch(`${getApiBase()}/payments/attribute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payment_id: paymentId, user_id: Number(userId), method: 'manual' }),
      })
      if (res.ok) { await loadData(); message.value = { type: 'success', text: 'Payee updated' }; auditPayment.value = null }
      else message.value = { type: 'error', text: 'Failed to update payee' }
    }
  } catch {
    message.value = { type: 'error', text: 'Failed' }
  }
}

async function handleWipe() {
  try {
    const res = await fetch(`${getApiBase()}/data/wipe`, { method: 'DELETE' })
    if (res.ok) { const d = await res.json(); message.value = { type: 'success', text: `Wiped ${d.bills_deleted} bills, ${d.payments_deleted} payments` }; showWipeConfirm.value = false; await loadData() }
    else message.value = { type: 'error', text: 'Failed' }
  } catch { message.value = { type: 'error', text: 'Failed' } }
}

function onDragStart(_e: DragEvent, _pay: Payment) { /* drag-drop simplified */ }

async function onChangeBill(paymentId: number, ev: Event) {
  const t = ev.target as HTMLSelectElement
  const billId = t.value ? parseInt(t.value, 10) : null
  try {
    const res = await fetch(`${getApiBase()}/payments/${paymentId}/bill`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ bill_id: billId }) })
    if (res.ok) { await loadData(); message.value = { type: 'success', text: 'Updated' } }
    else message.value = { type: 'error', text: 'Failed' }
  } catch { message.value = { type: 'error', text: 'Failed' } }
}

onMounted(loadData)
</script>

<style scoped>
.ha-wipe-section { padding: 1rem; background: #fff3e0; border-radius: 8px; border: 1px solid #ffcc80; margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; }
.ha-wipe-title { font-weight: 600; color: #e65100; }
.ha-wipe-desc { font-size: 0.8rem; color: #666; }
.ha-wipe-confirm { display: flex; gap: 0.5rem; }
.ha-btn { padding: 0.5rem 1rem; border: none; border-radius: 6px; cursor: pointer; font-size: 0.85rem; }
.ha-btn-red { background: #f44336; color: white; }
.ha-btn-danger { background: #d32f2f; color: white; }
.ha-btn-gray { background: #e0e0e0; color: #333; }
.ha-stats { font-size: 0.8rem; color: #666; margin-bottom: 1rem; }
.ha-loading, .ha-empty { text-align: center; padding: 2rem; color: #666; }
.ha-bill-block { margin-bottom: 1rem; border: 1px solid #ddd; border-radius: 8px; border-left: 4px solid #03a9f4; overflow: hidden; }
.ha-bill-header { padding: 0.5rem 0.75rem; background: #e3f2fd; display: flex; align-items: center; gap: 0.5rem; }
.ha-bill-badge { background: #03a9f4; color: white; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.7rem; font-weight: 600; }
.ha-bill-total { margin-left: auto; font-weight: 600; color: #f44336; }
.ha-payment-row { padding: 0.5rem 0.75rem; display: flex; align-items: center; gap: 0.5rem; border-bottom: 1px solid #eee; font-size: 0.85rem; }
.ha-drag { color: #999; cursor: grab; }
.ha-pay-amount { font-weight: 500; color: #4caf50; }
.ha-payee { font-size: 0.75rem; color: #1565c0; }
.ha-orphan-block { border-left: 4px solid #ff9800; }
.ha-orphan-header { padding: 0.5rem 0.75rem; background: #fff3e0; font-weight: 600; color: #e65100; }
.ha-message { margin-top: 1rem; padding: 0.75rem; border-radius: 4px; }
.ha-message.success { background: #e8f5e9; color: #2e7d32; }
.ha-message.error { background: #ffebee; color: #c62828; }
.ha-payment-clickable { cursor: pointer; }
.ha-payment-clickable:hover { background: #f5f5f5; }
.ha-modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 1rem; }
.ha-modal { background: white; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.2); max-width: 360px; width: 100%; overflow: hidden; display: flex; flex-direction: column; }
.ha-modal-header { display: flex; justify-content: space-between; align-items: center; padding: 1rem 1.25rem; border-bottom: 1px solid #e0e0e0; font-weight: 600; }
.ha-modal-close { background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #666; padding: 0 0.25rem; line-height: 1; }
.ha-modal-close:hover { color: #333; }
.ha-modal-body { padding: 1.25rem; }
.ha-modal-footer { display: flex; justify-content: flex-end; gap: 0.5rem; padding: 1rem 1.25rem; border-top: 1px solid #e0e0e0; }
.ha-audit-payment-info { margin-bottom: 1rem; font-size: 0.95rem; }
.ha-btn-primary { background: #1976d2; color: white; }
.ha-btn-primary:hover { background: #1565c0; }
</style>
