<template>
  <div class="ha-card tts-card">
    <div class="ha-card-header">
      <span class="ha-card-icon">🔊</span>
      <span>TTS Alerts</span>
    </div>
    <div class="ha-card-content">
      <p class="ha-tts-intro">
        Configure text-to-speech for Con Edison events. Messages use <strong>(prefix), (message)</strong>.
        When running as a Home Assistant addon, TTS is sent directly via the HA API.
      </p>

      <div class="ha-tts-form">
        <div class="ha-form-row">
          <label class="ha-toggle-wrap">
            <input v-model="enabled" type="checkbox" class="ha-toggle" />
            <span class="ha-toggle-slider"></span>
            <span class="ha-toggle-label">Enable TTS Alerts</span>
          </label>
        </div>

        <div class="ha-form-group">
          <label for="tts-media-player" class="ha-form-label">Media Player <span class="ha-required">*</span></label>
          <input
            id="tts-media-player"
            v-model="mediaPlayer"
            type="text"
            class="ha-form-input ha-input-mono"
            placeholder="media_player.living_room"
          />
          <div class="ha-form-hint">Home Assistant entity ID (e.g. media_player.kitchen)</div>
        </div>

        <div class="ha-form-group">
          <label for="tts-service" class="ha-form-label">TTS Entity <span class="ha-required">*</span></label>
          <select id="tts-service" v-model="ttsService" class="ha-form-input ha-form-select">
            <option value="tts.google_translate_say">tts.google_translate_say</option>
            <option value="tts.cloud_say">tts.cloud_say</option>
            <option value="tts.amazon_polly_say">tts.amazon_polly_say</option>
            <option value="tts.piper">tts.piper</option>
            <option value="tts.microsoft_edge_say">tts.microsoft_edge_say</option>
            <option value="_custom">Custom...</option>
          </select>
          <input
            v-if="ttsService === '_custom'"
            v-model="ttsServiceCustom"
            type="text"
            class="ha-form-input ha-input-mono ha-form-input-mt"
            placeholder="tts.your_service_say"
          />
        </div>

        <div class="ha-form-group">
          <label for="tts-volume" class="ha-form-label">Volume</label>
          <div class="ha-volume-row">
            <input
              id="tts-volume"
              v-model.number="volume"
              type="range"
              class="ha-volume-slider"
              min="0"
              max="1"
              step="0.05"
            />
            <span class="ha-volume-value">{{ volumePercent }}%</span>
          </div>
        </div>

        <div class="ha-form-group">
          <label for="tts-language" class="ha-form-label">Language</label>
          <input
            id="tts-language"
            v-model="language"
            type="text"
            class="ha-form-input"
            placeholder="e.g. en, en-US"
          />
        </div>

        <div class="ha-form-group">
          <label for="tts-prefix" class="ha-form-label">TTS Prefix</label>
          <input
            id="tts-prefix"
            v-model="prefix"
            type="text"
            class="ha-form-input"
            placeholder="Message from Con Edison."
          />
          <div class="ha-form-hint">Prepended to every message</div>
        </div>

        <div class="ha-form-row">
          <label class="ha-toggle-wrap">
            <input v-model="waitForIdle" type="checkbox" class="ha-toggle" />
            <span class="ha-toggle-slider"></span>
            <span class="ha-toggle-label">Wait for media player idle</span>
          </label>
          <div class="ha-form-hint">Only play when media player is idle; otherwise wait up to 5 minutes</div>
        </div>

        <button type="button" class="ha-button ha-button-primary ha-btn-save" :disabled="isLoading" @click="handleSave">
          {{ isLoading ? 'Saving...' : 'Save TTS Config' }}
        </button>
      </div>

      <details class="ha-tts-section">
        <summary>TTS Message Templates</summary>
        <p class="ha-message-desc">
          Use <code v-pre>{placeholder}</code> for variables (e.g. <code v-pre>{amount}</code>, <code v-pre>{balance}</code>, <code v-pre>{month_range}</code>).
        </p>
        <div v-for="(msg, key) in messageEntries" :key="key" class="ha-form-group">
          <label :for="`msg-${key}`" class="ha-form-label">{{ formatLabel(key) }}</label>
          <input
            :id="`msg-${key}`"
            v-model="messages[key]"
            type="text"
            class="ha-form-input"
            :placeholder="placeholders[key]"
          />
        </div>
        <button type="button" class="ha-button ha-button-primary" :disabled="isLoading" @click="handleSave">
          {{ isLoading ? 'Saving...' : 'Save Messages' }}
        </button>
      </details>

      <div class="ha-tts-actions">
        <button
          type="button"
          class="ha-button ha-btn-test"
          :disabled="!enabled || !mediaPlayer.trim() || testLoading"
          @click="handleTest"
        >
          {{ testLoading ? 'Sending...' : 'Test TTS' }}
        </button>
      </div>

      <div v-if="message" :class="['ha-message', message.type]">{{ message.text }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getApiBase } from '../../lib/api-base'

