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
          <label class="ha-form-label">Add Payee</label>
          <div class="ha-add-row">
            <button v-if="isAddon" type="button" class="ha-button ha-button-secondary" :disabled="haUsersLoading" @click="showHaUserModal = true; loadHaUsersAndServices()">
              {{ haUsersLoading ? 'Loading...' : '+ Add from HA Users' }}
            </button>
            <input v-model="newUserName" type="text" class="ha-form-input" placeholder="Or enter name manually" />
            <button type="button" class="ha-button ha-button-primary" :disabled="!newUserName.trim() || isLoading" @click="handleAddUser">Add</button>
          </div>
        </div>
        <div v-if="users.length" class="ha-users-list">
          <div v-for="user in users" :key="user.id" class="ha-user-card">
            <div class="ha-user-row">
              <div v-if="editingNameId === user.id" class="ha-user-name-edit" @click.stop>
                <input
                  ref="renameInputRef"
                  v-model="editingNameValue"
                  type="text"
                  class="ha-form-input ha-rename-input"
                  @blur="saveRename(user.id)"
                  @keydown.enter="saveRename(user.id)"
                  @keydown.escape="cancelRename"
                />
              </div>
              <span
                v-else
                class="ha-user-name ha-user-name-clickable"
                title="Click to rename"
                @click="startRename(user)"
              >{{ user.name }}</span>
              <div class="ha-user-actions" @click.stop>
                <button type="button" class="ha-btn-sm ha-btn-red" @click="handleDeleteUser(user.id)">Delete</button>
              </div>
            </div>
            <div class="ha-user-detail">
              <div class="ha-responsibility">
                <span>Bill Share:</span>
                <input v-model.number="responsibilities[user.id]" type="number" min="0" max="100" @input="(e: Event) => responsibilities[user.id] = parseInt((e.target as HTMLInputElement).value) || 0" @click.stop />
                <span>%</span>
              </div>
              <!-- Notification settings -->
              <div v-if="isAddon" class="ha-notify-row" @click.stop>
                <label class="ha-notify-toggle">
                  <input type="checkbox" :checked="user.notifications_enabled" @change="toggleNotifications(user)" />
                  <span>Notifications</span>
                </label>
                <div v-if="editingPayeeId === user.id" class="ha-notify-edit">
                  <select v-model="editingNotifyService" class="ha-form-input ha-notify-select">
                    <option value="">No device</option>
                    <option v-for="svc in notifyServices" :key="svc.service" :value="svc.service">{{ svc.friendly_name }}</option>
                  </select>
                  <button type="button" class="ha-btn-sm ha-btn-green" @click="saveNotifyService(user.id)">Save</button>
                  <button type="button" class="ha-btn-sm" @click="editingPayeeId = null">Cancel</button>
                </div>
                <button v-else type="button" class="ha-notify-device" @click="openNotifyEdit(user)">
                  📱 {{ user.notify_service ? notifyServices.find(s => s.service === user.notify_service)?.friendly_name || user.notify_service : 'Set device' }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="ha-breakdown-setting" style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #e0e0e0;">
          <label class="ha-breakdown-label">
            <input v-model="breakdownShowRollover" type="checkbox" :disabled="breakdownSaving" @change="handleBreakdownChange" />
            {{ breakdownShowRollover ? 'Rollover' : 'Bill only' }}
          </label>
          <div class="ha-breakdown-desc">Breakdown view in ledger: show current bill only, or cumulative rollover</div>
        </div>
        <div v-if="totalResponsibility > 0 && Math.abs(totalResponsibility - 100) > 0.1" class="ha-warn">Total: {{ totalResponsibility.toFixed(1) }}% — must equal 100%</div>
        <button v-if="users.length" type="button" class="ha-button ha-button-primary" :disabled="isLoading || (totalResponsibility > 0 && Math.abs(totalResponsibility - 100) > 0.1)" @click="handleSaveResponsibilities">{{ isLoading ? 'Saving...' : 'Save Responsibilities' }}</button>
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
        <div class="ha-relink-section" style="margin-top: 1rem;">
          <div>
            <div class="ha-wipe-title">Relink Payments</div>
            <div class="ha-wipe-desc">Assign unlinked payments to bills by date (payment after bill posted, before next bill).</div>
          </div>
          <button type="button" class="ha-btn ha-btn-primary" :disabled="relinkLoading" @click="handleRelink">
            {{ relinkLoading ? 'Linking...' : 'Relink Payments to Bills' }}
          </button>
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
              <button
                v-if="pay.payee_status === 'unverified'"
                type="button"
                class="ha-unverified-badge"
                title="Unverified - click to assign payee"
                @click.stop="openPayeeAudit(pay)"
              >Unverified</button>
              <button
                v-else-if="pay.payee_status === 'needs_admin_verification'"
                type="button"
                class="ha-unverified-badge"
                title="Multiple payees claimed - click to resolve"
                @click.stop="openPayeeAudit(pay)"
              >Needs Admin Verification</button>
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
              <span v-if="pay.payee_name" class="ha-payee">{{ pay.payee_name }}</span>
              <button
                v-if="pay.payee_status === 'unverified'"
                type="button"
                class="ha-unverified-badge"
                title="Unverified - click to assign payee"
                @click.stop="openPayeeAudit(pay)"
              >Unverified</button>
              <button
                v-else-if="pay.payee_status === 'needs_admin_verification'"
                type="button"
                class="ha-unverified-badge"
                title="Multiple payees claimed - click to resolve"
                @click.stop="openPayeeAudit(pay)"
              >Needs Admin Verification</button>
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

    <!-- HA User Selection Modal -->
    <div v-if="showHaUserModal" class="ha-modal-overlay" @click.self="showHaUserModal = false">
      <div class="ha-modal ha-ha-user-modal">
        <div class="ha-modal-header">
          <h3>Add Payee from Home Assistant</h3>
          <button type="button" class="ha-modal-close" @click="showHaUserModal = false">×</button>
        </div>
        <div class="ha-modal-content">
          <div v-if="haUsersLoading" class="ha-loading">Loading HA users...</div>
          <div v-else-if="haUsers.length === 0" class="ha-empty">No Home Assistant users found.</div>
          <div v-else class="ha-ha-users-list">
            <div
              v-for="haUser in haUsers"
              :key="haUser.id"
              :class="['ha-ha-user-item', { disabled: isUserAlreadyAdded(haUser.id) }]"
              @click="!isUserAlreadyAdded(haUser.id) && handleAddHaUser(haUser)"
            >
              <div class="ha-ha-user-info">
                <span class="ha-ha-user-name">{{ haUser.name }}</span>
                <span v-if="haUser.is_admin" class="ha-badge ha-badge-admin">Admin</span>
                <span v-if="isUserAlreadyAdded(haUser.id)" class="ha-badge ha-badge-added">Already added</span>
              </div>
              <span v-if="haUser.username" class="ha-ha-user-username">@{{ haUser.username }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="message" :class="['ha-message', message.type]">{{ message.text }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { getApiBase } from '../../lib/api-base'

interface User { 
  id: number
  name: string
  ha_user_id?: string | null
  notify_service?: string | null
  notifications_enabled?: boolean
  is_default: boolean
  responsibility_percent?: number 
}
interface Payment { id: number; payment_date: string; amount: string; description: string; bill_id: number | null; bill_month: string | null; bill_cycle: string | null; payee_name: string | null; payee_user_id: number | null; payee_status: string }
interface Bill { id: number; bill_cycle_date: string; month_range: string; bill_total: string; payments: Payment[] }
interface HaUser { id: string; name: string; username?: string; is_admin?: boolean; is_active?: boolean }
interface NotifyService { service: string; friendly_name: string; full_service: string }

const users = ref<User[]>([])
const newUserName = ref('')
const responsibilities = ref<Record<number, number>>({})
const isLoading = ref(false)
const message = ref<{ type: 'success' | 'error'; text: string } | null>(null)

const bills = ref<Bill[]>([])
const orphanPayments = ref<Payment[]>([])
const allBills = ref<{ id: number; month_range: string }[]>([])
const paymentsLoading = ref(false)
const relinkLoading = ref(false)
const showWipeConfirm = ref(false)
const auditPayment = ref<Payment | null>(null)
const auditPayeeId = ref<number | string>('')

const breakdownShowRollover = ref(false)
const breakdownSaving = ref(false)

// HA user and notify service state
const showHaUserModal = ref(false)
const haUsers = ref<HaUser[]>([])
const notifyServices = ref<NotifyService[]>([])
const haUsersLoading = ref(false)
const isAddon = ref(false)
const editingPayeeId = ref<number | null>(null)
const editingNotifyService = ref<string>('')

const totalResponsibility = computed(() => Object.values(responsibilities.value).reduce((a, b) => a + (b || 0), 0))
const totalPayments = computed(() => {
  let n = orphanPayments.value.length
  bills.value.forEach((b) => (n += b.payments?.length || 0))
  return n
})

async function loadAppSettings() {
  try {
    const res = await fetch(`${getApiBase()}/app-settings`)
    if (res.ok) {
      const d = await res.json()
      breakdownShowRollover.value = d.breakdown_show_rollover === true
    }
  } catch { /* ignore */ }
}

async function handleBreakdownChange() {
  breakdownSaving.value = true
  try {
    const res = await fetch(`${getApiBase()}/app-settings/payee-preferences`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ breakdown_show_rollover: breakdownShowRollover.value })
    })
    if (!res.ok) {
      const e = await res.json().catch(() => ({}))
      message.value = { type: 'error', text: e.detail || 'Failed to save breakdown setting' }
    }
  } catch {
    message.value = { type: 'error', text: 'Failed to connect' }
  } finally {
    breakdownSaving.value = false
  }
}

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
    const res = await fetch(`${getApiBase()}/payee-users`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: newUserName.value.trim(), is_default: false }) })
    if (res.ok) { newUserName.value = ''; await loadUsers(); message.value = { type: 'success', text: 'User added' } }
    else { const e = await res.json().catch(() => ({})); message.value = { type: 'error', text: e.detail || 'Failed' } }
  } catch { message.value = { type: 'error', text: 'Failed to connect' } }
  finally { isLoading.value = false }
}

