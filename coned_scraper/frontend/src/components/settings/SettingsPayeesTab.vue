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

      <!-- Card management modal -->
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
interface CardItem { id: number; user_id: number; card_last_four: string; card_label: string | null }
const users = ref<User[]>([])
const unverifiedPayments = ref<any[]>([])
const newUserName = ref('')
const responsibilities = ref<Record<number, number>>({})
const isLoading = ref(false)
const message = ref<{ type: 'success' | 'error'; text: string } | null>(null)

const modalUser = ref<User | null>(null)
const modalCards = ref<CardItem[]>([])
const newCardDigits = ref('')
const newCardLabel = ref('')
const cardLoading = ref(false)
const editingCardId = ref<number | null>(null)
const editingLabel = ref('')

const totalResponsibility = computed(() => Object.values(responsibilities.value).reduce((a, b) => a + (b || 0), 0))
const isValidCardDigits = computed(() => /^\d{4}$/.test(newCardDigits.value))

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

/* Card modal */
.ha-user-card { cursor: pointer; }
.ha-modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 1rem; }
.ha-modal { background: white; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.2); max-width: 420px; width: 100%; max-height: 90vh; overflow: hidden; display: flex; flex-direction: column; }
.ha-modal-header { display: flex; justify-content: space-between; align-items: center; padding: 1rem 1.25rem; border-bottom: 1px solid #e0e0e0; }
.ha-modal-header h3 { margin: 0; font-size: 1.1rem; }
.ha-modal-close { background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #666; padding: 0 0.25rem; line-height: 1; }
.ha-modal-close:hover { color: #333; }
.ha-modal-content { padding: 1.25rem; overflow-y: auto; }
.ha-modal-desc { font-size: 0.9rem; color: #666; margin: 0 0 1rem 0; }
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
</style>
