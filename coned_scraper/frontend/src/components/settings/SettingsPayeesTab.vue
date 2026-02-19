<template>
  <div class="ha-card">
    <div class="ha-card-header">
      <span class="ha-card-icon">👥</span>
      <span>Payees</span>
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
        <div v-for="user in users" :key="user.id" :class="['ha-user-card', { default: user.is_default }]">
          <div class="ha-user-row">
            <span class="ha-user-name">{{ user.name }}</span>
            <span v-if="user.is_default" class="ha-badge">DEFAULT</span>
            <div class="ha-user-actions">
              <button v-if="!user.is_default" type="button" class="ha-btn-sm ha-btn-green" @click="handleSetDefault(user.id)">Set Default</button>
              <button type="button" class="ha-btn-sm ha-btn-red" @click="handleDeleteUser(user.id)">Delete</button>
            </div>
          </div>
          <div v-if="!user.is_default" class="ha-user-detail">
            <div class="ha-responsibility">
              <span>Bill Share:</span>
              <input v-model.number="responsibilities[user.id]" type="number" min="0" max="100" @input="(e: Event) => responsibilities[user.id] = parseInt((e.target as HTMLInputElement).value) || 0" />
              <span>%</span>
            </div>
            <div class="ha-cards">Cards: {{ user.cards?.length ? user.cards.map((c: string) => '*' + c).join(', ') : 'None' }}</div>
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
      <div v-if="message" :class="['ha-message', message.type]">{{ message.text }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getApiBase } from '../../lib/api-base'

interface User { id: number; name: string; is_default: boolean; cards: string[]; responsibility_percent?: number }
const users = ref<User[]>([])
const unverifiedPayments = ref<any[]>([])
const newUserName = ref('')
const responsibilities = ref<Record<number, number>>({})
const isLoading = ref(false)
const message = ref<{ type: 'success' | 'error'; text: string } | null>(null)

const totalResponsibility = computed(() => Object.values(responsibilities.value).reduce((a, b) => a + (b || 0), 0))

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

async function handleAddUser() {
  if (!newUserName.value.trim()) return
  isLoading.value = true
  message.value = null
  try {
    const res = await fetch(`${getApiBase()}/payee-users`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: newUserName.value.trim(), is_default: users.value.length === 0 }) })
    if (res.ok) { newUserName.value = ''; await loadUsers(); message.value = { type: 'success', text: 'User added' } }
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

async function handleAttribute(paymentId: number, userId: string) {
  if (!userId) return
  try {
    const res = await fetch(`${getApiBase()}/payments/attribute`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ payment_id: paymentId, user_id: parseInt(userId), method: 'manual' }) })
    if (res.ok) { await loadUnverified(); message.value = { type: 'success', text: 'Assigned' } }
  } catch { message.value = { type: 'error', text: 'Failed' } }
}

onMounted(() => { loadUsers(); loadUnverified() })
</script>

<style scoped>
.ha-add-row { display: flex; gap: 0.5rem; }
.ha-add-row input { flex: 1; }
.ha-users-list { display: flex; flex-direction: column; gap: 0.75rem; margin: 1rem 0; }
.ha-user-card { padding: 0.75rem; border-radius: 8px; border: 1px solid #e0e0e0; }
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
.ha-unv-row { display: flex; justify-content: space-between; align-items: center; padding: 0.5rem; background: #fff3e0; border-radius: 6px; margin-bottom: 0.5rem; }
.ha-message { margin-top: 1rem; padding: 0.75rem; border-radius: 4px; }
.ha-message.success { background: #e8f5e9; color: #2e7d32; }
.ha-message.error { background: #ffebee; color: #c62828; }
</style>