const enabled = ref(false)
const mediaPlayer = ref('')
const volume = ref(0.7)
const language = ref('en')
const ttsService = ref('tts.google_translate_say')
const ttsServiceCustom = ref('')
const prefix = ref('Message from Con Edison.')
const waitForIdle = ref(true)
const messages = ref<Record<string, string>>({
  new_bill: 'Your new Con Edison bill for {month_range} is now available.',
  payment_received: 'Good news — your payment of {amount} has been received. Your account balance is now {balance}.',
})
const isLoading = ref(false)
const testLoading = ref(false)
const message = ref<{ type: 'success' | 'error'; text: string } | null>(null)

const messageEntries = computed(() => Object.keys(messages.value))

const volumePercent = computed(() => Math.round((volume.value || 0) * 100))

const effectiveTtsService = computed(() =>
  ttsService.value === '_custom' ? ttsServiceCustom.value.trim() : ttsService.value
)

const placeholders: Record<string, string> = {
  new_bill: 'Your new Con Edison bill for {month_range} is now available.',
  payment_received: 'Good news — your payment of {amount} has been received. Your account balance is now {balance}.',
}

function formatLabel(key: string) {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

async function loadConfig() {
  try {
    const res = await fetch(`${getApiBase()}/tts-config`)
    if (res.ok) {
      const data = await res.json()
      enabled.value = data.enabled ?? false
      mediaPlayer.value = data.media_player ?? ''
      volume.value = typeof data.volume === 'number' ? data.volume : 0.7
      language.value = data.language ?? 'en'
      const svc = data.tts_service ?? 'tts.google_translate_say'
      const known = ['tts.google_translate_say', 'tts.cloud_say', 'tts.amazon_polly_say', 'tts.piper', 'tts.microsoft_edge_say']
      if (known.includes(svc)) {
        ttsService.value = svc
      } else {
        ttsService.value = '_custom'
        ttsServiceCustom.value = svc
      }
      prefix.value = data.prefix ?? 'Message from Con Edison.'
      waitForIdle.value = data.wait_for_idle ?? true
      if (data.messages && typeof data.messages === 'object') {
        messages.value = { ...messages.value, ...data.messages }
      }
    }
  } catch (e) {
    console.error(e)
  }
}

async function handleSave() {
  isLoading.value = true
  message.value = null
  try {
    const res = await fetch(`${getApiBase()}/tts-config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        enabled: enabled.value,
        media_player: mediaPlayer.value.trim(),
        volume: volume.value,
        language: language.value,
        prefix: prefix.value,
        tts_service: effectiveTtsService.value || 'tts.google_translate_say',
        wait_for_idle: waitForIdle.value,
        messages: messages.value,
      }),
    })
    if (res.ok) {
      message.value = { type: 'success', text: 'TTS config saved' }
    } else {
      const err = await res.json().catch(() => ({}))
      message.value = { type: 'error', text: err.detail || 'Failed to save' }
    }
  } catch {
    message.value = { type: 'error', text: 'Failed to connect' }
  } finally {
    isLoading.value = false
  }
}

async function handleTest() {
  if (!enabled.value || !mediaPlayer.value.trim()) return
  testLoading.value = true
  message.value = null
  try {
    const res = await fetch(`${getApiBase()}/tts/test`, { method: 'POST' })
    const data = await res.json().catch(() => ({}))
    if (res.ok) {
      message.value = { type: 'success', text: data.message || 'TTS request sent' }
    } else {
      message.value = { type: 'error', text: data.detail || 'Failed' }
    }
  } catch {
    message.value = { type: 'error', text: 'Failed to connect' }
  } finally {
    testLoading.value = false
  }
}

onMounted(loadConfig)
</script>

<style scoped>
.ha-tts-intro {
  margin-bottom: 1.5rem;
  font-size: 0.95rem;
  color: #555;
  line-height: 1.5;
}
.ha-tts-intro strong { color: #333; }

.ha-tts-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}

.ha-form-row { margin-bottom: 0.5rem; }
.ha-form-row .ha-form-hint { margin-top: 0.25rem; margin-left: 0; }

.ha-form-group { display: flex; flex-direction: column; gap: 0.35rem; }
.ha-form-hint { font-size: 0.8rem; color: #666; margin-top: 0.25rem; }
.ha-required { color: #e65100; }

.ha-toggle-wrap {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  cursor: pointer;
}
.ha-toggle {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}
.ha-toggle-label {
  font-weight: 500;
  color: #333;
}
.ha-toggle-slider {
  position: relative;
  width: 44px;
  height: 24px;
  background: #ccc;
  border-radius: 24px;
  transition: background 0.2s;
}
.ha-toggle-slider::before {
  content: '';
  position: absolute;
  width: 20px;
  height: 20px;
  left: 2px;
  top: 2px;
  background: white;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0,0,0,0.3);
  transition: transform 0.2s;
}
.ha-toggle:checked + .ha-toggle-slider {
  background: #03a9f4;
}
.ha-toggle:checked + .ha-toggle-slider::before {
  transform: translateX(20px);
}

.ha-form-select {
  cursor: pointer;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%23666' viewBox='0 0 16 16'%3E%3Cpath d='M8 11L3 6h10l-5 5z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.75rem center;
  padding-right: 2rem;
}
.ha-form-input-mt { margin-top: 0.5rem; }

.ha-volume-row {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.ha-volume-slider {
  flex: 1;
  height: 8px;
  -webkit-appearance: none;
  appearance: none;
  background: #e0e0e0;
  border-radius: 4px;
}
.ha-volume-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  background: #ff9800;
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}
.ha-volume-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  background: #ff9800;
  border-radius: 50%;
  cursor: pointer;
  border: none;
}
.ha-volume-value {
  min-width: 3.5rem;
  font-weight: 500;
  color: #333;
  font-size: 0.9rem;
}

.ha-btn-save { align-self: flex-start; }

.ha-tts-section {
  margin-top: 1.5rem;
  padding: 1rem 1.25rem;
  background: #f9f9f9;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
}
.ha-tts-section summary {
  cursor: pointer;
  font-weight: 600;
  color: #333;
  margin-bottom: 0.75rem;
}
.ha-tts-section[open] summary { margin-bottom: 1rem; }
.ha-message-desc {
  margin-bottom: 1rem;
  font-size: 0.9rem;
  color: #555;
}
.ha-message-desc code {
  background: #eee;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  font-size: 0.85rem;
}

.ha-tts-actions { margin-top: 1.25rem; }
.ha-btn-test {
  background: #ff9800 !important;
  color: white !important;
  padding: 0.65rem 1.25rem;
  font-weight: 600;
}
.ha-btn-test:hover:not(:disabled) {
  background: #f57c00 !important;
}
.ha-btn-test:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ha-message {
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  border-radius: 6px;
  font-size: 0.9rem;
}
.ha-message.success { background: #e8f5e9; color: #2e7d32; }
.ha-message.error { background: #ffebee; color: #c62828; }

.ha-input-mono { font-family: ui-monospace, monospace; }

.tts-card {
  flex: 1;
  min-height: 400px;
}
</style>
