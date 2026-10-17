<template>
  <div
    v-if="phase !== 'idle'"
    class="ha-swr-status"
    :class="`is-${phase}`"
    role="status"
    aria-live="polite"
    aria-atomic="true"
    :aria-busy="phase === 'updating' ? 'true' : 'false'"
  >
    <span class="ha-swr-mark" aria-hidden="true"></span>
    <span class="ha-swr-text">{{ message }}</span>
  </div>
</template>

<script setup lang="ts">
import type { RefreshPhase } from '../lib/refresh-status'

defineProps<{
  phase: RefreshPhase
  message: string
}>()
</script>

<style scoped>
.ha-swr-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 0.75rem;
  padding: 0.55rem 0.85rem;
  min-height: 2.75rem;
  border-radius: 6px;
  border: 1px solid transparent;
  border-left-width: 4px;
  font-size: 0.9rem;
  font-weight: 600;
  line-height: 1.35;
  position: sticky;
  top: 0;
  z-index: 5;
}

.ha-swr-mark {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}

.ha-swr-text {
  min-width: 0;
}

.ha-swr-status.is-updating {
  background: #e3f2fd;
  color: #0d47a1;
  border-color: #03a9f4;
}

.ha-swr-status.is-updated {
  background: #e8f5e9;
  color: #1b5e20;
  border-color: #66bb6a;
}

.ha-swr-status.is-error {
  background: #fff8e1;
  color: #4e342e;
  border-color: #ffb300;
}
</style>
