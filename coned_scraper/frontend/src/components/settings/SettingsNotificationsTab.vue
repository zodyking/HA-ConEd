<template>
  <div class="notify-settings">
    <!-- Loading State -->
    <div v-if="loading" class="notify-loading">
      <div class="notify-spinner"></div>
      <p>Loading notification settings...</p>
    </div>

    <template v-else>
      <!-- Overview / Addon Check -->
      <div v-if="!isAddon" class="notify-addon-notice">
        <span class="notify-notice-icon">⚠️</span>
        <div>
          <strong>Home Assistant Addon Required</strong>
          <p>Push notifications require this app to run as a Home Assistant addon with the Companion App configured on your mobile devices.</p>
        </div>
      </div>

      <template v-else>
        <!-- Test recipient selector -->
        <div v-if="payeesWithNotify.length" class="notify-test-select-row">
          <label class="notify-label">Send test notifications to:</label>
          <select v-model="testPayeeId" class="notify-select">
            <option value="">All payees with notifications</option>
            <option v-for="p in payeesWithNotify" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </div>

        <!-- New Bill Posted -->
        <div class="notify-section">
          <div class="notify-section-header" @click="toggleSection('new_bill')">
            <div class="notify-section-title">
              <span class="notify-section-icon">📄</span>
              <span>New Bill Posted</span>
            </div>
            <span class="notify-section-sub">When a new bill appears on your account</span>
            <span class="notify-section-chevron" :class="{ expanded: expandedSections.new_bill }">▼</span>
          </div>
          
          <div v-if="expandedSections.new_bill" class="notify-section-content">
            <div class="notify-toggle-row">
              <label class="notify-toggle">
                <input v-model="configs.new_bill.enabled" type="checkbox" />
                <span class="notify-toggle-slider"></span>
              </label>
              <span class="notify-toggle-label">Enable Notification</span>
            </div>

            <template v-if="configs.new_bill.enabled">
              <div class="notify-form-group">
                <label class="notify-label">Title</label>
                <input v-model="configs.new_bill.title" type="text" class="notify-input" />
              </div>

              <div class="notify-form-group">
                <label class="notify-label">Message Template</label>
                <div class="notify-var-chips">
                  <span class="notify-var-chip" @click="insertVar('new_bill', '{amount}')">{amount}</span>
                  <span class="notify-var-chip" @click="insertVar('new_bill', '{due_date}')">{due_date}</span>
                  <span class="notify-var-chip" @click="insertVar('new_bill', '{month_range}')">{month_range}</span>
                </div>
                <textarea
                  ref="newBillInput"
                  v-model="configs.new_bill.template"
                  class="notify-textarea"
                  rows="2"
                ></textarea>
              </div>

              <button class="notify-btn notify-btn-test" :disabled="testing === 'new_bill'" @click="testNotification('new_bill')">
                {{ testing === 'new_bill' ? 'Sending...' : '📱 Test Notification' }}
              </button>
            </template>
          </div>
        </div>

        <!-- Payment Received -->
        <div class="notify-section">
          <div class="notify-section-header" @click="toggleSection('payment_received')">
            <div class="notify-section-title">
              <span class="notify-section-icon">💳</span>
              <span>Payment Received</span>
            </div>
            <span class="notify-section-sub">When a payment is detected on your account</span>
            <span class="notify-section-chevron" :class="{ expanded: expandedSections.payment_received }">▼</span>
          </div>
          
          <div v-if="expandedSections.payment_received" class="notify-section-content">
            <div class="notify-toggle-row">
              <label class="notify-toggle">
                <input v-model="configs.payment_received.enabled" type="checkbox" />
                <span class="notify-toggle-slider"></span>
              </label>
              <span class="notify-toggle-label">Enable Notification</span>
            </div>

            <template v-if="configs.payment_received.enabled">
              <div class="notify-form-group">
                <label class="notify-label">Title</label>
                <input v-model="configs.payment_received.title" type="text" class="notify-input" />
              </div>

              <div class="notify-form-group">
                <label class="notify-label">Message Template</label>
                <div class="notify-var-chips">
                  <span class="notify-var-chip" @click="insertVar('payment_received', '{amount}')">{amount}</span>
                  <span class="notify-var-chip" @click="insertVar('payment_received', '{balance}')">{balance}</span>
                  <span class="notify-var-chip" @click="insertVar('payment_received', '{payee_name}')">{payee_name}</span>
                </div>
                <textarea
                  ref="paymentReceivedInput"
                  v-model="configs.payment_received.template"
                  class="notify-textarea"
                  rows="2"
                ></textarea>
              </div>

              <button class="notify-btn notify-btn-test" :disabled="testing === 'payment_received'" @click="testNotification('payment_received')">
                {{ testing === 'payment_received' ? 'Sending...' : '📱 Test Notification' }}
              </button>
            </template>
          </div>
        </div>

        <!-- Due Date Reminder -->
        <div class="notify-section">
          <div class="notify-section-header" @click="toggleSection('due_reminder')">
            <div class="notify-section-title">
              <span class="notify-section-icon">⏰</span>
              <span>Due Date Reminder</span>
            </div>
            <span class="notify-section-sub">Daily reminder until due; send time configurable</span>
            <span class="notify-section-chevron" :class="{ expanded: expandedSections.due_reminder }">▼</span>
          </div>
          
          <div v-if="expandedSections.due_reminder" class="notify-section-content">
            <div class="notify-toggle-row">
              <label class="notify-toggle">
                <input v-model="configs.due_reminder.enabled" type="checkbox" />
                <span class="notify-toggle-slider"></span>
              </label>
              <span class="notify-toggle-label">Enable Notification</span>
            </div>

            <template v-if="configs.due_reminder.enabled">
              <div class="notify-form-group">
                <label class="notify-label">Days Before Due (start)</label>
                <input v-model.number="configs.due_reminder.days_before_due" type="number" min="1" max="30" class="notify-input notify-input-small" />
                <p class="notify-hint">Sends daily from this many days before due through the due date</p>
              </div>

              <div class="notify-form-group">
                <label class="notify-label">Send at time (daily)</label>
                <input v-model="configs.due_reminder.reminder_send_time" type="time" class="notify-input notify-input-small" />
                <p class="notify-hint">Time each day to send the reminder (e.g. 09:00)</p>
              </div>

              <div class="notify-form-group">
                <label class="notify-label">Title</label>
                <input v-model="configs.due_reminder.title" type="text" class="notify-input" />
              </div>

              <div class="notify-form-group">
                <label class="notify-label">Message Template</label>
                <div class="notify-var-chips">
                  <span class="notify-var-chip" @click="insertVar('due_reminder', '{amount}')">{amount}</span>
                  <span class="notify-var-chip" @click="insertVar('due_reminder', '{due_date}')">{due_date}</span>
                  <span class="notify-var-chip" @click="insertVar('due_reminder', '{days_until}')">{days_until}</span>
                  <span class="notify-var-chip" @click="insertVar('due_reminder', '{days_until_text}')">{days_until_text}</span>
                </div>
                <textarea
                  ref="dueReminderInput"
                  v-model="configs.due_reminder.template"
                  class="notify-textarea"
                  rows="2"
                ></textarea>
              </div>

              <button class="notify-btn notify-btn-test" :disabled="testing === 'due_reminder'" @click="testNotification('due_reminder')">
                {{ testing === 'due_reminder' ? 'Sending...' : '📱 Test Notification' }}
              </button>
            </template>
          </div>
        </div>

        <!-- Balance Change -->
        <div class="notify-section">
          <div class="notify-section-header" @click="toggleSection('balance_change')">
            <div class="notify-section-title">
              <span class="notify-section-icon">💰</span>
              <span>Balance Change</span>
            </div>
            <span class="notify-section-sub">When your account balance changes</span>
            <span class="notify-section-chevron" :class="{ expanded: expandedSections.balance_change }">▼</span>
          </div>
          
          <div v-if="expandedSections.balance_change" class="notify-section-content">
            <div class="notify-toggle-row">
              <label class="notify-toggle">
                <input v-model="configs.balance_change.enabled" type="checkbox" />
                <span class="notify-toggle-slider"></span>
              </label>
              <span class="notify-toggle-label">Enable Notification</span>
            </div>

            <template v-if="configs.balance_change.enabled">
              <div class="notify-form-group">
                <label class="notify-label">Title</label>
                <input v-model="configs.balance_change.title" type="text" class="notify-input" />
              </div>

              <div class="notify-form-group">
                <label class="notify-label">Message Template</label>
                <div class="notify-var-chips">
                  <span class="notify-var-chip" @click="insertVar('balance_change', '{old_balance}')">{old_balance}</span>
                  <span class="notify-var-chip" @click="insertVar('balance_change', '{new_balance}')">{new_balance}</span>
                </div>
                <textarea
                  ref="balanceChangeInput"
                  v-model="configs.balance_change.template"
                  class="notify-textarea"
                  rows="2"
                ></textarea>
              </div>

              <button class="notify-btn notify-btn-test" :disabled="testing === 'balance_change'" @click="testNotification('balance_change')">
                {{ testing === 'balance_change' ? 'Sending...' : '📱 Test Notification' }}
              </button>
            </template>
          </div>
        </div>

        <!-- Late Fee -->
        <div class="notify-section">
          <div class="notify-section-header" @click="toggleSection('late_fee')">
            <div class="notify-section-title">
              <span class="notify-section-icon">⚠️</span>
              <span>Late Fee Added</span>
            </div>
            <span class="notify-section-sub">When a late fee is detected on your account balance</span>
            <span class="notify-section-chevron" :class="{ expanded: expandedSections.late_fee }">▼</span>
          </div>
          
          <div v-if="expandedSections.late_fee" class="notify-section-content">
            <div class="notify-toggle-row">
              <label class="notify-toggle">
                <input v-model="configs.late_fee.enabled" type="checkbox" />
                <span class="notify-toggle-slider"></span>
              </label>
              <span class="notify-toggle-label">Enable Notification</span>
            </div>

            <template v-if="configs.late_fee.enabled">
              <div class="notify-form-group">
                <label class="notify-label">Title</label>
                <input v-model="configs.late_fee.title" type="text" class="notify-input" />
              </div>

              <div class="notify-form-group">
                <label class="notify-label">Message Template</label>
                <div class="notify-var-chips">
                  <span class="notify-var-chip" @click="insertVar('late_fee', '{late_fee_amount}')">{late_fee_amount}</span>
                </div>
                <textarea
                  ref="lateFeeInput"
                  v-model="configs.late_fee.template"
                  class="notify-textarea"
                  rows="2"
                ></textarea>
              </div>

              <button class="notify-btn notify-btn-test" :disabled="testing === 'late_fee'" @click="testNotification('late_fee')">
                {{ testing === 'late_fee' ? 'Sending...' : '📱 Test Notification' }}
              </button>
            </template>
          </div>
        </div>

        <!-- Payment Claimed -->
        <div class="notify-section">
          <div class="notify-section-header" @click="toggleSection('payment_claimed')">
            <div class="notify-section-title">
              <span class="notify-section-icon">✅</span>
              <span>Payment Claimed</span>
            </div>
            <span class="notify-section-sub">When a payee claims a payment via notification</span>
            <span class="notify-section-chevron" :class="{ expanded: expandedSections.payment_claimed }">▼</span>
          </div>
          <div v-if="expandedSections.payment_claimed" class="notify-section-content">
            <div class="notify-toggle-row">
              <label class="notify-toggle">
                <input v-model="configs.payment_claimed.enabled" type="checkbox" />
                <span class="notify-toggle-slider"></span>
              </label>
              <span class="notify-toggle-label">Enable Notification</span>
            </div>
            <template v-if="configs.payment_claimed.enabled">
              <div class="notify-form-group">
                <label class="notify-label">Title</label>
                <input v-model="configs.payment_claimed.title" type="text" class="notify-input" />
              </div>
              <div class="notify-form-group">
                <label class="notify-label">Message Template</label>
                <div class="notify-var-chips">
                  <span class="notify-var-chip" @click="insertVar('payment_claimed', '{payee_name}')">{payee_name}</span>
                  <span class="notify-var-chip" @click="insertVar('payment_claimed', '{amount}')">{amount}</span>
                  <span class="notify-var-chip" @click="insertVar('payment_claimed', '{payment_date}')">{payment_date}</span>
                </div>
                <textarea ref="paymentClaimedInput" v-model="configs.payment_claimed.template" class="notify-textarea" rows="2"></textarea>
              </div>
              <button class="notify-btn notify-btn-test" :disabled="testing === 'payment_claimed'" @click="testNotification('payment_claimed')">
                {{ testing === 'payment_claimed' ? 'Sending...' : '📱 Test Notification' }}
              </button>
            </template>
          </div>
        </div>

        <!-- Payment Unclaimed -->
        <div class="notify-section">
          <div class="notify-section-header" @click="toggleSection('payment_unclaimed')">
            <div class="notify-section-title">
              <span class="notify-section-icon">↩️</span>
              <span>Payment Unclaimed</span>
            </div>
            <span class="notify-section-sub">When a payee unclaims a payment via Account Ledger</span>
            <span class="notify-section-chevron" :class="{ expanded: expandedSections.payment_unclaimed }">▼</span>
          </div>
          <div v-if="expandedSections.payment_unclaimed" class="notify-section-content">
            <div class="notify-toggle-row">
              <label class="notify-toggle">
                <input v-model="configs.payment_unclaimed.enabled" type="checkbox" />
                <span class="notify-toggle-slider"></span>
              </label>
              <span class="notify-toggle-label">Enable Notification</span>
            </div>
            <template v-if="configs.payment_unclaimed.enabled">
              <div class="notify-form-group">
                <label class="notify-label">Title</label>
                <input v-model="configs.payment_unclaimed.title" type="text" class="notify-input" />
              </div>
              <div class="notify-form-group">
                <label class="notify-label">Message Template</label>
                <div class="notify-var-chips">
                  <span class="notify-var-chip" @click="insertVar('payment_unclaimed', '{payee_name}')">{payee_name}</span>
                  <span class="notify-var-chip" @click="insertVar('payment_unclaimed', '{amount}')">{amount}</span>
                  <span class="notify-var-chip" @click="insertVar('payment_unclaimed', '{payment_date}')">{payment_date}</span>
                </div>
                <textarea ref="paymentUnclaimedInput" v-model="configs.payment_unclaimed.template" class="notify-textarea" rows="2"></textarea>
              </div>
              <button class="notify-btn notify-btn-test" :disabled="testing === 'payment_unclaimed'" @click="testNotification('payment_unclaimed')">
                {{ testing === 'payment_unclaimed' ? 'Sending...' : '📱 Test Notification' }}
              </button>
            </template>
          </div>
        </div>

        <!-- Payment claim prompt (per-payee Yes/No push) -->
        <div class="notify-section">
          <div class="notify-section-header" @click="toggleSection('payment_claim_prompt')">
            <div class="notify-section-title">
              <span class="notify-section-icon">❓</span>
              <span>Payment claim prompt</span>
            </div>
            <span class="notify-section-sub">“Did you make this payment?” — sent to each payee (actions unchanged)</span>
            <span class="notify-section-chevron" :class="{ expanded: expandedSections.payment_claim_prompt }">▼</span>
          </div>
          <div v-if="expandedSections.payment_claim_prompt" class="notify-section-content">
            <div class="notify-toggle-row">
              <label class="notify-toggle">
                <input v-model="configs.payment_claim_prompt.enabled" type="checkbox" />
                <span class="notify-toggle-slider"></span>
              </label>
              <span class="notify-toggle-label">Enable</span>
            </div>
            <template v-if="configs.payment_claim_prompt.enabled">
              <div class="notify-form-group">
                <label class="notify-label">Title</label>
                <input v-model="configs.payment_claim_prompt.title" type="text" class="notify-input" />
              </div>
              <div class="notify-form-group">
                <label class="notify-label">Message template</label>
                <div class="notify-var-chips">
                  <span class="notify-var-chip" @click="insertVar('payment_claim_prompt', '{amount}')">{amount}</span>
                  <span class="notify-var-chip" @click="insertVar('payment_claim_prompt', '{payment_date}')">{payment_date}</span>
                </div>
                <textarea ref="paymentClaimPromptInput" v-model="configs.payment_claim_prompt.template" class="notify-textarea" rows="3"></textarea>
              </div>
              <button class="notify-btn notify-btn-test" :disabled="testing === 'payment_claim_prompt'" @click="testNotification('payment_claim_prompt')">
                {{ testing === 'payment_claim_prompt' ? 'Sending...' : '📱 Test Notification' }}
              </button>
            </template>
          </div>
        </div>

        <!-- Petition: question to assignee -->
        <div class="notify-section">
          <div class="notify-section-header" @click="toggleSection('petition_assignee_question')">
            <div class="notify-section-title">
              <span class="notify-section-icon">📣</span>
              <span>Petition — assignee question</span>
            </div>
            <span class="notify-section-sub">Sent to the payee currently assigned when someone petitions</span>
            <span class="notify-section-chevron" :class="{ expanded: expandedSections.petition_assignee_question }">▼</span>
          </div>
          <div v-if="expandedSections.petition_assignee_question" class="notify-section-content">
            <div class="notify-toggle-row">
              <label class="notify-toggle">
                <input v-model="configs.petition_assignee_question.enabled" type="checkbox" />
                <span class="notify-toggle-slider"></span>
              </label>
              <span class="notify-toggle-label">Enable</span>
            </div>
            <template v-if="configs.petition_assignee_question.enabled">
              <div class="notify-form-group">
                <label class="notify-label">Title</label>
                <input v-model="configs.petition_assignee_question.title" type="text" class="notify-input" />
              </div>
              <div class="notify-form-group">
                <label class="notify-label">Message template</label>
                <div class="notify-var-chips">
                  <span class="notify-var-chip" @click="insertVar('petition_assignee_question', '{petitioner_name}')">{petitioner_name}</span>
                  <span class="notify-var-chip" @click="insertVar('petition_assignee_question', '{amount}')">{amount}</span>
                  <span class="notify-var-chip" @click="insertVar('petition_assignee_question', '{payment_date}')">{payment_date}</span>
                </div>
                <textarea ref="petitionAssigneeInput" v-model="configs.petition_assignee_question.template" class="notify-textarea" rows="3"></textarea>
              </div>
              <button class="notify-btn notify-btn-test" :disabled="testing === 'petition_assignee_question'" @click="testNotification('petition_assignee_question')">
                {{ testing === 'petition_assignee_question' ? 'Sending...' : '📱 Test Notification' }}
              </button>
            </template>
          </div>
        </div>

        <!-- Petition: no change (both parties) -->
        <div class="notify-section">
          <div class="notify-section-header" @click="toggleSection('petition_resolved_no_change')">
            <div class="notify-section-title">
              <span class="notify-section-icon">✔️</span>
              <span>Petition — no change</span>
            </div>
            <span class="notify-section-sub">When assignee confirms they made the payment (notify both parties)</span>
            <span class="notify-section-chevron" :class="{ expanded: expandedSections.petition_resolved_no_change }">▼</span>
          </div>
          <div v-if="expandedSections.petition_resolved_no_change" class="notify-section-content">
            <div class="notify-toggle-row">
              <label class="notify-toggle">
                <input v-model="configs.petition_resolved_no_change.enabled" type="checkbox" />
                <span class="notify-toggle-slider"></span>
              </label>
              <span class="notify-toggle-label">Enable</span>
            </div>
            <template v-if="configs.petition_resolved_no_change.enabled">
              <div class="notify-form-group">
                <label class="notify-label">Title</label>
                <input v-model="configs.petition_resolved_no_change.title" type="text" class="notify-input" />
              </div>
              <div class="notify-form-group">
                <label class="notify-label">Message template</label>
                <div class="notify-var-chips">
                  <span class="notify-var-chip" @click="insertVar('petition_resolved_no_change', '{payee_name}')">{payee_name}</span>
                  <span class="notify-var-chip" @click="insertVar('petition_resolved_no_change', '{amount}')">{amount}</span>
                  <span class="notify-var-chip" @click="insertVar('petition_resolved_no_change', '{payment_date}')">{payment_date}</span>
                </div>
                <textarea ref="petitionResolvedInput" v-model="configs.petition_resolved_no_change.template" class="notify-textarea" rows="3"></textarea>
              </div>
              <button class="notify-btn notify-btn-test" :disabled="testing === 'petition_resolved_no_change'" @click="testNotification('petition_resolved_no_change')">
                {{ testing === 'petition_resolved_no_change' ? 'Sending...' : '📱 Test Notification' }}
              </button>
            </template>
          </div>
        </div>

        <!-- Save Button -->
        <div class="notify-actions">
          <button class="notify-btn notify-btn-primary" :disabled="saving" @click="saveAll">
            {{ saving ? 'Saving...' : 'Save All Notification Settings' }}
          </button>
        </div>

        <div v-if="message" :class="['notify-message', message.type]">
          {{ message.text }}
        </div>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getApiBase } from '../../lib/api-base'

