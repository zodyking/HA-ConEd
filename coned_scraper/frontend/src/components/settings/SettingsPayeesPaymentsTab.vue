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
              <!-- Link HA User (required for unclaim/petition in Account Ledger) -->
              <div v-if="isAddon" class="ha-link-row" @click.stop>
                <span class="ha-link-label">Link HA User:</span>
                <button
                  type="button"
                  class="ha-link-btn"
                  :title="user.ha_user_id ? 'Change linked HA user' : 'Link to HA user for unclaim/petition in Account Ledger'"
                  @click="openLinkHaUserModal(user)"
                >
                  {{ getLinkedHaUserName(user) || 'Not linked' }}
                  <span class="ha-link-action">{{ user.ha_user_id ? 'Change' : 'Link' }}</span>
                </button>
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

        <section class="ha-rollover-clear" aria-labelledby="calc-switch-heading">
          <h3 id="calc-switch-heading" class="ha-rollover-clear-title">How payee shares are counted</h3>
          <p class="ha-breakdown-desc ha-rollover-clear-desc">
            Bill only fits a household where everyone pays their share in full each month. Each bill stands on its own.
          </p>
          <p class="ha-breakdown-desc ha-rollover-clear-desc">
            Rollover fits a household that needs an unpaid amount carried onto the next bill. It starts clean at the month you choose, and earlier bills stay as they were.
          </p>
          <p v-if="switchError" class="ha-rollover-clear-error" role="alert">{{ switchError }}</p>
          <p v-if="switchStatus === 'loading'" class="ha-rollover-clear-empty">Loading calculation switches…</p>
          <ul v-else-if="calculationSwitches.length" class="ha-switch-list">
            <li v-for="item in calculationSwitches" :key="item.month" class="ha-switch-item">
              <span>{{ item.mode === 'rollover' ? 'Rollover' : 'Bill only' }} starts {{ item.label || formatMonthLabel(item.month) }}</span>
              <button type="button" class="ha-rollover-undo" :disabled="switchSaving" @click="removeCalculationSwitch(item.month)">
                Remove
              </button>
            </li>
          </ul>
          <p v-else-if="switchStatus === 'ready'" class="ha-rollover-clear-empty">
            No switches yet. Every bill uses bill only until you add one.
          </p>
          <form v-if="switchStatus === 'ready' && rolloverMonthOptions.length" class="ha-rollover-clear-form" @submit.prevent="addCalculationSwitch">
            <label class="ha-rollover-clear-label" for="calc-switch-month">Starting month</label>
            <select id="calc-switch-month" v-model="selectedRolloverMonth" :disabled="switchSaving">
              <option v-for="opt in rolloverMonthOptions" :key="opt.month" :value="opt.month">
                {{ opt.optionLabel }}
              </option>
            </select>
            <label class="ha-rollover-clear-label" for="calc-switch-mode">Method</label>
            <select id="calc-switch-mode" v-model="selectedSwitchMode" :disabled="switchSaving">
              <option value="rollover">Rollover</option>
              <option value="bill_only">Bill only</option>
            </select>
            <button type="submit" class="ha-rollover-clear-btn" :disabled="switchSaving || !selectedRolloverMonth">
              {{ switchSaving ? 'Saving…' : `Start ${selectedSwitchMode === 'rollover' ? 'rollover' : 'bill only'} ${selectedRolloverLabel}` }}
            </button>
          </form>
          <p v-else-if="switchStatus === 'ready'" class="ha-rollover-clear-empty">No bill months available yet.</p>
        </section>
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

    <!-- Link HA User Modal -->
    <div v-if="showLinkHaUserModal" class="ha-modal-overlay" @click.self="showLinkHaUserModal = false; linkHaUserPayeeId = null">
      <div class="ha-modal ha-ha-user-modal">
        <div class="ha-modal-header">
          <h3>Link to HA User</h3>
          <button type="button" class="ha-modal-close" @click="showLinkHaUserModal = false; linkHaUserPayeeId = null">×</button>
        </div>
        <div class="ha-modal-content">
          <p class="ha-modal-desc">Select an HA user to link to this payee. Linked payees can unclaim or petition payments in the Account Ledger.</p>
          <div
            v-if="linkHaUserPayeeId != null && (users.find(u => u.id === linkHaUserPayeeId)?.ha_user_id)"
            class="ha-unlink-row"
          >
            <button type="button" class="ha-btn ha-btn-gray" @click="unlinkHaUserFromModal">Unlink HA User</button>
          </div>
          <div v-if="haUsersLoading" class="ha-loading">Loading HA users...</div>
          <div v-else-if="haUsers.length === 0" class="ha-empty">No Home Assistant users found.</div>
          <div v-else class="ha-ha-users-list">
            <div
              v-for="haUser in haUsers"
              :key="haUser.id"
              :class="['ha-ha-user-item', { disabled: linkHaUserPayeeId != null && isHaUserLinkedToOtherPayee(haUser.id, linkHaUserPayeeId) }]"
              @click="linkHaUserPayeeId != null && !isHaUserLinkedToOtherPayee(haUser.id, linkHaUserPayeeId) && handleLinkHaUser(haUser)"
            >
              <div class="ha-ha-user-info">
                <span class="ha-ha-user-name">{{ haUser.name }}</span>
                <span v-if="haUser.is_admin" class="ha-badge ha-badge-admin">Admin</span>
                <span v-if="linkHaUserPayeeId != null && isHaUserLinkedToOtherPayee(haUser.id, linkHaUserPayeeId)" class="ha-badge ha-badge-added">Linked to another payee</span>
              </div>
              <span v-if="haUser.username" class="ha-ha-user-username">@{{ haUser.username }}</span>
            </div>
          </div>
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

    <div
      v-if="rolloverConfirmOpen"
      class="ha-modal-overlay"
      @click.self="rolloverConfirmOpen = false"
      @keydown.esc.prevent="rolloverConfirmOpen = false"
    >
      <div
        class="ha-modal ha-rollover-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="rollover-clear-title"
      >
        <div class="ha-modal-header ha-rollover-dialog-header">
          <span id="rollover-clear-title">Clear rollover balance</span>
        </div>
        <div class="ha-modal-body">
          <p>
            Clear the rollover balance starting {{ selectedRolloverLabel }}? Bills from that month on start from zero.
            Earlier bills stay the same. You can undo this.
          </p>
        </div>
        <div class="ha-modal-footer ha-rollover-dialog-actions">
          <button type="button" class="ha-btn ha-btn-gray ha-rollover-dialog-btn" @click="rolloverConfirmOpen = false">
            Cancel
          </button>
          <button
            ref="rolloverConfirmButton"
            type="button"
            class="ha-rollover-clear-btn ha-rollover-dialog-btn"
            :disabled="rolloverClearSaving"
            @click="applyRolloverClear"
          >
            Clear rollover starting {{ selectedRolloverLabel }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="message" :class="['ha-message', message.type]">{{ message.text }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from 'vue'
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
interface RolloverBillMonth {
  rollover_month?: string | null
  bill_cycle_date?: string | null
  month_range?: string | null
}
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

const showLinkHaUserModal = ref(false)
const linkHaUserPayeeId = ref<number | null>(null)

function getLinkedHaUserName(user: User): string | null {
  if (!user.ha_user_id) return null
  const haUser = haUsers.value.find(u => u.id === user.ha_user_id)
  return haUser?.name ?? null
}

function isHaUserLinkedToOtherPayee(haUserId: string, excludePayeeId: number): boolean {
  return users.value.some(u => u.id !== excludePayeeId && (u.ha_user_id ?? null) === haUserId)
}

async function openLinkHaUserModal(user: User) {
  linkHaUserPayeeId.value = user.id
  showLinkHaUserModal.value = true
  await loadHaUsersAndServices()
}

async function handleLinkHaUser(haUser: HaUser) {
  const payeeId = linkHaUserPayeeId.value
  if (!payeeId) return
  isLoading.value = true
  message.value = null
  try {
    const res = await fetch(`${getApiBase()}/payee-users/${payeeId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ha_user_id: haUser.id })
    })
    if (res.ok) {
      showLinkHaUserModal.value = false
      linkHaUserPayeeId.value = null
      await loadUsers()
      message.value = { type: 'success', text: `Linked to ${haUser.name}` }
    } else {
      const e = await res.json().catch(() => ({}))
      message.value = { type: 'error', text: e.detail || 'Failed to link' }
    }
  } catch {
    message.value = { type: 'error', text: 'Failed to connect' }
  } finally {
    isLoading.value = false
  }
}

async function unlinkHaUserFromModal() {
  const pid = linkHaUserPayeeId.value
  if (pid == null) return
  const user = users.value.find(u => u.id === pid)
  if (!user) return
  await unlinkHaUser(user)
  if (message.value?.type === 'success') {
    showLinkHaUserModal.value = false
    linkHaUserPayeeId.value = null
  }
}

async function unlinkHaUser(user: User) {
  if (!confirm(`Unlink ${user.name} from HA user?`)) return
  isLoading.value = true
  message.value = null
  try {
    const res = await fetch(`${getApiBase()}/payee-users/${user.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ unlink_ha_user: true })
    })
    if (res.ok) {
      await loadUsers()
      message.value = { type: 'success', text: 'Unlinked' }
    } else {
      const e = await res.json().catch(() => ({}))
      message.value = { type: 'error', text: e.detail || 'Failed to unlink' }
    }
  } catch {
    message.value = { type: 'error', text: 'Failed to connect' }
  } finally {
    isLoading.value = false
  }
}

