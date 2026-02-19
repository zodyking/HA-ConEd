<template>
  <div class="ha-payees-payments">
    <!-- Payees Section -->
    <div class="ha-card ha-section-card">
      <div class="ha-card-header">
        <span class="ha-card-icon">👥</span>
        <span>Payees & Bill Split</span>
      </div>
      <div class="ha-card-content">
        <div class="ha-form-group">
          <label class="ha-form-label">Add User</label>
          <div class="ha-add-row">
            <input v-model="newUserName" type="text" class="ha-form-input" placeholder="Name" />
            <button type="button" class="ha-button ha-button-primary" :disabled="!newUserName.trim() || isLoading" @click="handleAddUser">Add</button>
          </div>
        </div>
        <div v-if="users.length" class="ha-users-list">
          <div v-for="user in users" :key="user.id" :class="['ha-user-card', { default: user.is_default }]" @click="openCardModal(user)">
            <div class="ha-user-row">
              <span class="ha-user-name">{{ user.name }}</span>
              <span v-if="user.is_default" class="ha-badge">DEFAULT</span>
              <div class="ha-user-actions" @click.stop>
                <button v-if="!user.is_default" type="button" class="ha-btn-sm ha-btn-green" @click="handleSetDefault(user.id)">Set Default</button>
                <button type="button" class="ha-btn-sm ha-btn-red" @click="handleDeleteUser(user.id)">Delete</button>
              </div>
            </div>
            <div class="ha-user-detail">
              <div v-if="!user.is_default" class="ha-responsibility">
                <span>Bill Share:</span>
                <input v-model.number="responsibilities[user.id]" type="number" min="0" max="100" @input="(e: Event) => responsibilities[user.id] = parseInt((e.target as HTMLInputElement).value) || 0" @click.stop />
                <span>%</span>
              </div>
              <div class="ha-cards">Cards: {{ user.cards?.length ? user.cards.map((c: string) => '*' + c).join(', ') : 'None' }} — click to manage</div>
            </div>
          </div>
        </div>

        <div v-if="totalResponsibility > 0 && Math.abs(totalResponsibility - 100) > 0.1" class="ha-warn">Total: {{ totalResponsibility.toFixed(1) }}% — must equal 100%</div>
        <button v-if="users.length" type="button" class="ha-button ha-button-primary" :disabled="isLoading || (totalResponsibility > 0 && Math.abs(totalResponsibility - 100) > 0.1)" @click="handleSaveResponsibilities">{{ isLoading ? 'Saving...' : 'Save Responsibilities' }}</button>

        <div v-if="unverifiedPayments.length && users.length" class="ha-unverified">
          <h4>Unverified Payments ({{ unverifiedPayments.length }})</h4>
          <div v-for="p in unverifiedPayments.slice(0, 5)" :key="p.id" class="ha-unv-row">
            <span>{{ p.amount }} — {{ p.payment_date }}</span>
            <select @change="handleAttribute(p.id, ($event.target as HTMLSelectElement).value)">
              <option value="">Assign...</option>
              <option v-for="u in users" :key="u.id" :value="u.id">{{ u.name }}</option>
            </select>
          </div>
        </div>
      </div>
    </div>

    <!-- Payments Audit Section -->
    <div class="ha-card ha-section-card">
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
        <div v-if="paymentsLoading" class="ha-loading">Loading...</div>
        <template v-else-if="bills.length || orphanPayments.length">
          <div v-for="bill in bills" :key="bill.id" class="ha-bill-block">
            <div class="ha-bill-header">
              <span class="ha-bill-badge">BILL</span>
              <span>{{ bill.month_range }}</span>
              <span class="ha-bill-total">{{ bill.bill_total }}</span>
            </div>
            <div v-for="pay in bill.payments" :key="pay.id" class="ha-payment-row ha-payment-clickable" @click="openPayeeAudit(pay)">
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
      </div>
    </div>

    <!-- Card Management Modal -->
    <div v-if="modalUser" class="ha-modal-overlay" @click.self="closeCardModal">
      <div class="ha-modal ha-card-modal">
        <div class="ha-modal-header">
          <h3>Manage Cards — {{ modalUser.name }}</h3>
          <button type="button" class="ha-modal-close" @click="closeCardModal">×</button>
        </div>
        <div class="ha-modal-content">
          <p class="ha-modal-desc">Add 4-digit card endings (e.g. 1234) to match payments to this payee.</p>
          <div class="ha-add-card-row">
            <input v-model="newCardDigits" type="text" class="ha-form-input" placeholder="Last 4 digits" maxlength="4" inputmode="numeric" pattern="[0-9]*" @keyup.enter="handleAddCard" />
            <input v-model="newCardLabel" type="text" class="ha-form-input" placeholder="Label (optional)" @keyup.enter="handleAddCard" />
            <button type="button" class="ha-button ha-button-primary" :disabled="!isValidCardDigits || cardLoading" @click="handleAddCard">{{ cardLoading ? '...' : 'Add' }}</button>
          </div>
          <div v-if="modalCards.length" class="ha-cards-list">
            <div v-for="c in modalCards" :key="c.id" class="ha-card-row">
              <span class="ha-card-display">*{{ c.card_last_four }}</span>
              <input v-if="editingCardId === c.id" v-model="editingLabel" type="text" class="ha-form-input ha-card-label-input" placeholder="Label" @keyup.enter="saveEditLabel(c.id)" />
              <span v-else class="ha-card-label">{{ c.card_label || '—' }}</span>
              <div class="ha-card-actions">
                <button v-if="editingCardId === c.id" type="button" class="ha-btn-sm ha-btn-green" @click="saveEditLabel(c.id)">Save</button>
                <button v-else type="button" class="ha-btn-sm" @click="startEditCard(c)">Edit</button>
                <button type="button" class="ha-btn-sm ha-btn-red" @click="handleDeleteCard(c.id)">Delete</button>
              </div>
            </div>
          </div>
          <div v-else class="ha-no-cards">No cards yet. Add one above.</div>
        </div>
      </div>
    </div>

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
              <option v-for="p in users" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
          </div>
        </div>
        <div class="ha-modal-footer">
          <button type="button" class="ha-btn ha-btn-gray" @click="auditPayment = null">Cancel</button>
          <button type="button" class="ha-btn ha-btn-primary" @click="savePayeeAudit">Save</button>
        </div>
      </div>
    </div>

    <div v-if="message" :class="['ha-message', message.type]">{{ message.text }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getApiBase } from '../../lib/api-base'