const editingNameId = ref<number | null>(null)
const editingNameValue = ref('')
const renameInputRef = ref<HTMLInputElement | null>(null)

function startRename(user: User) {
  editingNameId.value = user.id
  editingNameValue.value = user.name
  nextTick(() => {
    const r = renameInputRef.value
    const el = Array.isArray(r) ? r[0] : r
    if (el instanceof HTMLInputElement) el.focus()
  })
}

function cancelRename() {
  editingNameId.value = null
  editingNameValue.value = ''
}

async function saveRename(userId: number) {
  const name = editingNameValue.value.trim()
  if (!name) {
    cancelRename()
    return
  }
  try {
    const res = await fetch(`${getApiBase()}/payee-users/${userId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    })
    if (res.ok) {
      await loadUsers()
      message.value = { type: 'success', text: 'Name updated' }
    } else {
      const e = await res.json().catch(() => ({}))
      message.value = { type: 'error', text: e.detail || 'Failed to rename' }
    }
  } catch {
    message.value = { type: 'error', text: 'Failed to connect' }
  } finally {
    cancelRename()
  }
}

async function handleDeleteUser(id: number) {
  if (!confirm('Delete this payee?')) return
  try {
    const res = await fetch(`${getApiBase()}/payee-users/${id}`, { method: 'DELETE' })
    if (res.ok) { await loadUsers(); message.value = { type: 'success', text: 'Deleted' } }
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
      if (res.ok) { await loadPaymentsData(); message.value = { type: 'success', text: 'Payee cleared' }; auditPayment.value = null }
      else message.value = { type: 'error', text: 'Failed to clear payee' }
    } else {
      const res = await fetch(`${getApiBase()}/payments/attribute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payment_id: paymentId, user_id: Number(userId), method: 'manual' }),
      })
      if (res.ok) { await loadPaymentsData(); message.value = { type: 'success', text: 'Payee updated' }; auditPayment.value = null }
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
    } else message.value = { type: 'error', text: 'Failed' }
  } catch { message.value = { type: 'error', text: 'Failed' } }
}