const MONTH_LABELS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

const rolloverBills = ref<RolloverBillMonth[]>([])
const rolloverClearStatus = ref<'loading' | 'ready' | 'error'>('loading')
const rolloverClearMonth = ref<string | null>(null)
const rolloverClearLabel = ref<string | null>(null)
const selectedRolloverMonth = ref('')
const rolloverClearSaving = ref(false)
const rolloverClearError = ref<string | null>(null)
const rolloverConfirmOpen = ref(false)
const rolloverConfirmButton = ref<HTMLButtonElement | null>(null)

function formatMonthLabel(month: string): string {
  const match = /^(\d{4})-(\d{2})$/.exec(month)
  if (!match) return month
  const index = Number(match[2]) - 1
  const name = MONTH_LABELS[index]
  return name ? `${name} ${match[1]}` : month
}

function monthFromCycleDate(cycle: string | null | undefined): string | null {
  if (!cycle) return null
  const us = /^(\d{1,2})\/\d{1,2}\/(\d{4})$/.exec(cycle.trim())
  if (us) {
    const month = Number(us[1])
    if (month >= 1 && month <= 12) return `${us[2]}-${String(month).padStart(2, '0')}`
  }
  const iso = /^(\d{4})-(\d{2})/.exec(cycle.trim())
  if (iso) return `${iso[1]}-${iso[2]}`
  return null
}