interface User { id: number; name: string; is_default: boolean; cards: string[]; responsibility_percent?: number }
interface CardItem { id: number; user_id: number; card_last_four: string; card_label: string | null }
interface Payment { id: number; payment_date: string; amount: string; description: string; bill_id: number | null; bill_month: string | null; bill_cycle: string | null; payee_name: string | null; payee_user_id: number | null; payee_status: string }
interface Bill { id: number; bill_cycle_date: string; month_range: string; bill_total: string; payments: Payment[] }

const users = ref<User[]>([])
const unverifiedPayments = ref<Payment[]>([])
const newUserName = ref('')
const responsibilities = ref<Record<number, number>>({})
const isLoading = ref(false)
const message = ref<{ type: 'success' | 'error'; text: string } | null>(null)

const bills = ref<Bill[]>([])
const orphanPayments = ref<Payment[]>([])
const allBills = ref<{ id: number; month_range: string }[]>([])
const paymentsLoading = ref(false)
const showWipeConfirm = ref(false)
const auditPayment = ref<Payment | null>(null)
const auditPayeeId = ref<number | string>('')

const modalUser = ref<User | null>(null)
const modalCards = ref<CardItem[]>([])
const newCardDigits = ref('')
const newCardLabel = ref('')
const cardLoading = ref(false)
const editingCardId = ref<number | null>(null)
const editingLabel = ref('')

const totalResponsibility = computed(() => Object.values(responsibilities.value).reduce((a, b) => a + (b || 0), 0))
const isValidCardDigits = computed(() => /^\d{4}$/.test(newCardDigits.value))
const totalPayments = computed(() => {
  let n = orphanPayments.value.length
  bills.value.forEach((b) => (n += b.payments?.length || 0))
  return n
})

async function loadUsers() {
  try {
    const res = await fetch(`${getApiBase()}/payee-users`)
    if (res.ok) {
      const d = await res.json()
      users.value = d.users || []
      const next: Record<number, number> = {}
      users.value.forEach((u) => { next[u.id] = u.responsibility_percent ?? 0 })
      responsibilities.value = next
    }
  } catch (e) { console.error(e) }
}

