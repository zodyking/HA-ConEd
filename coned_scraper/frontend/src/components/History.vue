<template>
  <div class="ha-history">
    <!-- Loading -->
    <div v-if="isLoading" class="ha-loading-state">
      <div class="ha-loading-spinner"></div>
      <div class="ha-loading-text">Loading billing history...</div>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="ha-error-state">{{ error }}</div>

    <!-- No Data -->
    <div v-else-if="!historyData.length" class="ha-empty-data">
      <div class="ha-empty-icon">📊</div>
      <h2 class="ha-empty-title">No History Data Yet</h2>
      <p class="ha-empty-desc">
        Upload bill PDFs in Settings to populate billing history charts.
      </p>
    </div>

    <!-- History Content -->
    <div v-else class="ha-history-content">
      <!-- Summary Cards -->
      <div class="ha-history-summary">
        <div class="ha-summary-card">
          <div class="ha-summary-card-icon">⚡</div>
          <div class="ha-summary-card-content">
            <div class="ha-summary-card-label">Avg. kWh/Month</div>
            <div class="ha-summary-card-value">{{ averageKwh }}</div>
          </div>
        </div>
        <div class="ha-summary-card">
          <div class="ha-summary-card-icon">💵</div>
          <div class="ha-summary-card-content">
            <div class="ha-summary-card-label">Avg. kWh Cost</div>
            <div class="ha-summary-card-value">${{ averageKwhCost }}/kWh</div>
          </div>
        </div>
        <div class="ha-summary-card">
          <div class="ha-summary-card-icon">📈</div>
          <div class="ha-summary-card-content">
            <div class="ha-summary-card-label">Avg. Bill</div>
            <div class="ha-summary-card-value">${{ averageBill }}</div>
          </div>
        </div>
        <div class="ha-summary-card">
          <div class="ha-summary-card-icon">📅</div>
          <div class="ha-summary-card-content">
            <div class="ha-summary-card-label">Bills Tracked</div>
            <div class="ha-summary-card-value">{{ historyData.length }}</div>
          </div>
        </div>
      </div>

      <!-- Tabbed Charts Section -->
      <div class="ha-chart-card ha-chart-tabs-card">
        <div class="ha-chart-tabs">
          <button 
            v-if="meterEnabled"
            class="ha-chart-tab" 
            :class="{ active: activeChartTab === 'realtime' }"
            @click="activeChartTab = 'realtime'"
          >
            <span class="ha-tab-icon">⚡</span>
            <span class="ha-tab-label">
              Recent Usage
              <span v-if="realtimeDataRange?.isStale" class="ha-tab-stale">({{ realtimeDataRange.hoursAgo }}h ago)</span>
            </span>
          </button>
          <button 
            class="ha-chart-tab" 
            :class="{ active: activeChartTab === 'billHistory' }"
            @click="activeChartTab = 'billHistory'"
          >
            <span class="ha-tab-icon">💰</span>
            <span class="ha-tab-label">Bill History</span>
          </button>
          <button 
            class="ha-chart-tab" 
            :class="{ active: activeChartTab === 'kwh' }"
            @click="activeChartTab = 'kwh'"
          >
            <span class="ha-tab-icon">📈</span>
            <span class="ha-tab-label">kWh Usage</span>
          </button>
          <button 
            class="ha-chart-tab" 
            :class="{ active: activeChartTab === 'cost' }"
            @click="activeChartTab = 'cost'"
          >
            <span class="ha-tab-icon">📊</span>
            <span class="ha-tab-label">Cost per kWh</span>
          </button>
          <button 
            class="ha-chart-tab" 
            :class="{ active: activeChartTab === 'rates' }"
            @click="activeChartTab = 'rates'"
          >
            <span class="ha-tab-icon">🔌</span>
            <span class="ha-tab-label">Supply & Delivery Charges</span>
          </button>
        </div>
        
        <div class="ha-chart-tab-content">
          <!-- Real Time Usage Chart (Last 24 Hours) -->
          <div v-show="activeChartTab === 'realtime'" class="ha-realtime-wrapper">
            <div class="ha-realtime-header">
              <span class="ha-realtime-title">
                Last 24 Hours of Available Data
                <span v-if="realtimeDataRange" class="ha-realtime-range">
                  ({{ formatRealtimeRange(realtimeDataRange.first) }} — {{ formatRealtimeRange(realtimeDataRange.last) }})
                </span>
              </span>
              <button 
                class="ha-refresh-btn" 
                @click="refreshRealtimeData" 
                :disabled="realtimeLoading"
                title="Fetch latest data from Con Edison"
              >
                <span :class="{ 'ha-spin': realtimeLoading }">🔄</span>
                Refresh
              </button>
            </div>
            <div class="ha-chart-container ha-chart-container-tall">
              <div v-if="realtimeLoading" class="ha-realtime-loading">
                <div class="ha-loading-spinner small"></div>
                <span>Loading real-time data...</span>
              </div>
              <div v-else-if="realtimeError" class="ha-realtime-error">
                {{ realtimeError }}
              </div>
              <div v-else-if="!realtimeData.length" class="ha-realtime-empty">
                <p>No usage data yet.</p>
                <p class="ha-realtime-hint">Enable Meter Tracking in Settings, then click <strong>Refresh</strong> above to fetch data from Con Edison.</p>
              </div>
              <canvas v-show="realtimeData.length && !realtimeLoading" ref="realtimeChart"></canvas>
            </div>
            <div v-if="realtimeData.length && !realtimeLoading" class="ha-realtime-disclaimer">
              <p v-if="realtimeDataRange?.isStale" class="ha-delay-notice">
                <strong>Data is {{ realtimeDataRange.hoursAgo }} hours behind.</strong> Con Edison usage data is typically delayed 1-24 hours.
              </p>
              Please note: As per Con Edison, your real-time usage may not match billing. Billed usage is validated (reconciled) and may have a multiplier applied (peak hour kWh rates), which will be shown on your bill statement.
            </div>
          </div>
          
          <!-- Bill History Chart -->
          <div v-show="activeChartTab === 'billHistory'" class="ha-chart-container ha-chart-container-tall">
            <canvas ref="billChart"></canvas>
          </div>
          
          <!-- kWh Usage Chart -->
          <div v-show="activeChartTab === 'kwh'" class="ha-chart-container ha-chart-container-tall">
            <canvas ref="kwhChart"></canvas>
          </div>
          
          <!-- kWh Cost Chart -->
          <div v-show="activeChartTab === 'cost'" class="ha-chart-container ha-chart-container-tall">
            <canvas ref="kwhCostChart"></canvas>
          </div>
          
          <!-- Supply & Delivery Charges -->
          <div v-show="activeChartTab === 'rates'" class="ha-chart-container ha-chart-container-tall">
            <canvas ref="supplyDeliveryChart"></canvas>
          </div>
        </div>
      </div>

      <!-- Detailed History Table -->
      <div class="ha-chart-card">
        <div class="ha-chart-header">
          <span class="ha-chart-icon">📋</span>
          <span>Detailed Billing History</span>
        </div>
        <div class="ha-table-container">
          <table class="ha-history-table">
            <thead>
              <tr>
                <th>Bill Cycle</th>
                <th>kWh</th>
                <th>$/kWh</th>
                <th>Supply</th>
                <th>Supply Rate</th>
                <th>Delivery</th>
                <th>Delivery Rate</th>
                <th>Cycle Total</th>
                <th>Roll-over Balance</th>
                <th>Bill Total</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in historyData" :key="row.bill_id">
                <td>{{ formatBillCycleDate(row.bill_cycle_date) }}</td>
                <td>{{ formatNumber(row.kwh_used) }}</td>
                <td>{{ row.kwh_cost ? `$${row.kwh_cost.toFixed(4)}` : '—' }}</td>
                <td>{{ row.supply_total ? `$${row.supply_total.toFixed(2)}` : '—' }}</td>
                <td>{{ row.supply_rate ? `$${row.supply_rate.toFixed(4)}` : '—' }}</td>
                <td>{{ row.delivery_total ? `$${row.delivery_total.toFixed(2)}` : '—' }}</td>
                <td>{{ row.delivery_rate ? `$${row.delivery_rate.toFixed(4)}` : '—' }}</td>
                <td>{{ row.total_from_billing_period ? `$${row.total_from_billing_period.toFixed(2)}` : (row.electricity_total ? `$${row.electricity_total.toFixed(2)}` : '—') }}</td>
                <td>{{ row.balance_from_previous_bill ? `$${row.balance_from_previous_bill.toFixed(2)}` : '$0.00' }}</td>
                <td class="ha-total-cell">{{ formatBillTotal(row) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { getApiBase } from '../lib/api-base'
import {
  Chart,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  BarController,
  LineController,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'

Chart.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  BarController,
  LineController,
  Title,
  Tooltip,
  Legend,
  Filler
)

interface HistoryRow {
  bill_id: number
  month_range: string | null
  bill_cycle_date: string | null
  bill_total: string | null
  amount_numeric: number | null
  kwh_used: number | null
  kwh_cost: number | null
  electricity_total: number | null
  total_from_billing_period: number | null
  balance_from_previous_bill: number
  billing_days: number | null
  supply_total: number
  supply_rate: number
  delivery_total: number
  delivery_rate: number
}

interface RealtimeReading {
  start_time: string
  end_time: string
  consumption: number
}

const isLoading = ref(true)
const error = ref<string | null>(null)
const historyData = ref<HistoryRow[]>([])
const activeChartTab = ref<'realtime' | 'billHistory' | 'kwh' | 'cost' | 'rates'>('billHistory')

// Realtime data state
const realtimeData = ref<RealtimeReading[]>([])
const realtimeLoading = ref(false)
const realtimeError = ref<string | null>(null)
const meterEnabled = ref(false)

const realtimeChart = ref<HTMLCanvasElement | null>(null)
const kwhChart = ref<HTMLCanvasElement | null>(null)
const billChart = ref<HTMLCanvasElement | null>(null)
const kwhCostChart = ref<HTMLCanvasElement | null>(null)
const supplyDeliveryChart = ref<HTMLCanvasElement | null>(null)

let chartInstances: Chart[] = []
let realtimeChartInstance: Chart | null = null

const averageKwh = computed(() => {
  const vals = historyData.value.filter(r => r.kwh_used).map(r => r.kwh_used!)
  if (!vals.length) return '—'
  return Math.round(vals.reduce((a, b) => a + b, 0) / vals.length).toLocaleString()
})

const averageKwhCost = computed(() => {
  const vals = historyData.value.filter(r => r.kwh_cost).map(r => r.kwh_cost!)
  if (!vals.length) return '—'
  return (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(4)
})

const averageBill = computed(() => {
  const vals = historyData.value
    .filter(r => r.electricity_total || r.amount_numeric)
    .map(r => r.electricity_total || r.amount_numeric || 0)
  if (!vals.length) return '—'
  return Math.round(vals.reduce((a, b) => a + b, 0) / vals.length).toLocaleString()
})


function formatNumber(val: number | null | undefined): string {
  if (val == null) return '—'
  return val.toLocaleString()
}

function formatBillTotal(row: HistoryRow): string {
  // Bill Total = Cycle Total + Previous Balance
  const cycleTotal = row.total_from_billing_period || row.electricity_total || row.amount_numeric || 0
  const prevBalance = row.balance_from_previous_bill || 0
  const billTotal = cycleTotal + prevBalance
  if (billTotal === 0) return '—'
  return `$${billTotal.toFixed(2)}`
}

function formatRealtimeRange(date: Date): string {
  return date.toLocaleString('en-US', { 
    month: 'short', 
    day: 'numeric', 
    hour: 'numeric', 
    minute: '2-digit',
    hour12: true 
  })
}

function formatBillCycleDate(dateStr: string | null): string {
  if (!dateStr) return '—'
  try {
    // Handle M/D/YYYY or MM/DD/YYYY format
    const parts = dateStr.split('/')
    if (parts.length === 3) {
      const month = parseInt(parts[0], 10)
      const day = parseInt(parts[1], 10)
      const year = parseInt(parts[2], 10)
      const date = new Date(year, month - 1, day)
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    }
    // Fallback for other formats
    const date = new Date(dateStr)
    if (!isNaN(date.getTime())) {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    }
    return dateStr
  } catch {
    return dateStr
  }
}

async function fetchHistory() {
  isLoading.value = true
  error.value = null
  try {
    // Use same endpoint as AccountLedger to ensure consistent data/ordering
    const res = await fetch(`${getApiBase()}/ledger`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const ledger = await res.json()
    const bills = ledger.bills || []
    
    // Also fetch bill details for the extra parsed data (kwh, supply/delivery)
    const detailsRes = await fetch(`${getApiBase()}/bill-history`)
    let detailsMap: Record<number, any> = {}
    if (detailsRes.ok) {
      const detailsData = await detailsRes.json()
      for (const d of (detailsData.history || [])) {
        detailsMap[d.bill_id] = d
      }
    }
    
    // Merge ledger bills with details - bills are already in correct order from ledger
    historyData.value = bills.map((bill: any) => {
      const details = detailsMap[bill.id] || {}
      return {
        bill_id: bill.id,
        month_range: bill.month_range,
        bill_cycle_date: bill.bill_cycle_date,
        bill_total: bill.bill_total,
        amount_numeric: bill.amount_numeric,
        kwh_used: details.kwh_used || null,
        kwh_cost: details.kwh_cost || null,
        electricity_total: details.electricity_total || null,
        total_from_billing_period: details.total_from_billing_period || null,
        balance_from_previous_bill: details.balance_from_previous_bill || 0,
        billing_days: details.billing_days || null,
        supply_total: details.supply_total || 0,
        supply_rate: details.supply_rate || 0,
        delivery_total: details.delivery_total || 0,
        delivery_rate: details.delivery_rate || 0,
      }
    })
  } catch (e: any) {
    error.value = e.message || 'Failed to load history'
  } finally {
    isLoading.value = false
  }
}

async function fetchRealtimeData(forceRefresh: boolean = false) {
  realtimeLoading.value = true
  realtimeError.value = null
  try {
    // First check if meter tracking is enabled (tab shows when enabled, even if no data yet)
    const statusRes = await fetch(`${getApiBase()}/meter-reading`)
    if (statusRes.ok) {
      const statusData = await statusRes.json()
      meterEnabled.value = statusData.enabled === true
    }
    
    if (!meterEnabled.value) {
      realtimeData.value = []
      if (activeChartTab.value === 'realtime') {
        activeChartTab.value = 'billHistory'
      }
      return
    }
    
    // Use refresh=true to force fresh data from opower API
    const refreshParam = forceRefresh ? '&refresh=true' : ''
    const res = await fetch(`${getApiBase()}/meter-reading/realtime?hours=24${refreshParam}`)
    if (!res.ok) {
      if (res.status === 400) {
        realtimeData.value = []
        if (activeChartTab.value === 'realtime') {
          activeChartTab.value = 'billHistory'
        }
        return
      }
      throw new Error(`HTTP ${res.status}`)
    }
    const data = await res.json()
    let readings = data.readings || []
    
    // Filter to show only the last 24 hours from the most recent available reading
    // (opower data is delayed, so we can't filter from "now")
    if (readings.length > 0) {
      const lastReadingTime = new Date(readings[readings.length - 1].end_time)
      const cutoffTime = new Date(lastReadingTime.getTime() - 24 * 60 * 60 * 1000)
      readings = readings.filter((r: RealtimeReading) => new Date(r.start_time) >= cutoffTime)
    }
    
    realtimeData.value = readings
    
    if (!realtimeData.value.length) {
      // Auto-fetch from API when cache is empty and meter is enabled
      if (meterEnabled.value && !forceRefresh) {
        await fetchRealtimeData(true)
        return
      }
      if (activeChartTab.value === 'realtime') {
        activeChartTab.value = 'billHistory'
      }
      return
    }
    
    await nextTick()
    createRealtimeChart()
  } catch (e: any) {
    realtimeError.value = e.message || 'Failed to load real-time data'
    realtimeData.value = []
  } finally {
    realtimeLoading.value = false
  }
}

async function refreshRealtimeData() {
  await fetchRealtimeData(true)
}

function destroyRealtimeChart() {
  if (realtimeChartInstance) {
    realtimeChartInstance.destroy()
    realtimeChartInstance = null
  }
}

const realtimeDataRange = computed(() => {
  if (!realtimeData.value.length) return null
  const first = new Date(realtimeData.value[0].start_time)
  const last = new Date(realtimeData.value[realtimeData.value.length - 1].end_time)
  const hoursAgo = Math.round((Date.now() - last.getTime()) / (1000 * 60 * 60))
  return {
    first,
    last,
    hoursAgo,
    isStale: hoursAgo > 2
  }
})

function createRealtimeChart() {
  destroyRealtimeChart()
  
  if (!realtimeChart.value || !realtimeData.value.length) return
  
  const ctx = realtimeChart.value.getContext('2d')
  if (!ctx) return
  
  // Use all available data (opower data is delayed, don't filter by "now")
  const chartData = realtimeData.value
  
  // Format labels as time (e.g., "2:30 PM") with date if spans multiple days
  const firstDate = new Date(chartData[0].start_time).toDateString()
  const lastDate = new Date(chartData[chartData.length - 1].end_time).toDateString()
  const showDate = firstDate !== lastDate
  
  const labels = chartData.map(r => {
    const date = new Date(r.end_time)
    if (showDate) {
      return date.toLocaleString('en-US', { 
        month: 'short',
        day: 'numeric',
        hour: 'numeric', 
        minute: '2-digit',
        hour12: true 
      })
    }
    return date.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    })
  })
  
  const consumption = chartData.map(r => r.consumption)
  
  realtimeChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Usage (kWh)',
        data: consumption,
        borderColor: 'rgba(0, 136, 204, 1)',
        backgroundColor: 'rgba(0, 136, 204, 0.15)',
        fill: true,
        tension: 0.2,
        pointRadius: 2,
        pointBackgroundColor: 'rgba(0, 136, 204, 1)',
        pointHoverRadius: 5
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        intersect: false,
        mode: 'index'
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: (items) => {
              if (items.length && chartData[items[0].dataIndex]) {
                const r = chartData[items[0].dataIndex]
                const start = new Date(r.start_time)
                const end = new Date(r.end_time)
                const dateStr = start.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                return `${dateStr} ${start.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })} - ${end.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}`
              }
              return ''
            },
            label: (ctx) => `${ctx.parsed.y.toFixed(3)} kWh`
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          title: { display: true, text: 'kWh (15-min interval)' }
        },
        x: {
          title: { display: true, text: 'Time' },
          ticks: {
            maxTicksLimit: 12,
            maxRotation: 45,
            minRotation: 0
          }
        }
      }
    }
  })
}