const rolloverMonthOptions = computed(() => {
  const byMonth = new Map<string, string>()
  for (const bill of rolloverBills.value) {
    const month = bill.rollover_month || monthFromCycleDate(bill.bill_cycle_date)
    if (!month || byMonth.has(month)) continue
    const label = formatMonthLabel(month)
    const range = bill.month_range ? ` (${bill.month_range})` : ''
    byMonth.set(month, `${label}${range}`)
  }
  return [...byMonth.entries()]
    .sort((a, b) => b[0].localeCompare(a[0]))
    .map(([month, optionLabel]) => ({
      month,
      label: formatMonthLabel(month),
      optionLabel,
    }))
})

interface CalculationSwitch {
  month: string
  mode: 'bill_only' | 'rollover'
  label?: string | null
}

const calculationSwitches = ref<CalculationSwitch[]>([])
const switchStatus = ref<'loading' | 'ready' | 'error'>('loading')
const switchSaving = ref(false)
const switchError = ref<string | null>(null)
const selectedSwitchMode = ref<'bill_only' | 'rollover'>('rollover')

const selectedRolloverLabel = computed(() => {
  const match = rolloverMonthOptions.value.find((opt) => opt.month === selectedRolloverMonth.value)
  return match?.label || (selectedRolloverMonth.value ? formatMonthLabel(selectedRolloverMonth.value) : 'the selected month')
})

watch(rolloverMonthOptions, (opts) => {
  const first = opts[0]
  if (!first) {
    selectedRolloverMonth.value = ''
    return
  }
  if (!opts.some((opt) => opt.month === selectedRolloverMonth.value)) {
    selectedRolloverMonth.value = first.month
  }
}, { immediate: true })

watch(rolloverConfirmOpen, async (open) => {
  if (!open) return
  await nextTick()
  rolloverConfirmButton.value?.focus()
})

async function loadCalculationSwitches() {
  switchStatus.value = 'loading'
  switchError.value = null
  try {
    const [switchRes, ledgerRes] = await Promise.all([
      fetch(`${getApiBase()}/calculation-switches`),
      fetch(`${getApiBase()}/ledger`),
    ])
    if (!switchRes.ok) {
      switchStatus.value = 'error'
      switchError.value = "Couldn't load the calculation switches."
      return
    }
    const data = await switchRes.json()
    calculationSwitches.value = Array.isArray(data?.switches) ? data.switches : []
    if (ledgerRes.ok) {
      const ledger = await ledgerRes.json()
      rolloverBills.value = Array.isArray(ledger?.bills) ? ledger.bills : []
    }
    switchStatus.value = 'ready'
  } catch {
    switchStatus.value = 'error'
    switchError.value = "Couldn't load the calculation switches."
  }
}

