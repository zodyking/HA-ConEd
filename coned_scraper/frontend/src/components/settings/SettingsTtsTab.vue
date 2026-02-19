<template>
  <div class="ha-card">
    <div class="ha-card-header">
      <span class="ha-card-icon">🔊</span>
      <span>TTS Alerts</span>
    </div>
    <div class="ha-card-content">
      <p class="ha-tts-intro">
        Configure text-to-speech announcements for Con Edison events. Messages use format:
        <strong>(prefix), (message)</strong>. TTS is sent via MQTT—add the automation below to your Home Assistant.
      </p>

      <div class="ha-accordion">
        <!-- Section 1: Media Player & TTS Setup -->
        <div class="ha-accordion-item" :class="{ open: accordionOpen === 'settings' }">
          <button type="button" class="ha-accordion-header" @click="toggleAccordion('settings')">
            <span class="ha-accordion-icon">{{ accordionOpen === 'settings' ? '▼' : '▶' }}</span>
            <span>Media Player & TTS Setup</span>
          </button>
          <div v-show="accordionOpen === 'settings'" class="ha-accordion-body">
            <div class="ha-form-group">
              <label class="ha-check-label">
                <input v-model="enabled" type="checkbox" />
                <span>Enable TTS Alerts</span>
              </label>
            </div>
            <div class="ha-form-group">
              <label for="tts-media-player" class="ha-form-label">Media Player Entity</label>
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
              <label for="tts-volume" class="ha-form-label">Volume (0–1)</label>
              <input
                id="tts-volume"
                v-model.number="volume"
                type="number"
                class="ha-form-input"
                min="0"
                max="1"
                step="0.1"
                placeholder="0.7"
              />
            </div>
            <div class="ha-form-group">
              <label for="tts-language" class="ha-form-label">TTS Language</label>
              <input
                id="tts-language"
                v-model="language"
                type="text"
                class="ha-form-input"
                placeholder="en"
              />
              <div class="ha-form-hint">e.g. en, es, google_translate_en</div>
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
              <div class="ha-form-hint">Prepended to every message: (prefix), (message)</div>
            </div>
            <div class="ha-form-group">
              <label class="ha-check-label">
                <input v-model="waitForIdle" type="checkbox" />
                <span>Wait for media player idle</span>
              </label>
              <div class="ha-form-hint">
                Only play when media player state is idle; otherwise wait. Requires HA automation.
              </div>
            </div>
            <button type="button" class="ha-button ha-button-primary" :disabled="isLoading" @click="handleSave">
              {{ isLoading ? 'Saving...' : 'Save TTS Config' }}
            </button>
          </div>
        </div>

        <!-- Section 2: TTS Message Templates -->
        <div class="ha-accordion-item" :class="{ open: accordionOpen === 'messages' }">
          <button type="button" class="ha-accordion-header" @click="toggleAccordion('messages')">
            <span class="ha-accordion-icon">{{ accordionOpen === 'messages' ? '▼' : '▶' }}</span>
            <span>TTS Message Templates</span>
          </button>
          <div v-show="accordionOpen === 'messages'" class="ha-accordion-body">
            <p class="ha-message-desc">
              Edit messages. Use <code v-pre>{{ variable }}</code> for placeholders
              (e.g. <code v-pre>{{ amount }}</code>, <code v-pre>{{ balance }}</code>, <code v-pre>{{ month_range }}</code>).
            </p>
            <div
              v-for="(msg, key) in messageEntries"
              :key="key"
              class="ha-form-group"
            >
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
          </div>
        </div>
      </div>

      <div class="ha-tts-actions">
        <button
          type="button"
          class="ha-button ha-button-primary"
          :disabled="!enabled || !mediaPlayer.trim() || testLoading"
          @click="handleTest"
        >
          {{ testLoading ? 'Sending...' : 'Test TTS' }}
        </button>
      </div>

      <div v-if="message" :class="['ha-message', message.type]">{{ message.text }}</div>

      <details class="ha-tts-docs">
        <summary>Home Assistant Automation (wait for idle)</summary>
        <pre class="ha-automation-yaml">{{ automationYaml }}</pre>
        <p class="ha-form-hint">Add this automation to your <code>configuration.yaml</code> or create via UI. Replace <code>media_player.your_speaker</code> with your entity.</p>
      </details>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getApiBase } from '../../lib/api-base'