async function loadUnverified() {
  try {
    const res = await fetch(`${getApiBase()}/payments/unverified`)
    if (res.ok) {
      const d = await res.json()
      unverifiedPayments.value = d.payments || []
    }
  } catch (e) { console.error(e) }
}

async function loadPaymentsData() {
  paymentsLoading.value = true
  try {
    const res = await fetch(`${getApiBase()}/bills-with-payments`)
    if (res.ok) {
      const d = await res.json()
      bills.value = d.bills || []
      orphanPayments.value = d.orphan_payments || []
      allBills.value = (d.bills || []).map((b: Bill) => ({ id: b.id, month_range: b.month_range }))
    }
  } catch (e) { console.error(e) }
  finally { paymentsLoading.value = false }
}

async function handleAddUser() {
  if (!newUserName.value.trim()) return
  isLoading.value = true
  message.value = null
  try {
    const res = await fetch(`${getApiBase()}/payee-users`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: newUserName.value.trim(), is_default: users.value.length === 0 }) })
    if (res.ok) { newUserName.value = ''; await loadUsers(); await loadUnverified(); message.value = { type: 'success', text: 'User added' } }
    else { const e = await res.json().catch(() => ({})); message.value = { type: 'error', text: e.detail || 'Failed' } }
  } catch { message.value = { type: 'error', text: 'Failed to connect' } }
  finally { isLoading.value = false }
}

async function handleSetDefault(id: number) {
  try {
    const res = await fetch(`${getApiBase()}/payee-users/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ is_default: true }) })
    if (res.ok) { await loadUsers(); message.value = { type: 'success', text: 'Default updated' } }
  } catch { message.value = { type: 'error', text: 'Failed' } }
}

async function handleDeleteUser(id: number) {
  if (!confirm('Delete this payee?')) return
  try {
    const res = await fetch(`${getApiBase()}/payee-users/${id}`, { method: 'DELETE' })
    if (res.ok) { await loadUsers(); await loadUnverified(); message.value = { type: 'success', text: 'Deleted' } }
  } catch { message.value = { type: 'error', text: 'Failed' } }
}

async function handleSaveResponsibilities() {
  isLoading.value = true
  message.value = null
  try {
    const res = await fetch(`${getApiBase()}/payee-users/responsibilities`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ responsibilities: responsibilities.value }) })
    if (res.ok) message.value = { type: 'success', text: 'Saved!' }
    else message.value = { type: 'error', text: 'Failed' }
  } catch { message.value = { type: 'error', text: 'Failed' } }
  finally { isLoading.value = false }
}

async function handleAttribute(paymentId: number, userId: string) {
  if (!userId) return
  try {
    const res = await fetch(`${getApiBase()}/payments/attribute`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ payment_id: paymentId, user_id: parseInt(userId), method: 'manual' }) })
    if (res.ok) { await loadUnverified(); await loadPaymentsData(); message.value = { type: 'success', text: 'Assigned' } }
  } catch { message.value = { type: 'error', text: 'Failed' } }
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
      if (res.ok) { await loadPaymentsData(); await loadUnverified(); message.value = { type: 'success', text: 'Payee cleared' }; auditPayment.value = null }
      else message.value = { type: 'error', text: 'Failed to clear payee' }
    } else {
      const res = await fetch(`${getApiBase()}/payments/attribute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payment_id: paymentId, user_id: Number(userId), method: 'manual' }),
      })
      if (res.ok) { await loadPaymentsData(); await loadUnverified(); message.value = { type: 'success', text: 'Payee updated' }; auditPayment.value = null }
      else message.value = { type: 'error', text: 'Failed to update payee' }
    }
  } catch {
    message.value = { type: 'error', text: 'Failed' }
  }
}

async function handleWipe() {
  try {
    const res = await fetch(`${getApiBase()}/data/wipe`, { method: 'DELETE' })
    if (res.ok) {
      const d = await res.json()
      message.value = { type: 'success', text: `Wiped ${d.bills_deleted} bills, ${d.payments_deleted} payments` }
      showWipeConfirm.value = false
      await loadPaymentsData()
      await loadUsers()
      await loadUnverified()
    } else message.value = { type: 'error', text: 'Failed' }
  } catch { message.value = { type: 'error', text: 'Failed' } }
}