async function handleRelink() {
  relinkLoading.value = true
  message.value = null
  try {
    const res = await fetch(`${getApiBase()}/bills/relink-payments`, { method: 'POST' })
    if (res.ok) {
      const d = await res.json()
      message.value = { type: 'success', text: d.message || `Linked ${d.updated} payments to bills` }
      await loadPaymentsData()
    } else {
      const e = await res.json().catch(() => ({}))
      message.value = { type: 'error', text: e.detail || 'Failed to relink' }
    }
  } catch { message.value = { type: 'error', text: 'Failed to connect' } }
  finally { relinkLoading.value = false }
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

async function loadHaUsersAndServices() {
  haUsersLoading.value = true
  try {
    const [usersRes, servicesRes] = await Promise.all([
      fetch(`${getApiBase()}/ha-users`),
      fetch(`${getApiBase()}/ha-notify-services`)
    ])
    if (usersRes.ok) {
      const d = await usersRes.json()
      haUsers.value = d.users || []
      isAddon.value = d.is_addon === true
    }
    if (servicesRes.ok) {
      const d = await servicesRes.json()
      notifyServices.value = d.services || []
    }
  } catch (e) {
    console.error('Failed to load HA data:', e)
  } finally {
    haUsersLoading.value = false
  }
}

async function handleAddHaUser(haUser: HaUser) {
  isLoading.value = true
  message.value = null
  try {
    const res = await fetch(`${getApiBase()}/payee-users`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
        name: haUser.name,
        ha_user_id: haUser.id,
        notifications_enabled: true,
        is_default: false
      })
    })
    if (res.ok) {
      showHaUserModal.value = false
      await loadUsers()
      message.value = { type: 'success', text: `Added ${haUser.name}` }
    } else {
      const e = await res.json().catch(() => ({}))
      message.value = { type: 'error', text: e.detail || 'Failed to add user' }
    }
  } catch {
    message.value = { type: 'error', text: 'Failed to connect' }
  } finally {
    isLoading.value = false
  }
}

