<template>
  <div class="ha-card">
    <div class="ha-card-header">
      <span class="ha-card-icon">📡</span>
      <span>MQTT Configuration</span>
    </div>
    <div class="ha-card-content">
      <div class="info-text" style="margin-bottom: 1.5rem">
        Configure MQTT to publish sensor data to Home Assistant. With <strong>MQTT Discovery</strong> enabled, sensors like <code>sensor.coned_latest_bill</code> and <code>sensor.coned_account_balance</code> are auto-registered—no manual configuration.yaml needed.
      </div>
      <form @submit.prevent="handleSave">
        <div class="ha-form-group">
          <label for="mqtt-url" class="ha-form-label">MQTT Broker URL</label>
          <input id="mqtt-url" v-model="mqttUrl" type="text" class="ha-form-input ha-input-mono" placeholder="mqtt://homeassistant.local:1883" />
          <div class="info-text">Leave empty to disable MQTT publishing</div>
        </div>
        <div class="ha-form-group">
          <label for="mqtt-username" class="ha-form-label">MQTT Username</label>
          <input id="mqtt-username" v-model="mqttUsername" type="text" class="ha-form-input" placeholder="Optional" />
        </div>
        <div class="ha-form-group">
          <label for="mqtt-password" class="ha-form-label">MQTT Password <span class="hint">(leave empty to keep existing)</span></label>
          <input id="mqtt-password" v-model="mqttPassword" type="password" class="ha-form-input" placeholder="Optional" autocomplete="new-password" />
        </div>
        <div class="ha-form-group">
          <label for="mqtt-base-topic" class="ha-form-label">Base Topic</label>
          <input id="mqtt-base-topic" v-model="mqttBaseTopic" type="text" class="ha-form-input ha-input-mono" placeholder="coned" />
          <div class="info-text">Topics will be: {{ mqttBaseTopic || 'coned' }}/account_balance, etc.</div>
        </div>
        <div class="ha-form-group">
          <label for="mqtt-qos" class="ha-form-label">Quality of Service (QoS)</label>
          <select id="mqtt-qos" v-model.number="mqttQos" class="ha-form-input">
            <option :value="0">0 - At most once</option>
            <option :value="1">1 - At least once</option>
            <option :value="2">2 - Exactly once</option>
          </select>
        </div>
        <div class="ha-form-group">
          <label class="ha-check-label">
            <input v-model="mqttRetain" type="checkbox" />
            <span>Retain Messages</span>
          </label>
          <div class="info-text">Retained messages persist on the broker</div>
        </div>
        <div class="ha-form-group">
          <label class="ha-check-label">
            <input v-model="mqttDiscovery" type="checkbox" />
            <span>MQTT Discovery (auto-register sensors)</span>
          </label>
          <div class="info-text">Publish discovery configs so Home Assistant creates sensors (e.g. sensor.coned_latest_bill) automatically</div>
        </div>
        <button type="submit" class="ha-button ha-button-primary" :disabled="isLoading">{{ isLoading ? 'Saving...' : 'Save MQTT Config' }}</button>
      </form>
      <div v-if="message" :class="['ha-message', message.type]">{{ message.text }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getApiBase } from '../../lib/api-base'

const mqttUrl = ref('')
const mqttUsername = ref('')
const mqttPassword = ref('')
const mqttBaseTopic = ref('coned')
const mqttQos = ref(1)
const mqttRetain = ref(true)
const mqttDiscovery = ref(true)
const isLoading = ref(false)
const message = ref<{ type: 'success' | 'error'; text: string } | null>(null)

async function loadMqttConfig() {
  try {
    const res = await fetch(`${getApiBase()}/mqtt-config`)
    if (res.ok) {
      const data = await res.json()
      mqttUrl.value = data.mqtt_url || ''
      mqttUsername.value = data.mqtt_username || ''
      mqttPassword.value = ''
      mqttBaseTopic.value = data.mqtt_base_topic || 'coned'
      mqttQos.value = data.mqtt_qos ?? 1
      mqttRetain.value = data.mqtt_retain !== undefined ? data.mqtt_retain : true
      mqttDiscovery.value = data.mqtt_discovery !== undefined ? data.mqtt_discovery : true
    }
  } catch (e) {
    console.error(e)
  }
}

async function handleSave() {
  isLoading.value = true
  message.value = null
  try {
    const res = await fetch(`${getApiBase()}/mqtt-config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mqtt_url: mqttUrl.value.trim(),
        mqtt_username: mqttUsername.value.trim(),
        mqtt_password: mqttPassword.value || undefined,
        mqtt_base_topic: mqttBaseTopic.value.trim() || 'coned',
        mqtt_qos: mqttQos.value,
        mqtt_retain: mqttRetain.value,
        mqtt_discovery: mqttDiscovery.value,
      }),
    })
    if (res.ok) {
      message.value = { type: 'success', text: 'MQTT configuration saved successfully!' }
      await loadMqttConfig()
    } else {
      const err = await res.json().catch(() => ({}))
      message.value = { type: 'error', text: err.detail || 'Failed to save MQTT config' }
    }
  } catch {
    message.value = { type: 'error', text: 'Failed to connect to API.' }
  } finally {
    isLoading.value = false
  }
}

onMounted(loadMqttConfig)
</script>

<style scoped>
.ha-input-mono { font-family: monospace; font-size: 0.9rem; }
.hint { font-size: 0.85rem; font-weight: normal; margin-left: 0.5rem; color: #666; }
.ha-check-label { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; }
code { font-family: monospace; font-size: 0.9em; background: #f0f0f0; padding: 0.1em 0.3em; border-radius: 3px; }
.ha-check-label input { width: 18px; height: 18px; }
.ha-message { margin-top: 1rem; padding: 0.75rem; border-radius: 4px; }
.ha-message.success { background: #e8f5e9; color: #2e7d32; }
.ha-message.error { background: #ffebee; color: #c62828; }
</style>