async function onChangeBill(paymentId: number, ev: Event) {
  const t = ev.target as HTMLSelectElement
  const billId = t.value ? parseInt(t.value, 10) : null
  try {
    const res = await fetch(`${getApiBase()}/payments/${paymentId}/bill`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ bill_id: billId }) })
    if (res.ok) { await loadPaymentsData(); message.value = { type: 'success', text: 'Updated' } }
    else message.value = { type: 'error', text: 'Failed' }
  } catch { message.value = { type: 'error', text: 'Failed' } }
}

async function openCardModal(user: User) {
  modalUser.value = user
  newCardDigits.value = ''
  newCardLabel.value = ''
  editingCardId.value = null
  try {
    const res = await fetch(`${getApiBase()}/payee-users/${user.id}/cards`)
    if (res.ok) {
      const d = await res.json()
      modalCards.value = d.cards || []
    }
  } catch (e) { console.error(e); modalCards.value = [] }
}

function closeCardModal() {
  modalUser.value = null
  modalCards.value = []
  loadUsers()
}

async function handleAddCard() {
  if (!modalUser.value || !isValidCardDigits.value) return
  cardLoading.value = true
  message.value = null
  try {
    const res = await fetch(`${getApiBase()}/user-cards`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: modalUser.value.id, card_last_four: newCardDigits.value, label: newCardLabel.value || null })
    })
    if (res.ok) {
      newCardDigits.value = ''
      newCardLabel.value = ''
      await openCardModal(modalUser.value)
      message.value = { type: 'success', text: 'Card added' }
    } else {
      const e = await res.json().catch(() => ({}))
      message.value = { type: 'error', text: e.detail || 'Failed to add card' }
    }
  } catch { message.value = { type: 'error', text: 'Failed to connect' } }
  finally { cardLoading.value = false }
}

async function handleDeleteCard(cardId: number) {
  if (!confirm('Remove this card?')) return
  try {
    const res = await fetch(`${getApiBase()}/user-cards/${cardId}`, { method: 'DELETE' })
    if (res.ok && modalUser.value) {
      await openCardModal(modalUser.value)
      message.value = { type: 'success', text: 'Card removed' }
    }
  } catch { message.value = { type: 'error', text: 'Failed' } }
}

function startEditCard(c: CardItem) {
  editingCardId.value = c.id
  editingLabel.value = c.card_label || ''
}