function openNotifyEdit(user: User) {
  editingPayeeId.value = user.id
  editingNotifyService.value = user.notify_service || ''
}

async function saveNotifyService(userId: number) {
  try {
    const res = await fetch(`${getApiBase()}/payee-users/${userId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notify_service: editingNotifyService.value || null })
    })
    if (res.ok) {
      editingPayeeId.value = null
      await loadUsers()
      message.value = { type: 'success', text: 'Notification device updated' }
    } else {
      message.value = { type: 'error', text: 'Failed to save' }
    }
  } catch {
    message.value = { type: 'error', text: 'Failed to connect' }
  }
}

async function toggleNotifications(user: User) {
  try {
    const res = await fetch(`${getApiBase()}/payee-users/${user.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notifications_enabled: !user.notifications_enabled })
    })
    if (res.ok) {
      await loadUsers()
    }
  } catch {
    message.value = { type: 'error', text: 'Failed to update' }
  }
}

function isUserAlreadyAdded(haUserId: string): boolean {
  return users.value.some(u => u.ha_user_id === haUserId)
}

onMounted(() => {
  loadUsers()
  loadPaymentsData()
  loadAppSettings()
  loadHaUsersAndServices()
})
</script>

<style scoped>
.ha-payees-payments { display: flex; flex-direction: column; gap: 1.5rem; }
.ha-section-card .ha-card-content { padding: 1rem 1.25rem; }