function destroyCharts() {
  chartInstances.forEach(c => c.destroy())
  chartInstances = []
  destroyRealtimeChart()
}

function createCharts() {
  destroyCharts()
  
  // For charts, use chronological order (oldest first) - reverse the DESC order from ledger
  const chartData = [...historyData.value].reverse()
  const labels = chartData.map(r => r.month_range || `Bill ${r.bill_id}`)
  
  // kWh Usage Chart
  if (kwhChart.value) {
    const ctx = kwhChart.value.getContext('2d')
    if (ctx) {
      chartInstances.push(new Chart(ctx, {
        type: 'bar',
        data: {
          labels,
          datasets: [{
            label: 'kWh Used',
            data: chartData.map(r => r.kwh_used || 0),
            backgroundColor: 'rgba(0, 136, 204, 0.7)',
            borderColor: 'rgba(0, 136, 204, 1)',
            borderWidth: 1,
            borderRadius: 4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (ctx) => `${ctx.parsed.y.toLocaleString()} kWh`
              }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              title: { display: true, text: 'kWh' }
            }
          }
        }
      }))
    }
  }

  // Bill Total Chart - Stacked bar with current period + previous balance
  if (billChart.value) {
    const ctx = billChart.value.getContext('2d')
    if (ctx) {
      chartInstances.push(new Chart(ctx, {
        type: 'bar',
        data: {
          labels,
          datasets: [
            {
              label: 'Cycle Usage',
              data: chartData.map(r => r.total_from_billing_period || r.electricity_total || r.amount_numeric || 0),
              backgroundColor: 'rgba(34, 139, 34, 0.7)',
              borderColor: 'rgba(34, 139, 34, 1)',
              borderWidth: 1,
              borderRadius: 4
            },
            {
              label: 'Roll-over Balance',
              data: chartData.map(r => r.balance_from_previous_bill || 0),
              backgroundColor: 'rgba(255, 99, 132, 0.7)',
              borderColor: 'rgba(255, 99, 132, 1)',
              borderWidth: 1,
              borderRadius: 4
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'top' },
            tooltip: {
              callbacks: {
                title: (items) => items[0]?.label || '',
                label: (ctx) => `${ctx.dataset.label}: $${ctx.parsed.y.toFixed(2)}`,
                afterBody: (items) => {
                  if (!items.length) return ''
                  const dataIndex = items[0].dataIndex
                  const row = chartData[dataIndex]
                  const cycleUsage = row.total_from_billing_period || row.electricity_total || row.amount_numeric || 0
                  const rollover = row.balance_from_previous_bill || 0
                  const totalBill = cycleUsage + rollover
                  return `\nTotal Bill: $${totalBill.toFixed(2)}`
                }
              }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              stacked: true,
              title: { display: true, text: 'USD ($)' }
            },
            x: {
              stacked: true
            }
          }
        }
      }))
    }
  }

  // kWh Cost Chart
  if (kwhCostChart.value) {
    const ctx = kwhCostChart.value.getContext('2d')
    if (ctx) {
      chartInstances.push(new Chart(ctx, {
        type: 'line',
        data: {
          labels,
          datasets: [{
            label: '$/kWh',
            data: chartData.map(r => r.kwh_cost || 0),
            borderColor: 'rgba(220, 20, 60, 1)',
            backgroundColor: 'rgba(220, 20, 60, 0.1)',
            fill: true,
            tension: 0.3,
            pointRadius: 5,
            pointBackgroundColor: 'rgba(220, 20, 60, 1)'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (ctx) => `$${ctx.parsed.y.toFixed(4)}/kWh`
              }
            }
          },
          scales: {
            y: {
              beginAtZero: false,
              title: { display: true, text: '$/kWh' }
            }
          }
        }
      }))
    }
  }

  // Supply & Delivery Charges Chart ($/kWh) - Line Chart
  if (supplyDeliveryChart.value) {
    const ctx = supplyDeliveryChart.value.getContext('2d')
    if (ctx) {
      chartInstances.push(new Chart(ctx, {
        type: 'line',
        data: {
          labels,
          datasets: [
            {
              label: 'Supply Rate',
              data: chartData.map(r => r.supply_rate || 0),
              borderColor: 'rgba(255, 159, 64, 1)',
              backgroundColor: 'rgba(255, 159, 64, 0.1)',
              borderWidth: 2,
              pointBackgroundColor: 'rgba(255, 159, 64, 1)',
              pointBorderColor: '#fff',
              pointRadius: 4,
              pointHoverRadius: 6,
              tension: 0.3,
              fill: true
            },
            {
              label: 'Delivery Rate',
              data: chartData.map(r => r.delivery_rate || 0),
              borderColor: 'rgba(75, 192, 192, 1)',
              backgroundColor: 'rgba(75, 192, 192, 0.1)',
              borderWidth: 2,
              pointBackgroundColor: 'rgba(75, 192, 192, 1)',
              pointBorderColor: '#fff',
              pointRadius: 4,
              pointHoverRadius: 6,
              tension: 0.3,
              fill: true
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: {
            intersect: false,
            mode: 'index'
          },
          plugins: {
            legend: { position: 'top' },
            tooltip: {
              callbacks: {
                label: (ctx) => `${ctx.dataset.label}: $${ctx.parsed.y.toFixed(4)}/kWh`
              }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              title: { display: true, text: '$/kWh' }
            }
          }
        }
      }))
    }
  }
}

watch(historyData, async () => {
  await nextTick()
  if (historyData.value.length > 0) {
    createCharts()
  }
})

watch(activeChartTab, async (newTab) => {
  await nextTick()
  if (newTab === 'realtime' && realtimeData.value.length && !realtimeChartInstance) {
    createRealtimeChart()
  }
})

onMounted(async () => {
  // Fetch both history and realtime data in parallel
  await Promise.all([
    fetchHistory(),
    fetchRealtimeData()
  ])
})

onUnmounted(() => {
  destroyCharts()
})
</script>

<style scoped>
.ha-history {
  padding: 16px;
}

.ha-loading-state,
.ha-error-state,
.ha-empty-data {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
}

.ha-loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--ha-border-color, #e0e0e0);
  border-top-color: var(--ha-primary-color, #0088cc);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.ha-loading-text {
  margin-top: 12px;
  color: var(--ha-secondary-text-color, #666);
  font-size: 14px;
}

.ha-error-state {
  color: var(--ha-error-color, #dc3545);
  font-size: 14px;
}

.ha-empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.ha-empty-title {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 600;
  color: var(--ha-primary-text-color, #333);
}

.ha-empty-desc {
  margin: 0;
  color: var(--ha-secondary-text-color, #666);
  font-size: 14px;
  max-width: 300px;
}

.ha-history-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.ha-history-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}

.ha-summary-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: var(--ha-card-background, #fff);
  border: 1px solid var(--ha-border-color, #e0e0e0);
  border-radius: 8px;
}

.ha-summary-card-icon {
  font-size: 28px;
}

.ha-summary-card-content {
  flex: 1;
  min-width: 0;
}

.ha-summary-card-label {
  font-size: 12px;
  color: var(--ha-secondary-text-color, #666);
  margin-bottom: 4px;
}

.ha-summary-card-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--ha-primary-text-color, #333);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ha-chart-card {
  background: var(--ha-card-background, #fff);
  border: 1px solid var(--ha-border-color, #e0e0e0);
  border-radius: 8px;
  overflow: hidden;
}

.ha-chart-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: var(--ha-card-header-bg, #f8f9fa);
  border-bottom: 1px solid var(--ha-border-color, #e0e0e0);
  font-weight: 600;
  font-size: 14px;
  color: var(--ha-primary-text-color, #333);
}

.ha-chart-icon {
  font-size: 16px;
}

.ha-chart-container {
  padding: 16px;
  height: 280px;
}

.ha-chart-container-tall {
  height: 365px;
}

/* Primary chart (Bill Totals) */
.ha-chart-primary {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.ha-chart-primary .ha-chart-header {
  background: linear-gradient(135deg, #0088cc 0%, #005fa3 100%);
  color: #fff;
  border-bottom: none;
}

/* Tabbed charts section */
.ha-chart-tabs-card {
  overflow: visible;
}

.ha-chart-tabs {
  display: flex;
  background: var(--ha-card-header-bg, #f8f9fa);
  border-bottom: 1px solid var(--ha-border-color, #e0e0e0);
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.ha-chart-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 14px 20px;
  font-size: 13px;
  font-weight: 500;
  color: var(--ha-secondary-text-color, #666);
  background: transparent;
  border: none;
  border-bottom: 3px solid transparent;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s ease;
}

.ha-chart-tab:hover {
  background: rgba(0, 136, 204, 0.05);
  color: var(--ha-primary-text-color, #333);
}

.ha-chart-tab.active {
  color: var(--ha-primary-color, #0088cc);
  border-bottom-color: var(--ha-primary-color, #0088cc);
  background: rgba(0, 136, 204, 0.08);
}

.ha-tab-icon {
  font-size: 14px;
}

.ha-tab-label {
  font-weight: 600;
}

.ha-chart-tab-content {
  min-height: 365px;
}

.ha-chart-tab-content .ha-chart-container {
  height: 280px;
}

.ha-chart-tab-content .ha-chart-container-tall {
  height: 365px;
}

.ha-realtime-wrapper {
  display: flex;
  flex-direction: column;
}

.ha-realtime-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.ha-realtime-title {
  font-size: 13px;
  font-weight: 500;
  color: #495057;
}

.ha-realtime-range {
  font-weight: normal;
  color: #6c757d;
  font-size: 12px;
}

.ha-refresh-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  font-size: 12px;
  background: #0088cc;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.ha-refresh-btn:hover {
  background: #006699;
}

.ha-refresh-btn:disabled {
  background: #adb5bd;
  cursor: not-allowed;
}

.ha-spin {
  display: inline-block;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.ha-realtime-disclaimer {
  margin: 12px 16px 16px;
  padding: 10px 14px;
  background: #fff8e1;
  border: 1px solid #ffcc02;
  border-radius: 6px;
  font-size: 11px;
  color: #8d6e00;
  line-height: 1.5;
}

.ha-realtime-disclaimer .ha-delay-notice {
  margin: 0 0 8px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid #ffcc02;
  color: #b38600;
}

.ha-tab-stale {
  font-size: 10px;
  color: #ff9800;
  font-weight: normal;
  margin-left: 4px;
}

.ha-table-container {
  overflow-x: auto;
}

.ha-history-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.ha-history-table th,
.ha-history-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid var(--ha-border-color, #e0e0e0);
  white-space: nowrap;
}

.ha-history-table th {
  background: var(--ha-card-header-bg, #f8f9fa);
  font-weight: 600;
  color: var(--ha-secondary-text-color, #666);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.ha-history-table tbody tr:hover {
  background: var(--ha-hover-bg, #f5f5f5);
}

.ha-total-cell {
  font-weight: 600;
  color: var(--ha-primary-text-color, #333);
}

/* Realtime chart states */
.ha-realtime-loading,
.ha-realtime-error,
.ha-realtime-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 200px;
  color: var(--ha-secondary-text-color, #666);
  text-align: center;
  padding: 24px;
}

.ha-realtime-loading {
  gap: 12px;
}

.ha-loading-spinner.small {
  width: 24px;
  height: 24px;
  border-width: 2px;
}

.ha-realtime-error {
  color: var(--ha-error-color, #dc3545);
}

.ha-realtime-empty p {
  margin: 4px 0;
}

.ha-realtime-hint {
  font-size: 12px;
  color: var(--ha-tertiary-text-color, #999);
}

@media (max-width: 600px) {
  .ha-history-summary {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .ha-summary-card {
    padding: 12px;
  }
  
  .ha-summary-card-icon {
    font-size: 24px;
  }
  
  .ha-summary-card-value {
    font-size: 16px;
  }
  
  .ha-chart-container {
    height: 220px;
  }

  .ha-chart-container-tall {
    height: 290px;
  }
  
  .ha-chart-tab {
    padding: 12px 14px;
    font-size: 12px;
  }
  
  .ha-tab-icon {
    font-size: 12px;
  }
  
  .ha-chart-tab-content {
    min-height: 290px;
  }

  .ha-chart-tab-content .ha-chart-container {
    height: 220px;
  }

  .ha-chart-tab-content .ha-chart-container-tall {
    height: 290px;
  }

  .ha-realtime-disclaimer {
    font-size: 10px;
    padding: 8px 10px;
  }
  
  .ha-history-table {
    font-size: 12px;
  }
  
  .ha-history-table th,
  .ha-history-table td {
    padding: 8px 6px;
  }
}
</style>
