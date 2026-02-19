<template>
  <div class="ha-card">
    <div class="ha-card-header">
      <span class="ha-card-icon">🔊</span>
      <span>TTS Alerts</span>
    </div>
    <div class="ha-card-content">
      <div class="info-text" style="margin-bottom: 1.5rem">
        Configure text-to-speech for Con Edison events. When running as a Home Assistant addon, TTS is sent via the HA API. Messages use <strong>(prefix), (message)</strong>.
      </div>
      <form @submit.prevent="handleSave">
        <div class="ha-form-group">
          <label class="ha-check-label">
            <input v-model="enabled" type="checkbox" />
            <span>Enable TTS Alerts</span>
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
          <div class="info-text">Home Assistant entity ID (e.g. media_player.kitchen)</div>
        </div>
        <div class="ha-form-group">
          <label for="tts-service" class="ha-form-label">TTS Service</label>
          <select id="tts-service" v-model="ttsService" class="ha-form-input">
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
            class="ha-form-input ha-input-mono"
            style="margin-top: 0.5rem"
            placeholder="tts.your_service_say"
          />
        </div>
        <div class="ha-form-group">
          <label for="tts-volume" class="ha-form-label">Volume ({{ volumePercent }}%)</label>
          <input
            id="tts-volume"
            v-model.number="volume"
            type="range"
            class="ha-volume-slider"
            min="0"
            max="1"
            step="0.05"
          />
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
          <div class="info-text">Prepended to every message</div>
        </div>
        <div class="ha-form-group">
          <label class="ha-check-label">
            <input v-model="waitForIdle" type="checkbox" />
            <span>Wait for media player idle</span>
          </label>
          <div class="info-text">Only play when media player is idle; otherwise wait up to 5 minutes</div>
        </div>

        <div class="ha-section-divider">
          <h4 class="ha-form-subtitle">Message Templates</h4>
          <p class="info-text">Use <code>{placeholder}</code> for variables (e.g. <code>{amount}</code>, <code>{balance}</code>, <code>{month_range}</code>).</p>
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
        </div>

        <div class="ha-form-actions">
          <button type="submit" class="ha-button ha-button-primary" :disabled="isLoading">{{ isLoading ? 'Saving...' : 'Save TTS Config' }}</button>
          <button
            type="button"
            class="ha-button ha-btn-test"
            :disabled="!enabled || !mediaPlayer.trim() || testLoading"
            @click="handleTest"
          >
            {{ testLoading ? 'Sending...' : 'Test TTS' }}
          </button>
        </div>
      </form>
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
.ha-input-mono { font-family: ui-monospace, monospace; font-size: 0.9rem; }
.ha-required { color: #e65100; }
.ha-check-label { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; }
.ha-check-label input { width: 18px; height: 18px; flex-shrink: 0; }

.ha-volume-slider {
  width: 100%;
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
}
.ha-volume-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  background: #ff9800;
  border-radius: 50%;
  cursor: pointer;
  border: none;
}

.ha-section-divider {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e0e0e0;
}
.ha-form-subtitle {
  font-size: 1rem;
  font-weight: 600;
  margin: 0 0 0.5rem 0;
  color: #333;
}
code {
  font-family: ui-monospace, monospace;
  font-size: 0.85em;
  background: #f0f0f0;
  padding: 0.1em 0.3em;
  border-radius: 3px;
}

.ha-form-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 1rem;
}
.ha-btn-test {
  background: #ff9800 !important;
  color: white !important;
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
  padding: 0.75rem;
  border-radius: 4px;
}
.ha-message.success { background: #e8f5e9; color: #2e7d32; }
.ha-message.error { background: #ffebee; color: #c62828; }
</style>