const accordionOpen = ref<'settings' | 'messages' | null>('settings')
const enabled = ref(false)
const mediaPlayer = ref('')
const volume = ref(0.7)
const language = ref('en')
const prefix = ref('Message from Con Edison.')
const waitForIdle = ref(true)
const messages = ref<Record<string, string>>({
  new_bill: 'New bill is available for {month_range}.',
  payment_received: 'Payment of {amount} was received.',
  balance_alert: 'Account balance is {balance}.',
})
const isLoading = ref(false)
const testLoading = ref(false)
const message = ref<{ type: 'success' | 'error'; text: string } | null>(null)

const messageEntries = computed(() => Object.keys(messages.value))

const placeholders: Record<string, string> = {
  new_bill: 'New bill is available for {month_range}.',
  payment_received: 'Payment of {amount} was received.',
  balance_alert: 'Account balance is {balance}.',
}

const automationYaml = `# ConEd TTS - waits for media player idle before playing
# Change tts.google_translate_say to your TTS service (tts.cloud_say, tts.amazon_polly_say, etc)
trigger:
  - platform: mqtt
    topic: coned/tts/request
action:
  - variables:
      payload: "{{ trigger.payload_json }}"
      mp: "{{ payload.media_player }}"
      msg: "{{ payload.message }}"
      vol: "{{ payload.volume | default(0.7) }}"
      wait_idle: "{{ payload.wait_for_idle | default(true) }}"
  - if:
      - condition: template
        value_template: "{{ wait_idle == true or wait_idle == 'true' }}"
    then:
      - wait_for_trigger:
          - platform: state
            entity_id: "{{ mp }}"
            to: idle
    else: []
  - service: media_player.volume_set
    target:
      entity_id: "{{ mp }}"
    data:
      volume_level: "{{ vol }}"
  - service: tts.google_translate_say
    data:
      entity_id: "{{ mp }}"
      message: "{{ msg }}"`

function toggleAccordion(section: 'settings' | 'messages') {
  accordionOpen.value = accordionOpen.value === section ? null : section
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
.ha-tts-intro { margin-bottom: 1.25rem; font-size: 0.95rem; color: #555; line-height: 1.5; }
.ha-tts-intro strong { color: #333; }
.ha-accordion { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1.5rem; }
.ha-accordion-item { border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; }
.ha-accordion-item.open .ha-accordion-header { border-bottom: 1px solid #e0e0e0; }
.ha-accordion-header {
  width: 100%; padding: 1rem 1.25rem; background: #f9f9f9; border: none;
  display: flex; align-items: center; gap: 0.75rem; cursor: pointer; text-align: left;
  font-size: 1rem; font-weight: 600; color: #333;
}
.ha-accordion-header:hover { background: #f0f0f0; }
.ha-accordion-icon { font-size: 0.7rem; color: #666; }
.ha-accordion-body { padding: 1.25rem; }
.ha-form-hint { font-size: 0.8rem; color: #666; margin-top: 0.35rem; }
.ha-message-desc { margin-bottom: 1rem; font-size: 0.9rem; color: #555; }
.ha-message-desc code { background: #f0f0f0; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.85rem; }
.ha-tts-actions { margin-top: 1rem; }
.ha-tts-docs { margin-top: 1.5rem; padding: 1rem; background: #f5f5f5; border-radius: 8px; border: 1px solid #e0e0e0; }
.ha-tts-docs summary { cursor: pointer; font-weight: 600; }
.ha-automation-yaml {
  margin: 0.75rem 0; padding: 1rem; background: #1e1e1e; color: #d4d4d4; border-radius: 6px;
  font-size: 0.75rem; line-height: 1.5; overflow-x: auto; white-space: pre-wrap;
}
.ha-message { margin-top: 1rem; padding: 0.75rem; border-radius: 4px; }
.ha-message.success { background: #e8f5e9; color: #2e7d32; }
.ha-message.error { background: #ffebee; color: #c62828; }
.ha-input-mono { font-family: ui-monospace, monospace; }
</style>