async function saveEditLabel(cardId: number) {
  try {
    const res = await fetch(`${getApiBase()}/user-cards/${cardId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ card_label: editingLabel.value })
    })
    if (res.ok && modalUser.value) {
      editingCardId.value = null
      await openCardModal(modalUser.value)
      message.value = { type: 'success', text: 'Label updated' }
    }
  } catch { message.value = { type: 'error', text: 'Failed' } }
}

onMounted(() => {
  loadUsers()
  loadUnverified()
  loadPaymentsData()
})
</script>

<style scoped>
.ha-payees-payments { display: flex; flex-direction: column; gap: 1.5rem; }
.ha-section-card .ha-card-content { padding: 1rem 1.25rem; }

.ha-add-row { display: flex; gap: 0.5rem; }
.ha-add-row input { flex: 1; }
.ha-users-list { display: flex; flex-direction: column; gap: 0.75rem; margin: 1rem 0; }
.ha-user-card { padding: 0.75rem; border-radius: 8px; border: 1px solid #e0e0e0; cursor: pointer; }
.ha-user-card.default { border-color: #03a9f4; background: #e3f2fd; }
.ha-user-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
.ha-user-name { font-weight: 600; }
.ha-badge { font-size: 0.65rem; background: #03a9f4; color: white; padding: 0.15rem 0.4rem; border-radius: 3px; }
.ha-user-actions { display: flex; gap: 0.5rem; }
.ha-btn-sm { padding: 0.3rem 0.6rem; font-size: 0.7rem; border: none; border-radius: 4px; cursor: pointer; }
.ha-btn-green { background: #4caf50; color: white; }
.ha-btn-red { background: #f44336; color: white; }
.ha-responsibility { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }
.ha-responsibility input { width: 60px; }
.ha-warn { color: #e65100; font-size: 0.85rem; margin: 0.5rem 0; }
.ha-unverified { margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #e0e0e0; }
.ha-unverified h4 { margin: 0 0 0.75rem 0; font-size: 0.95rem; }
.ha-unv-row { display: flex; justify-content: space-between; align-items: center; padding: 0.5rem; background: #fff3e0; border-radius: 6px; margin-bottom: 0.5rem; }

.ha-wipe-section { padding: 1rem; background: #fff3e0; border-radius: 8px; border: 1px solid #ffcc80; margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; }
.ha-wipe-title { font-weight: 600; color: #e65100; }
.ha-wipe-desc { font-size: 0.8rem; color: #666; }
.ha-wipe-confirm { display: flex; gap: 0.5rem; }
.ha-btn { padding: 0.5rem 1rem; border: none; border-radius: 6px; cursor: pointer; font-size: 0.85rem; }
.ha-btn-danger { background: #d32f2f; color: white; }
.ha-btn-gray { background: #e0e0e0; color: #333; }
.ha-stats { font-size: 0.8rem; color: #666; margin-bottom: 1rem; }
.ha-loading, .ha-empty { text-align: center; padding: 2rem; color: #666; }
.ha-bill-block { margin-bottom: 1rem; border: 1px solid #ddd; border-radius: 8px; border-left: 4px solid #03a9f4; overflow: hidden; }
.ha-bill-header { padding: 0.5rem 0.75rem; background: #e3f2fd; display: flex; align-items: center; gap: 0.5rem; }
.ha-bill-badge { background: #03a9f4; color: white; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.7rem; font-weight: 600; }
.ha-bill-total { margin-left: auto; font-weight: 600; color: #f44336; }
.ha-payment-row { padding: 0.5rem 0.75rem; display: flex; align-items: center; gap: 0.5rem; border-bottom: 1px solid #eee; font-size: 0.85rem; }
.ha-pay-amount { font-weight: 500; color: #4caf50; }
.ha-payee { font-size: 0.75rem; color: #1565c0; }
.ha-orphan-block { border-left: 4px solid #ff9800; }
.ha-orphan-header { padding: 0.5rem 0.75rem; background: #fff3e0; font-weight: 600; color: #e65100; }
.ha-payment-clickable { cursor: pointer; }
.ha-payment-clickable:hover { background: #f5f5f5; }

.ha-message { margin-top: 1rem; padding: 0.75rem; border-radius: 4px; }
.ha-message.success { background: #e8f5e9; color: #2e7d32; }
.ha-message.error { background: #ffebee; color: #c62828; }

/* Modals */
.ha-modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 1rem; }
.ha-modal { background: white; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.2); max-width: 420px; width: 100%; max-height: 90vh; overflow: hidden; display: flex; flex-direction: column; }
.ha-payee-audit-modal { max-width: 360px; }
.ha-modal-header { display: flex; justify-content: space-between; align-items: center; padding: 1rem 1.25rem; border-bottom: 1px solid #e0e0e0; font-weight: 600; }
.ha-modal-header h3 { margin: 0; font-size: 1.1rem; }
.ha-modal-close { background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #666; padding: 0 0.25rem; line-height: 1; }
.ha-modal-close:hover { color: #333; }
.ha-modal-content, .ha-modal-body { padding: 1.25rem; overflow-y: auto; }
.ha-modal-desc { font-size: 0.9rem; color: #666; margin: 0 0 1rem 0; }
.ha-modal-footer { display: flex; justify-content: flex-end; gap: 0.5rem; padding: 1rem 1.25rem; border-top: 1px solid #e0e0e0; }
.ha-add-card-row { display: flex; gap: 0.5rem; margin-bottom: 1rem; flex-wrap: wrap; }
.ha-add-card-row input:first-of-type { width: 80px; }
.ha-add-card-row input:nth-of-type(2) { flex: 1; min-width: 100px; }
.ha-cards-list { display: flex; flex-direction: column; gap: 0.5rem; }
.ha-card-row { display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem; background: #f5f5f5; border-radius: 6px; }
.ha-card-display { font-weight: 600; font-family: monospace; min-width: 50px; }
.ha-card-label { flex: 1; font-size: 0.9rem; color: #666; }
.ha-card-label-input { flex: 1; max-width: 120px; }
.ha-card-actions { display: flex; gap: 0.25rem; }
.ha-no-cards { font-size: 0.9rem; color: #999; padding: 0.75rem 0; }
.ha-audit-payment-info { margin-bottom: 1rem; font-size: 0.95rem; }
.ha-btn-primary { background: #1976d2; color: white; }
.ha-btn-primary:hover { background: #1565c0; }
</style>