async function addCalculationSwitch() {
  const month = selectedRolloverMonth.value
  if (!month || switchSaving.value) return
  const methodLabel = selectedSwitchMode.value === 'rollover' ? 'rollover' : 'bill only'
  const label = selectedRolloverLabel.value
  if (!confirm(`Start ${methodLabel} in ${label}? Earlier bills stay on their current method.`)) return
  switchSaving.value = true
  switchError.value = null
  try {
    const res = await fetch(`${getApiBase()}/calculation-switches`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ month, mode: selectedSwitchMode.value }),
    })
    if (!res.ok) {
      switchError.value = "Couldn't save that switch. Nothing was changed."
      return
    }
    const data = await res.json()
    calculationSwitches.value = Array.isArray(data?.switches) ? data.switches : calculationSwitches.value
  } catch {
    switchError.value = "Couldn't save that switch. Nothing was changed."
  } finally {
    switchSaving.value = false
  }
}

async function removeCalculationSwitch(month: string) {
  if (switchSaving.value) return
  if (!confirm(`Remove the switch for ${formatMonthLabel(month)}?`)) return
  switchSaving.value = true
  switchError.value = null
  try {
    const res = await fetch(`${getApiBase()}/calculation-switches?month=${encodeURIComponent(month)}`, { method: 'DELETE' })
    if (!res.ok) {
      switchError.value = "Couldn't remove that switch. It is still in place."
      return
    }
    const data = await res.json()
    calculationSwitches.value = Array.isArray(data?.switches) ? data.switches : []
  } catch {
    switchError.value = "Couldn't remove that switch. It is still in place."
  } finally {
    switchSaving.value = false
  }
}

async function loadRolloverClearControl() {
  rolloverClearStatus.value = 'loading'
  rolloverClearError.value = null
  try {
    const [clearRes, ledgerRes] = await Promise.all([
      fetch(`${getApiBase()}/rollover-clear`),
      fetch(`${getApiBase()}/ledger`),
    ])
    if (!clearRes.ok) {
      rolloverClearStatus.value = 'error'
      rolloverClearError.value = "Couldn't load the rollover clear setting."
      return
    }
    const clearData = await clearRes.json()
    const month = typeof clearData?.month === 'string' && clearData.month ? clearData.month : null
    rolloverClearMonth.value = month
    rolloverClearLabel.value = month
      ? (clearData.label || formatMonthLabel(month))
      : null
    if (ledgerRes.ok) {
      const ledger = await ledgerRes.json()
      rolloverBills.value = Array.isArray(ledger?.bills) ? ledger.bills : []
    } else {
      rolloverBills.value = []
    }
    rolloverClearStatus.value = 'ready'
  } catch {
    rolloverClearStatus.value = 'error'
    rolloverClearError.value = "Couldn't load the rollover clear setting."
  }
}

function requestRolloverClear() {
  if (!selectedRolloverMonth.value || rolloverClearSaving.value) return
  rolloverClearError.value = null
  rolloverConfirmOpen.value = true
}

async function applyRolloverClear() {
  const month = selectedRolloverMonth.value
  if (!month || rolloverClearSaving.value) return
  rolloverConfirmOpen.value = false
  rolloverClearSaving.value = true
  rolloverClearError.value = null
  try {
    const res = await fetch(`${getApiBase()}/rollover-clear`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ month }),
    })
    if (!res.ok) {
      rolloverClearError.value = "Couldn't clear the rollover balance. Nothing was changed."
      return
    }
    const data = await res.json()
    if (!data?.month) {
      rolloverClearError.value = "Couldn't clear the rollover balance. Nothing was changed."
      return
    }
    rolloverClearMonth.value = data.month
    rolloverClearLabel.value = data.label || formatMonthLabel(data.month)
  } catch {
    rolloverClearError.value = "Couldn't clear the rollover balance. Nothing was changed."
  } finally {
    rolloverClearSaving.value = false
  }
}

async function undoRolloverClear() {
  if (rolloverClearSaving.value) return
  rolloverClearSaving.value = true
  rolloverClearError.value = null
  try {
    const res = await fetch(`${getApiBase()}/rollover-clear`, { method: 'DELETE' })
    if (!res.ok) {
      rolloverClearError.value = "Couldn't undo the rollover clear. It is still in place."
      return
    }
    rolloverClearMonth.value = null
    rolloverClearLabel.value = null
  } catch {
    rolloverClearError.value = "Couldn't undo the rollover clear. It is still in place."
  } finally {
    rolloverClearSaving.value = false
  }
}

