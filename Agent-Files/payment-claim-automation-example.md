# Payment Claim Automation Example

Example Home Assistant automation for recording ConEd payment claim Yes/No responses from mobile notifications. **You must create this automation** for tapping Yes/No to work; without it, the notification dismisses but no claim is recorded.

## Overview

When payees tap **Yes** or **No** on a "Did you make this payment?" notification, Home Assistant fires:
- **Android:** `mobile_app_notification_action` with `action` like `CONED_CLAIM_YES_123_45`
- **iOS:** `ios.notification_action` with `action` in the event data

The action format is `CONED_CLAIM_YES_<payment_id>_<payee_id>` or `CONED_CLAIM_NO_<payment_id>_<payee_id>`.

## Recommended: Simple claim-action endpoint (single URL, no parsing)

The addon provides `POST /api/payments/claim-action` that accepts the raw action string. Use this so your rest_command needs only a **static URL** (no payment_id in path).

### 1. Add rest_command

In `configuration.yaml` (or `rest_command.yaml`). Replace `core_coned` with your addon slug (Settings → Add-ons → Con Edison → check the slug).

```yaml
rest_command:
  coned_payee_claim:
    method: POST
    url: "http://homeassistant.local:8123/api/coned/ingress/core_coned/api/payments/claim-action"
    content_type: "application/json"
    payload_template: '{"action": "{{ action }}"}'
```

### 2. Add automation

Use **two triggers** if you have both Android and iOS devices (the event type differs).

```yaml
alias: ConEd Payment Claim - Record Yes/No
description: Record payee claim when user taps Yes or No on payment notification
trigger:
  - platform: event
    event_type: mobile_app_notification_action
  - platform: event
    event_type: ios.notification_action
condition:
  - condition: template
    value_template: >
      {{ trigger.event.data.action is defined
         and trigger.event.data.action starts with 'CONED_CLAIM_' }}
action:
  - service: rest_command.coned_payee_claim
    data:
      action: "{{ trigger.event.data.action }}"
```

### 3. Verify

After saving and reloading automations, tap Yes on a payment claim notification. The ledger should show the payment as claimed for that payee.

---

## Alternative: Parse and call payee-claim (URL includes payment_id)

If you prefer the original endpoint `POST /api/payments/{payment_id}/payee-claim`:

```yaml
alias: ConEd Payment Claim - Record Yes/No
trigger:
  - platform: event
    event_type: mobile_app_notification_action
  - platform: event
    event_type: ios.notification_action
condition:
  - condition: template
    value_template: "{{ trigger.event.data.action is defined and trigger.event.data.action starts with 'CONED_CLAIM_' }}"
action:
  - variables:
      action: "{{ trigger.event.data.action }}"
      parts: "{{ action.split('_') }}"
      claimed: "{{ parts[2] == 'YES' }}"
      payment_id: "{{ parts[3] | int }}"
      payee_id: "{{ parts[4] | int }}"
  - service: rest_command.coned_payee_claim
    data:
      payment_id: "{{ payment_id }}"
      payee_id: "{{ payee_id }}"
      claimed: "{{ claimed }}"
```

**REST command** (requires `url_template` in HA 2024.4+ or script + http.request):

```yaml
rest_command:
  coned_payee_claim:
    method: POST
    url_template: "http://homeassistant.local:8123/api/coned/ingress/core_coned/api/payments/{{ payment_id }}/payee-claim"
    content_type: "application/json"
    payload_template: '{"payee_id": {{ payee_id }}, "claimed": {{ claimed | lower }}}'
```

---

**Purpose:** Enable Yes/No claim responses so the addon can assign payments.
