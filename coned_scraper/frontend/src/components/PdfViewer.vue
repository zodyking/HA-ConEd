<template>
  <div
    class="ha-pdf-overlay"
    @click.self="$emit('close')"
  >
    <!-- Header -->
    <div class="ha-pdf-header">
      <span class="ha-pdf-title">📄 Latest Bill</span>
      <div class="ha-pdf-controls">
        <button class="ha-pdf-ctrl" title="Zoom out" @click="zoomOut">−</button>
        <span class="ha-pdf-scale">{{ Math.round(scale * 100) }}%</span>
        <button class="ha-pdf-ctrl" title="Zoom in" @click="zoomIn">+</button>
        <button class="ha-pdf-ctrl ha-pdf-fit" title="Fit" @click="fitToWidth">Fit</button>
        <div class="ha-pdf-divider"></div>
        <button class="ha-pdf-ctrl" :disabled="pageNumber <= 1" @click="goToPrevPage">‹</button>
        <span class="ha-pdf-pages">{{ pageNumber }} / {{ numPages }}</span>
        <button class="ha-pdf-ctrl" :disabled="pageNumber >= numPages" @click="goToNextPage">›</button>
      </div>
      <button class="ha-pdf-close" @click="$emit('close')">✕</button>
    </div>

    <!-- PDF Content -->
    <div class="ha-pdf-body">
      <div v-if="loading" class="ha-pdf-loading">
        <div>Loading PDF...</div>
        <img :src="ajaxLoader" alt="Loading" class="ha-pdf-loader-img" />
      </div>
      <div v-else-if="error" class="ha-pdf-error">
        <div class="ha-pdf-error-icon">📄</div>
        <div>{{ error }}</div>
        <button class="ha-pdf-open-btn" @click="openDirect">Open PDF Directly</button>
      </div>
      <VuePdfEmbed
        v-else
        :source="url"
        :page="pageNumber"
        :width="pageWidth"
        @loaded="onLoaded"
        @loading-failed="onLoadError"
      />
    </div>

    <!-- Mobile Footer -->
    <div class="ha-pdf-footer">
      <button
        class="ha-pdf-nav-btn"
        :disabled="pageNumber <= 1"
        :class="{ disabled: pageNumber <= 1 }"
        @click="goToPrevPage"
      >
        ← Previous
      </button>
      <span class="ha-pdf-footer-pages">Page {{ pageNumber }} of {{ numPages }}</span>
      <button
        class="ha-pdf-nav-btn"
        :disabled="pageNumber >= numPages"
        :class="{ disabled: pageNumber >= numPages }"
        @click="goToNextPage"
      >
        Next →
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ajaxLoader } from '../lib/assets'
import VuePdfEmbed from 'vue-pdf-embed'

const props = defineProps<{
  url: string
}>()

defineEmits<{ (e: 'close'): void }>()

const numPages = ref(0)
const pageNumber = ref(1)
const scale = ref(1)
const loading = ref(true)
const error = ref<string | null>(null)
const pageWidth = computed(() => Math.min(800, window.innerWidth - 48) * scale.value)

function onLoaded(pdf: { numPages: number }) {
  numPages.value = pdf.numPages
  loading.value = false
  error.value = null
}

function onLoadError() {
  error.value = 'Failed to load PDF'
  loading.value = false
}

function goToPrevPage() {
  pageNumber.value = Math.max(pageNumber.value - 1, 1)
}
function goToNextPage() {
  pageNumber.value = Math.min(pageNumber.value + 1, numPages.value)
}
function zoomIn() {
  scale.value = Math.min(scale.value + 0.25, 3)
}
function zoomOut() {
  scale.value = Math.max(scale.value - 0.25, 0.5)
}
function fitToWidth() {
  scale.value = 1
}
function openDirect() {
  window.open(props.url, '_blank')
}
</script>

<style scoped>
.ha-pdf-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.95);
  display: flex;
  flex-direction: column;
  z-index: 9999;
}
.ha-pdf-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: #1a1a2e;
  border-bottom: 1px solid #333;
  flex-shrink: 0;
}
.ha-pdf-title { color: white; font-weight: 500; }
.ha-pdf-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.ha-pdf-ctrl {
  background: #333;
  border: none;
  color: white;
  padding: 0.3rem 0.6rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  min-width: 30px;
}
.ha-pdf-ctrl:disabled { opacity: 0.5; cursor: not-allowed; }
.ha-pdf-fit { font-size: 0.7rem; padding: 0.3rem 0.5rem; }
.ha-pdf-scale { color: white; font-size: 0.8rem; min-width: 50px; text-align: center; }
.ha-pdf-pages { color: white; font-size: 0.8rem; min-width: 60px; text-align: center; }
.ha-pdf-divider { width: 1px; height: 20px; background: #444; margin: 0 0.5rem; }
.ha-pdf-close {
  background: none;
  border: none;
  color: white;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
}
.ha-pdf-body {
  flex: 1;
  overflow: auto;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 1rem;
  background: #525659;
}
.ha-pdf-loading {
  color: white;
  padding: 2rem;
  text-align: center;
}
.ha-pdf-loader-img { width: 40px; margin-top: 1rem; display: block; margin-left: auto; margin-right: auto; }
.ha-pdf-error {
  color: #ff6b6b;
  padding: 2rem;
  text-align: center;
}
.ha-pdf-error-icon { font-size: 3rem; margin-bottom: 1rem; }
.ha-pdf-open-btn {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background: #03a9f4;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.ha-pdf-footer {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem;
  background: #1a1a2e;
  border-top: 1px solid #333;
}
.ha-pdf-nav-btn {
  background: #03a9f4;
  border: none;
  color: white;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 500;
}
.ha-pdf-nav-btn.disabled { opacity: 0.5; cursor: not-allowed; }
.ha-pdf-footer-pages { color: white; font-size: 0.9rem; }
</style>