onMounted(() => {
  loadUsers()
  loadPaymentsData()
  loadAppSettings()
  loadHaUsersAndServices()
  loadCalculationSwitches()
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
.ha-link-row { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }
.ha-link-label { font-size: 0.85rem; color: #666; }
.ha-link-btn { font-size: 0.8rem; background: #e3f2fd; color: #1976d2; border: 1px solid #90caf9; padding: 0.3rem 0.6rem; border-radius: 4px; cursor: pointer; display: inline-flex; align-items: center; gap: 0.35rem; }
.ha-link-btn:hover { background: #bbdefb; }
.ha-link-action { font-size: 0.7rem; opacity: 0.9; }
.ha-unlink-row { margin-bottom: 1rem; }
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

.ha-rollover-clear {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e0e0e0;
}
.ha-switch-list {
  list-style: none;
  margin: 0.6rem 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.ha-switch-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  padding: 0.45rem 0.6rem;
  background: #f3f9fc;
  border: 1px solid #d7ebf5;
  border-radius: 6px;
  font-size: 0.85rem;
}
.ha-rollover-clear-title {
  margin: 0 0 0.25rem;
  font-size: 1rem;
  font-weight: 600;
  color: #212121;
}
.ha-rollover-clear-desc {
  margin-left: 0;
  margin-bottom: 0.75rem;
}
.ha-rollover-clear-form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-width: 100%;
}
.ha-rollover-clear-label {
  font-size: 1rem;
  font-weight: 600;
  color: #212121;
}
.ha-rollover-clear select {
  min-height: 44px;
  width: 100%;
  max-width: 100%;
  font-size: 1rem;
  padding: 0.4rem 0.6rem;
  border: 1px solid #0088cc;
  border-radius: 6px;
  background: #fff;
  color: #212121;
}
.ha-rollover-clear-btn,
.ha-rollover-undo,
.ha-rollover-dialog-btn {
  min-height: 44px;
  font-size: 1rem;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
}
.ha-rollover-clear-btn,
.ha-rollover-undo {
  width: 100%;
  max-width: 28rem;
}
.ha-rollover-clear-btn {
  background: #0088cc;
  color: #fff;
  border: none;
  font-weight: 600;
  text-align: center;
  white-space: normal;
  line-height: 1.3;
}
.ha-rollover-clear-btn:hover:not(:disabled) {
  background: #006699;
}
.ha-rollover-clear-btn:disabled,
.ha-rollover-undo:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}
.ha-rollover-undo {
  background: #fff;
  color: #01579b;
  border: 2px solid #0088cc;
  font-weight: 600;
}
.ha-rollover-undo:hover:not(:disabled) {
  background: #e3f2fd;
}
.ha-rollover-clear select:focus-visible,
.ha-rollover-clear-btn:focus-visible,
.ha-rollover-undo:focus-visible,
.ha-rollover-dialog-btn:focus-visible {
  outline: 2px solid #01579b;
  outline-offset: 2px;
}
.ha-rollover-clear-note {
  margin: 0 0 0.6rem;
  color: #01579b;
  font-size: 1rem;
  line-height: 1.4;
}
.ha-rollover-clear-empty {
  margin: 0;
  color: #424242;
  font-size: 0.95rem;
}
.ha-rollover-clear-error {
  margin: 0 0 0.6rem;
  padding: 0.5rem 0.65rem;
  background: #ffebee;
  color: #b71c1c;
  border-radius: 6px;
  font-size: 0.95rem;
}
.ha-rollover-dialog-header {
  background: #03a9f4;
  color: #fff;
  border-bottom: none;
}
.ha-rollover-dialog-actions {
  flex-wrap: wrap;
  gap: 0.5rem;
}
.ha-rollover-dialog-actions .ha-rollover-dialog-btn {
  flex: 1 1 10rem;
  width: auto;
  max-width: none;
  white-space: normal;
}
@media (min-width: 720px) {
  .ha-rollover-clear-form {
    display: grid;
    grid-template-columns: minmax(8rem, auto) minmax(0, 1fr);
    align-items: center;
  }
  .ha-rollover-clear-btn {
    grid-column: 1 / -1;
    justify-self: start;
  }
}
</style>