interface NotificationConfig {
  id?: number
  event_type: string
  enabled: boolean
  title: string
  template: string
  days_before_due?: number | null
  reminder_send_time?: string | null
}

const loading = ref(true)
const saving = ref(false)
const testing = ref<string | null>(null)
const isAddon = ref(false)
const message = ref<{ type: 'success' | 'error'; text: string } | null>(null)

const expandedSections = reactive({
  new_bill: true,
  payment_received: false,
  due_reminder: false,
  balance_change: false,
  late_fee: false,
  payment_claimed: false,
  payment_unclaimed: false,
  payment_claim_prompt: false,
  petition_assignee_question: false,
  petition_resolved_no_change: false,
})

const configs = reactive<Record<string, NotificationConfig>>({
  new_bill: { event_type: 'new_bill', enabled: true, title: 'Con Edison Billing', template: 'A new bill for {amount} has posted, due {due_date}' },
  payment_received: { event_type: 'payment_received', enabled: true, title: 'Con Edison Payment', template: 'Payment of {amount} received. Remaining balance: {balance}' },
  due_reminder: { event_type: 'due_reminder', enabled: true, title: 'Con Edison Reminder', template: 'Your bill of {amount} is due {days_until_text} on {due_date}', days_before_due: 3, reminder_send_time: '09:00' },
  balance_change: { event_type: 'balance_change', enabled: true, title: 'Con Edison Balance', template: 'Your account balance changed from {old_balance} to {new_balance}' },
  late_fee: { event_type: 'late_fee', enabled: true, title: 'Con Edison Late Fee', template: '{late_fee_amount} has been added to your account balance as a late fee charge. To avoid late fees pay bill by the due date.' },
  payment_claimed: { event_type: 'payment_claimed', enabled: true, title: 'Con Edison Payment Claimed', template: '{payee_name} has claimed a payment of {amount} made on {payment_date}. If this was in error you can unclaim the payment via the account ledger.' },
  payment_unclaimed: { event_type: 'payment_unclaimed', enabled: true, title: 'Con Edison Payment Unclaimed', template: '{payee_name} has unclaimed a payment of {amount} made on {payment_date}. If this was in error you can claim the payment via the account ledger.' },
  payment_claim_prompt: {
    event_type: 'payment_claim_prompt',
    enabled: true,
    title: 'Payment to claim',
    template: 'Did you make the {amount} payment on {payment_date}? (Tap & hold to respond)',
  },
  petition_assignee_question: {
    event_type: 'petition_assignee_question',
    enabled: true,
    title: 'Payment petition',
    template:
      '{petitioner_name} has requested a payment petition for payment made on {payment_date} in the amount of {amount}. Are you sure you made this payment? (Tap & hold to respond)',
  },
  petition_resolved_no_change: {
    event_type: 'petition_resolved_no_change',
    enabled: true,
    title: 'Payment petition resolved',
    template:
      '{payee_name} is sure they made the payment posted on {payment_date}, in the amount of {amount}. No changes have been made.',
  },
})

