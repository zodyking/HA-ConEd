<template>
  <div v-if="!summary" class="ha-payee-loading">Loading breakdown...</div>
  <div v-else-if="!hasResponsibilities" class="ha-payee-no-config">
    Set payee responsibilities in Settings → Payees
  </div>
  <div v-else class="ha-payee-summary">
    <div v-if="summary.calculation_note" class="ha-calc-note">
      <p class="ha-calc-note-title">{{ summary.calculation_note.title }}</p>
      <p class="ha-calc-note-body">{{ summary.calculation_note.body }}</p>
    </div>
    <div
      class="ha-payee-header"
      :class="summary.bill_status"
      @click="expanded = !expanded"
    >
      <span class="ha-payee-header-text">
        Bill: ${{ money(summary.bill_total) }} |
        Paid: <span class="paid">${{ money(summary.total_paid) }}</span>
        <template v-if="(summary.bill_balance || 0) > 0.01">
          | Still due: <span class="due">${{ money(summary.bill_balance) }}</span>
        </template>
      </span>
      <span class="ha-payee-header-right">
        <span class="ha-payee-mode-label">{{ usesRollover ? 'Rollover' : 'Bill only' }}</span>
        <span class="ha-payee-toggle">{{ expanded ? '▼' : '▶' }}</span>
      </span>
    </div>
    <div v-if="expanded" class="ha-payee-rows">
      <p class="ha-payee-legend">
        Each person's share of this bill, plus anything still unpaid from earlier bills.
        Those amounts add up to the ${{ money(summary.bill_total) }} bill.
      </p>
      <div
        v-for="payee in filteredPayees"
        :key="payee.user_id"
        class="ha-payee-row"
      >
        <div class="ha-payee-main">
        <div class="ha-payee-name">
          {{ payee.name }}
          <span class="ha-payee-pct">{{ payee.responsibility_percent }}%</span>
        </div>
        <div class="ha-payee-fraction">
          <span class="ha-payee-paid">Paid ${{ money(payee.amount_paid) }}</span>
          <span class="ha-payee-share">Share ${{ money(effectiveShare(payee)) }}</span>
        </div>
        <div class="ha-payee-status">
          <template v-if="isPaid(payee)">
            <span class="status-paid">Paid in full</span>
          </template>
          <template v-else-if="isOverPaid(payee)">
            <span class="status-paid">
              Credit<br />
              <span class="status-diff">${{ money(Math.abs(remaining(payee))) }} extra</span>
            </span>
          </template>
          <template v-else>
            <span class="status-under">
              Still owes<br />
              <span class="status-diff">${{ money(Math.abs(remaining(payee))) }}</span>
            </span>
          </template>
        </div>
        </div>
        <ul v-if="reasonLines(payee).length" class="ha-payee-reasons">
          <li v-for="(line, index) in reasonLines(payee)" :key="index">{{ line }}</li>
        </ul>
      </div>
      <p v-if="(summary.bill_balance || 0) > 0.01" class="ha-payee-footer">
        Left on the account: ${{ money(summary.bill_balance) }}
        (credits on one person reduce what the household still owes).
      </p>
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
  amount_due?: number
  share_of_bill?: number
  share_of_bill_cumulative?: number
  rollover_from_previous: number
  current_balance: number
  portion_reasons?: string[]
  status: 'paid' | 'partial' | 'unpaid'
}

interface CalculationNote {
  title: string
  body: string
  mode?: string
  label?: string
}

interface BillSummaryData {
  bill_id: number
  bill_total: number
  total_paid: number
  bill_balance: number
  bill_status: 'paid' | 'partial' | 'unpaid'
  uses_rollover?: boolean
  calculation_note?: CalculationNote | null
  payee_summaries: PayeeSummary[]
}

const props = defineProps<{
  billId: number
  billSummaries: Record<number, BillSummaryData>
  showCumulative?: boolean
}>()

const expanded = ref(true)

const summary = computed(() => props.billSummaries[props.billId])