.ha-add-row { display: flex; gap: 0.5rem; }
.ha-add-row input { flex: 1; }
.ha-users-list { display: flex; flex-direction: column; gap: 0.75rem; margin: 1rem 0; }
.ha-user-card { padding: 0.75rem; border-radius: 8px; border: 1px solid #e0e0e0; }
.ha-user-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
.ha-user-name { font-weight: 600; }
.ha-user-name-clickable { cursor: pointer; padding: 0.15rem 0; border-radius: 4px; }
.ha-user-name-clickable:hover { background: #e8f4fd; color: #1976d2; }
.ha-user-name-edit { display: inline-block; min-width: 120px; }
.ha-rename-input { font-weight: 600; padding: 0.2rem 0.4rem; width: 100%; }
.ha-badge { font-size: 0.65rem; background: #03a9f4; color: white; padding: 0.15rem 0.4rem; border-radius: 3px; }
.ha-user-actions { display: flex; gap: 0.5rem; }
.ha-btn-sm { padding: 0.3rem 0.6rem; font-size: 0.7rem; border: none; border-radius: 4px; cursor: pointer; }
.ha-btn-green { background: #4caf50; color: white; }
.ha-btn-red { background: #f44336; color: white; }
.ha-responsibility { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }
.ha-responsibility input { width: 60px; }
.ha-breakdown-setting { }
.ha-breakdown-label { display: inline-flex; align-items: center; gap: 0.5rem; cursor: pointer; font-weight: 500; }
.ha-breakdown-desc { font-size: 0.8rem; color: #666; margin-top: 0.25rem; margin-left: 1.5rem; }
.ha-warn { color: #e65100; font-size: 0.85rem; margin: 0.5rem 0; }

.ha-unverified-badge {
  font-size: 0.65rem;
  background: #fff3e0;
  color: #e65100;
  padding: 0.15rem 0.4rem;
  border-radius: 3px;
  border: 1px solid #ffcc80;
  cursor: pointer;
}
.ha-unverified-badge:hover {
  background: #ffe0b2;
}

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
.ha-audit-payment-info { margin-bottom: 1rem; font-size: 0.95rem; }
.ha-btn-primary { background: #1976d2; color: white; }
.ha-btn-primary:hover { background: #1565c0; }

/* HA User Modal */
.ha-ha-user-modal { max-width: 400px; }
.ha-ha-users-list { display: flex; flex-direction: column; gap: 0.5rem; max-height: 300px; overflow-y: auto; }
.ha-ha-user-item { padding: 0.75rem; border: 1px solid #e0e0e0; border-radius: 8px; cursor: pointer; transition: all 0.15s; }
.ha-ha-user-item:hover:not(.disabled) { background: #e3f2fd; border-color: #03a9f4; }
.ha-ha-user-item.disabled { opacity: 0.5; cursor: not-allowed; background: #f5f5f5; }
.ha-ha-user-info { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem; }
.ha-ha-user-name { font-weight: 600; }
.ha-ha-user-username { font-size: 0.8rem; color: #666; }
.ha-badge-admin { background: #9c27b0; }
.ha-badge-added { background: #9e9e9e; }

/* Notification settings */
.ha-notify-row { display: flex; align-items: center; gap: 0.75rem; margin-top: 0.5rem; flex-wrap: wrap; }
.ha-notify-toggle { display: flex; align-items: center; gap: 0.35rem; font-size: 0.8rem; cursor: pointer; }
.ha-notify-toggle input { cursor: pointer; }
.ha-notify-device { font-size: 0.75rem; color: #1976d2; background: #e3f2fd; border: 1px solid #90caf9; padding: 0.25rem 0.5rem; border-radius: 4px; cursor: pointer; }
.ha-notify-device:hover { background: #bbdefb; }
.ha-notify-edit { display: flex; gap: 0.35rem; align-items: center; }
.ha-notify-select { font-size: 0.8rem; padding: 0.25rem 0.5rem; max-width: 180px; }

/* Button secondary */
.ha-button-secondary { background: #e3f2fd; color: #1976d2; border: 1px solid #90caf9; }
.ha-button-secondary:hover { background: #bbdefb; }
</style>