const newBillInput = ref<HTMLTextAreaElement | null>(null)
const paymentReceivedInput = ref<HTMLTextAreaElement | null>(null)
const dueReminderInput = ref<HTMLTextAreaElement | null>(null)
const balanceChangeInput = ref<HTMLTextAreaElement | null>(null)
const lateFeeInput = ref<HTMLTextAreaElement | null>(null)
const paymentClaimedInput = ref<HTMLTextAreaElement | null>(null)
const paymentUnclaimedInput = ref<HTMLTextAreaElement | null>(null)
const paymentClaimPromptInput = ref<HTMLTextAreaElement | null>(null)
const petitionAssigneeInput = ref<HTMLTextAreaElement | null>(null)
const petitionResolvedInput = ref<HTMLTextAreaElement | null>(null)
const testPayeeId = ref<number | ''>('')

function toggleSection(section: keyof typeof expandedSections) {
  expandedSections[section] = !expandedSections[section]
}

function insertVar(eventType: string, variable: string) {
  const inputMap: Record<string, typeof newBillInput> = {
    new_bill: newBillInput,
    payment_received: paymentReceivedInput,
    due_reminder: dueReminderInput,
    balance_change: balanceChangeInput,
    late_fee: lateFeeInput,
    payment_claimed: paymentClaimedInput,
    payment_unclaimed: paymentUnclaimedInput,
    payment_claim_prompt: paymentClaimPromptInput,
    petition_assignee_question: petitionAssigneeInput,
    petition_resolved_no_change: petitionResolvedInput,
  }
  
  const inputRef = inputMap[eventType]
  const textarea = inputRef?.value
  if (!textarea) {
    configs[eventType].template += variable
    return
  }
  
  const start = textarea.selectionStart || 0
  const end = textarea.selectionEnd || 0
  const text = configs[eventType].template
  configs[eventType].template = text.slice(0, start) + variable + text.slice(end)
  
  setTimeout(() => {
    textarea.focus()
    const newPos = start + variable.length
    textarea.setSelectionRange(newPos, newPos)
  }, 0)
}