const usesRollover = computed(() => {
  if (typeof summary.value?.uses_rollover === 'boolean') return summary.value.uses_rollover
  return props.showCumulative === true
})

function money(value: number | undefined | null) {
  return (value || 0).toFixed(2)
}

function effectiveShare(payee: PayeeSummary) {
  return usesRollover.value ? (payee.share_of_bill_cumulative ?? payee.amount_due ?? payee.share_of_bill ?? 0) : (payee.share_of_bill ?? 0)
}

function reasonLines(payee: PayeeSummary) {
  return (payee.portion_reasons || []).filter((line) => line.trim().length > 0)
}

const hasResponsibilities = computed(() =>
  summary.value?.payee_summaries?.some((p) => p.responsibility_percent > 0)
)

const filteredPayees = computed(() =>
  (summary.value?.payee_summaries || []).filter((p) => p.responsibility_percent > 0)
)

function remaining(payee: PayeeSummary) {
  return effectiveShare(payee) - (payee.amount_paid || 0)
}

function isPaid(payee: PayeeSummary) {
  return Math.abs(remaining(payee)) < 0.01
}

function isOverPaid(payee: PayeeSummary) {
  return remaining(payee) < -0.01
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
.ha-calc-note {
  margin: 0;
  padding: 0.55rem 0.7rem;
  background: #f3f9fc;
  border-bottom: 1px solid #d7ebf5;
  border-left: 3px solid #03a9f4;
}
.ha-calc-note-title {
  margin: 0 0 0.2rem;
  font-size: 0.75rem;
  font-weight: 700;
  color: #01579b;
}
.ha-calc-note-body {
  margin: 0;
  font-size: 0.7rem;
  line-height: 1.4;
  color: #37474f;
}
.ha-payee-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.6rem;
  cursor: pointer;
  font-size: 0.7rem;
}
.ha-payee-header-right { display: flex; align-items: center; gap: 0.5rem; }
.ha-payee-header.paid { background: #e8f5e9; }
.ha-payee-header.partial { background: #fff8e1; }
.ha-payee-header.unpaid { background: #ffebee; }
.ha-payee-header-text { font-weight: 600; }
.ha-payee-header-text .paid { color: #4caf50; }
.ha-payee-header-text .due { color: #f44336; }
.ha-payee-toggle { font-size: 0.65rem; color: #666; }
.ha-payee-mode-label {
  margin-left: 0.5rem;
  font-size: 0.65rem;
  font-weight: 400;
  color: #888;
}
.ha-payee-rows { padding: 0.4rem; }
.ha-payee-legend,
.ha-payee-footer {
  margin: 0 0.2rem 0.45rem;
  font-size: 0.68rem;
  line-height: 1.4;
  color: #546e7a;
}
.ha-payee-footer { margin: 0.35rem 0.2rem 0.1rem; }
.ha-payee-row {
  display: flex;
  flex-wrap: wrap;
  padding: 0.5rem 0.6rem;
  margin-bottom: 0.3rem;
  background: #fff;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
  font-size: 0.75rem;
}
.ha-payee-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  gap: 0.5rem;
}
.ha-payee-reasons {
  width: 100%;
  margin: 0.35rem 0 0;
  padding-left: 1.1rem;
  color: #5d4037;
  font-size: 0.7rem;
  line-height: 1.4;
}
.ha-payee-name { font-weight: 600; min-width: 80px; }
.ha-payee-pct { font-size: 0.6rem; color: #999; font-weight: 400; margin-left: 0.3rem; }
.ha-payee-fraction { display: flex; flex-direction: column; align-items: center; line-height: 1.2; }
.ha-payee-paid { color: #4caf50; font-weight: 600; }
.ha-payee-share { border-top: 1px solid #999; color: #37474f; font-weight: 500; padding-top: 1px; font-size: 0.7rem; }
.ha-payee-status { font-weight: 600; font-size: 0.75rem; text-align: right; min-width: 100px; }
.status-paid { color: #4caf50; }
.status-under { color: #f44336; }
.status-diff { font-size: 0.7rem; }
</style>
