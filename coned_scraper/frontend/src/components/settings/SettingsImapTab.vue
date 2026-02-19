<template>
  <div class="ha-card">
    <div class="ha-card-header">
      <span class="ha-card-icon">📧</span>
      <span>Email Integration (IMAP)</span>
    </div>
    <div class="ha-card-content">
      <div class="info-text" style="margin-bottom: 1rem">Connect to your email to automatically identify who made each payment by matching card numbers in ConEd payment confirmation emails.</div>
      <div class="ha-form-group">
        <label class="ha-check-label">
          <input v-model="config.enabled" type="checkbox" />
          <span>Enable Email Integration</span>
        </label>
      </div>
      <div class="ha-form-group">
        <label class="ha-form-label">IMAP Server</label>
        <input v-model="config.server" type="text" class="ha-form-input" placeholder="imap.gmail.com" />
        <div class="info-text">Gmail: imap.gmail.com | Outlook: outlook.office365.com</div>
      </div>
      <div class="ha-form-row">
        <div class="ha-form-group">
          <label class="ha-form-label">Port</label>
          <input v-model.number="config.port" type="number" class="ha-form-input" />
        </div>
        <div class="ha-form-group">
          <label class="ha-check-label">
            <input v-model="config.use_ssl" type="checkbox" />
            <span>Use SSL/TLS</span>
          </label>
        </div>
      </div>
      <div class="ha-form-group">
        <label class="ha-form-label">Email Address</label>
        <input v-model="config.email" type="email" class="ha-form-input" placeholder="your@email.com" />
      </div>
      <div class="ha-form-group">
        <label class="ha-form-label">Password / App Password</label>
        <input v-model="config.password" type="password" class="ha-form-input" placeholder="••••••••" />
        <div class="info-text">For Gmail, use an App Password (Settings → Security → App passwords)</div>
      </div>
      <div class="ha-form-group">
        <label class="ha-form-label">Gmail Label / Folder</label>
        <input v-model="config.gmail_label" type="text" class="ha-form-input" placeholder="ConEd" />
      </div>
      <div class="ha-form-group">
        <label class="ha-form-label">Subject Filter</label>
        <input v-model="config.subject_filter" type="text" class="ha-form-input" placeholder="Con Edison Payment Processed" />
      </div>
      <div class="ha-form-group">
        <label class="ha-form-label">Auto-assign mode</label>
        <select v-model="config.auto_assign_mode" class="ha-form-input">
          <option value="manual">Manual only</option>
          <option value="every_scrape">Every scrape</option>
          <option value="custom">Custom interval</option>
        </select>
      </div>
      <div v-if="config.auto_assign_mode === 'custom'" class="ha-form-group">
        <label class="ha-form-label">Custom interval (minutes)</label>
        <input v-model.number="config.custom_interval_minutes" type="number" class="ha-form-input" />
      </div>
      <div class="ha-form-actions">
        <button type="button" class="ha-button ha-button-primary" :disabled="isLoading" @click="handleSave">{{ isLoading ? 'Saving...' : 'Save' }}</button>
        <button type="button" class="ha-button" :disabled="isLoading" @click="handleTest">Test Connection</button>
        <button type="button" class="ha-button" :disabled="isLoading" @click="handleSync">Sync Now</button>
        <button type="button" class="ha-button" :disabled="isLoading" @click="handlePreview">Preview</button>
      </div>
      <div v-if="message" :class="['ha-message', message.type]">{{ message.text }}</div>
      <div v-if="lastSync" class="ha-sync-info">Last sync: {{ lastSync }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getApiBase } from '../../lib/api-base'

const config = reactive({
  enabled: false,
  server: '',
  port: 993,
  email: '',
  password: '',
  use_ssl: true,
  gmail_label: 'ConEd',
  subject_filter: 'Con Edison Payment Processed',
  auto_assign_mode: 'manual' as 'manual' | 'every_scrape' | 'custom',
  custom_interval_minutes: 60,
})
const isLoading = ref(false)
const message = ref<{ type: 'success' | 'error'; text: string } | null>(null)
const lastSync = ref<string | null>(null)

async function loadConfig() {
  try {
    const res = await fetch(`${getApiBase()}/imap-config`)
    if (res.ok) {
      const d = await res.json()
      config.enabled = d.enabled || false
      config.server = d.server || ''
      config.port = d.port ?? 993
      config.email = d.email || ''
      config.password = d.password || ''
      config.use_ssl = d.use_ssl !== false
      config.gmail_label = d.gmail_label || 'ConEd'
      config.subject_filter = d.subject_filter || 'Con Edison Payment Processed'
      config.auto_assign_mode = d.auto_assign_mode || 'manual'
      config.custom_interval_minutes = d.custom_interval_minutes ?? 60
      lastSync.value = d.last_sync || null
    }
  } catch (e) { console.error(e) }
}

async function handleSave() {
  isLoading.value = true
  message.value = null
  try {
    const res = await fetch(`${getApiBase()}/imap-config`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(config) })
    if (res.ok) message.value = { type: 'success', text: 'Email configuration saved!' }
    else { const err = await res.json().catch(() => ({})); message.value = { type: 'error', text: err.detail || 'Failed' } }
  } catch { message.value = { type: 'error', text: 'Failed to connect' } }
  finally { isLoading.value = false }
}

async function handleTest() {
  isLoading.value = true
  message.value = null
  try {
    const res = await fetch(`${getApiBase()}/imap-config/test`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(config) })
    const d = await res.json()
    message.value = d.success ? { type: 'success', text: d.message } : { type: 'error', text: d.message }
  } catch { message.value = { type: 'error', text: 'Connection test failed' } }
  finally { isLoading.value = false }
}

async function handleSync() {
  isLoading.value = true
  message.value = null
  try {
    const res = await fetch(`${getApiBase()}/imap-config/sync`, { method: 'POST' })
    const d = await res.json()
    if (d.success) { message.value = { type: 'success', text: d.message }; await loadConfig() }
    else message.value = { type: 'error', text: d.message }
  } catch { message.value = { type: 'error', text: 'Sync failed' } }
  finally { isLoading.value = false }
}

async function handlePreview() {
  isLoading.value = true
  message.value = null
  try {
    const res = await fetch(`${getApiBase()}/imap-config/preview`, { method: 'POST' })
    const d = await res.json()
    message.value = d.success ? { type: 'success', text: `Found ${d.emails_found ?? 0} matching emails` } : { type: 'error', text: d.message || 'Preview failed' }
  } catch { message.value = { type: 'error', text: 'Failed' } }
  finally { isLoading.value = false }
}

onMounted(loadConfig)
</script>

<style scoped>
.ha-check-label { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; }
.ha-check-label input { width: 18px; height: 18px; }
.ha-form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.ha-form-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 1rem; }
.ha-message { margin-top: 1rem; padding: 0.75rem; border-radius: 4px; }
.ha-message.success { background: #e8f5e9; color: #2e7d32; }
.ha-message.error { background: #ffebee; color: #c62828; }
.ha-sync-info { margin-top: 0.5rem; font-size: 0.85rem; color: #666; }
</style>
