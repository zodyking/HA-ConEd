<template>
  <div v-if="!summary" class="ha-payee-loading">Loading breakdown...</div>
  <div v-else-if="!hasResponsibilities" class="ha-payee-no-config">
    Set payee responsibilities in Settings → Payees
  </div>
  <div v-else class="ha-payee-summary">
    <div
      class="ha-payee-header"
      :class="summary.bill_status"
      @click="expanded = !expanded"
    >
      <span class="ha-payee-header-text">
        Bill: ${{ summary.bill_total?.toFixed(2) }} |
        Paid: <span class="paid">${{ summary.total_paid?.toFixed(2) }}</span>
        <template v-if="summary.bill_balance > 0.01">
          | Due: <span class="due">${{ summary.bill_balance?.toFixed(2) }}</span>
        </template>
      </span>
      <span class="ha-payee-toggle">{{ expanded ? '▼' : '▶' }}</span>
    </div>
    <div v-if="expanded" class="ha-payee-rows">
      <div
        v-for="payee in filteredPayees"
        :key="payee.user_id"
        class="ha-payee-row"
      >
        <div class="ha-payee-name">
          {{ payee.name }}
          <span class="ha-payee-pct">{{ payee.responsibility_percent }}%</span>
        </div>
        <div class="ha-payee-fraction">
          <span class="ha-payee-paid">${{ (payee.amount_paid || 0).toFixed(2) }}</span>
          <span class="ha-payee-share">${{ (payee.share_of_bill || 0).toFixed(2) }}</span>
        </div>
        <div class="ha-payee-status">
          <template v-if="isPaid(payee)">
            <span class="status-paid">Paid ✓</span>
          </template>
          <template v-else-if="isOverPaid(payee)">
            <span class="status-paid">
              Over Paid<br />
              <span class="status-diff">by ${{ diff(payee).toFixed(2) }}</span>
            </span>
          </template>
          <template v-else>
            <span class="status-under">
              Under Paid<br />
              <span class="status-diff">by ${{ Math.abs(diff(payee)).toFixed(2) }}</span>
            </span>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface PayeeSummary {
  user_id: number
  name: string
  responsibility_percent: number
  amount_owed: number
  amount_paid: number
  share_of_bill?: number
  rollover_from_previous: number
  current_balance: number
  status: 'paid' | 'partial' | 'unpaid'
}

interface BillSummaryData {
  bill_id: number
  bill_total: number
  total_paid: number
  bill_balance: number
  bill_status: 'paid' | 'partial' | 'unpaid'
  payee_summaries: PayeeSummary[]
}

const props = defineProps<{
  billId: number
  billSummaries: Record<number, BillSummaryData>
}>()

const expanded = ref(true)

const summary = computed(() => props.billSummaries[props.billId])

const hasResponsibilities = computed(() =>
  summary.value?.payee_summaries?.some((p) => p.responsibility_percent > 0)
)

const filteredPayees = computed(() =>
  (summary.value?.payee_summaries || []).filter((p) => p.responsibility_percent > 0)
)

function diff(payee: PayeeSummary) {
  return (payee.amount_paid || 0) - (payee.share_of_bill || 0)
}

function isPaid(payee: PayeeSummary) {
  return Math.abs(diff(payee)) < 0.01
}

function isOverPaid(payee: PayeeSummary) {
  return diff(payee) > 0.01
}
</script>

<style scoped>
.ha-payee-loading {
  margin-top: 0.5rem;
  padding: 0.4rem;
  background: #f5f5f5;
  border-radius: 4px;
  font-size: 0.7rem;
  color: #999;
  text-align: center;
}
.ha-payee-no-config {
  margin-top: 0.5rem;
  padding: 0.4rem;
  background: #fff3e0;
  border-radius: 4px;
  font-size: 0.7rem;
  color: #e65100;
  text-align: center;
}
.ha-payee-summary {
  margin-top: 0.5rem;
  background: #fafafa;
  border-radius: 6px;
  border: 1px solid #e8e8e8;
  overflow: hidden;
}
.ha-payee-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.6rem;
  cursor: pointer;
  font-size: 0.7rem;
}
.ha-payee-header.paid { background: #e8f5e9; }
.ha-payee-header.partial { background: #fff8e1; }
.ha-payee-header.unpaid { background: #ffebee; }
.ha-payee-header-text { font-weight: 600; }
.ha-payee-header-text .paid { color: #4caf50; }
.ha-payee-header-text .due { color: #f44336; }
.ha-payee-toggle { font-size: 0.65rem; color: #666; }
.ha-payee-rows { padding: 0.4rem; }
.ha-payee-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.6rem;
  margin-bottom: 0.3rem;
  background: #fff;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
  font-size: 0.75rem;
}
.ha-payee-name { font-weight: 600; min-width: 80px; }
.ha-payee-pct { font-size: 0.6rem; color: #999; font-weight: 400; margin-left: 0.3rem; }
.ha-payee-fraction { display: flex; flex-direction: column; align-items: center; line-height: 1.1; }
.ha-payee-paid { color: #4caf50; font-weight: 600; }
.ha-payee-share { border-top: 1px solid #999; color: #f44336; font-weight: 500; padding-top: 1px; font-size: 0.7rem; }
.ha-payee-status { font-weight: 600; font-size: 0.75rem; text-align: right; min-width: 100px; }
.status-paid { color: #4caf50; }
.status-under { color: #f44336; }
.status-diff { font-size: 0.7rem; }
</style>