const payeesWithNotify = ref<{ id: number; name: string; notify_service: string | null }[]>([])

async function loadConfigs() {
  loading.value = true
  try {
    // Check addon status
    const haRes = await fetch(`${getApiBase()}/ha-notify-services`)
    if (haRes.ok) {
      const d = await haRes.json()
      isAddon.value = d.is_addon === true
    }

    // Load payees with notify service for test dropdown
    const payeesRes = await fetch(`${getApiBase()}/payee-users`)
    if (payeesRes.ok) {
      const d = await payeesRes.json()
      payeesWithNotify.value = (d.users || []).filter((u: { notify_service: string | null }) => u.notify_service)
    }

    // Load notification configs
    const res = await fetch(`${getApiBase()}/notification-config`)
    if (res.ok) {
      const d = await res.json()
      const loadedConfigs = d.configs || []
      for (const cfg of loadedConfigs) {
        if (configs[cfg.event_type]) {
          configs[cfg.event_type] = { ...configs[cfg.event_type], ...cfg }
        }
      }
    }
  } catch (e) {
    console.error('Failed to load notification configs:', e)
    message.value = { type: 'error', text: 'Failed to load settings' }
  } finally {
    loading.value = false
  }
}

async function saveAll() {
  saving.value = true
  message.value = null
  
  try {
    const eventTypes = [
      'new_bill',
      'payment_received',
      'due_reminder',
      'balance_change',
      'late_fee',
      'payment_claimed',
      'payment_unclaimed',
      'payment_claim_prompt',
      'petition_assignee_question',
      'petition_resolved_no_change',
    ]
    let success = true
    
    for (const eventType of eventTypes) {
      const cfg = configs[eventType]
      const res = await fetch(`${getApiBase()}/notification-config/${eventType}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          enabled: cfg.enabled,
          title: cfg.title,
          template: cfg.template,
          days_before_due: cfg.days_before_due,
          reminder_send_time: cfg.reminder_send_time ?? undefined
        })
      })
      if (!res.ok) {
        success = false
      }
    }
    
    if (success) {
      message.value = { type: 'success', text: 'Notification settings saved!' }
    } else {
      message.value = { type: 'error', text: 'Some settings failed to save' }
    }
  } catch (e) {
    message.value = { type: 'error', text: 'Failed to save settings' }
  } finally {
    saving.value = false
  }
}

async function testNotification(eventType: string) {
  testing.value = eventType
  message.value = null
  
  try {
    let url = `${getApiBase()}/notification-config/test/${eventType}`
    if (testPayeeId.value !== '') {
      url += `?payee_id=${testPayeeId.value}`
    }
    const res = await fetch(url, {
      method: 'POST'
    })
    const d = await res.json()
    
    if (res.ok) {
      message.value = { type: 'success', text: d.message || 'Test notification sent!' }
    } else {
      message.value = { type: 'error', text: d.detail || 'Failed to send test notification' }
    }
  } catch (e) {
    message.value = { type: 'error', text: 'Failed to send test notification' }
  } finally {
    testing.value = null
  }
}

onMounted(() => {
  loadConfigs()
})
</script>

<style scoped>
.notify-settings { display: flex; flex-direction: column; gap: 1rem; }

.notify-loading { text-align: center; padding: 3rem; color: #666; }
.notify-spinner { width: 32px; height: 32px; border: 3px solid #e0e0e0; border-top-color: #03a9f4; border-radius: 50%; margin: 0 auto 1rem; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.notify-addon-notice { display: flex; gap: 1rem; padding: 1.25rem; background: #fff3e0; border: 1px solid #ffcc80; border-radius: 12px; }
.notify-notice-icon { font-size: 1.5rem; }
.notify-addon-notice p { margin: 0.5rem 0 0; font-size: 0.9rem; color: #666; }

.notify-test-select-row { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem; padding: 0.75rem 1rem; background: #e3f2fd; border-radius: 8px; border: 1px solid #90caf9; }
.notify-test-select-row .notify-label { margin: 0; font-weight: 500; white-space: nowrap; }
.notify-select { padding: 0.4rem 0.75rem; border: 1px solid #ddd; border-radius: 6px; font-size: 0.9rem; min-width: 200px; }

.notify-section { background: white; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.notify-section-header { display: flex; flex-wrap: wrap; align-items: center; gap: 0.75rem; padding: 1rem 1.25rem; cursor: pointer; background: #fafafa; border-bottom: 1px solid transparent; transition: background 0.15s; }
.notify-section-header:hover { background: #f0f0f0; }
.notify-section-title { display: flex; align-items: center; gap: 0.5rem; font-weight: 600; }
.notify-section-icon { font-size: 1.25rem; }
.notify-section-sub { flex: 1; font-size: 0.85rem; color: #666; }
.notify-section-chevron { font-size: 0.75rem; color: #999; transition: transform 0.2s; }
.notify-section-chevron.expanded { transform: rotate(180deg); }

.notify-section-content { padding: 1.25rem; border-top: 1px solid #e0e0e0; }

.notify-toggle-row { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem; }
.notify-toggle { position: relative; width: 44px; height: 24px; cursor: pointer; }
.notify-toggle input { opacity: 0; width: 0; height: 0; }
.notify-toggle-slider { position: absolute; inset: 0; background: #ccc; border-radius: 24px; transition: background 0.2s; }
.notify-toggle-slider::before { content: ''; position: absolute; width: 18px; height: 18px; left: 3px; bottom: 3px; background: white; border-radius: 50%; transition: transform 0.2s; }
.notify-toggle input:checked + .notify-toggle-slider { background: #4caf50; }
.notify-toggle input:checked + .notify-toggle-slider::before { transform: translateX(20px); }
.notify-toggle-label { font-weight: 500; }

.notify-form-group { margin-bottom: 1rem; }
.notify-hint { margin: 0.35rem 0 0; font-size: 0.8rem; color: #666; }
.notify-label { display: block; font-weight: 500; margin-bottom: 0.5rem; font-size: 0.9rem; }
.notify-input { width: 100%; padding: 0.6rem 0.75rem; border: 1px solid #ddd; border-radius: 6px; font-size: 0.95rem; }
.notify-input:focus { outline: none; border-color: #03a9f4; box-shadow: 0 0 0 2px rgba(3, 169, 244, 0.15); }
.notify-input-small { max-width: 100px; }

.notify-textarea { width: 100%; padding: 0.6rem 0.75rem; border: 1px solid #ddd; border-radius: 6px; font-size: 0.95rem; font-family: inherit; resize: vertical; }
.notify-textarea:focus { outline: none; border-color: #03a9f4; box-shadow: 0 0 0 2px rgba(3, 169, 244, 0.15); }

.notify-var-chips { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-bottom: 0.5rem; }
.notify-var-chip { display: inline-block; padding: 0.25rem 0.5rem; background: #e3f2fd; color: #1565c0; font-size: 0.75rem; font-family: monospace; border-radius: 4px; cursor: pointer; border: 1px solid #90caf9; transition: all 0.15s; }
.notify-var-chip:hover { background: #bbdefb; transform: translateY(-1px); }

.notify-btn { padding: 0.6rem 1.25rem; border: none; border-radius: 6px; font-size: 0.9rem; font-weight: 500; cursor: pointer; transition: all 0.15s; }
.notify-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.notify-btn-primary { background: #1976d2; color: white; }
.notify-btn-primary:hover:not(:disabled) { background: #1565c0; }
.notify-btn-test { background: #e3f2fd; color: #1976d2; border: 1px solid #90caf9; margin-top: 0.5rem; }
.notify-btn-test:hover:not(:disabled) { background: #bbdefb; }

.notify-actions { margin-top: 0.5rem; }

.notify-message { padding: 0.75rem 1rem; border-radius: 6px; margin-top: 1rem; }
.notify-message.success { background: #e8f5e9; color: #2e7d32; }
.notify-message.error { background: #ffebee; color: #c62828; }
</style>
