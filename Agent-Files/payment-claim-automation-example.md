# Payment Claim Automation Example

Example Home Assistant automation for recording ConEd payment claim Yes/No responses from mobile notifications.

## Overview

When payees tap **Yes** or **No** on a "Did you make this payment?" notification, Home Assistant fires `mobile_app_notification_action` with an action string like:
- `CONED_CLAIM_YES_123_45` (payment 123, payee 45, claimed Yes)
- `CONED_CLAIM_NO_123_45` (payment 123, payee 45, claimed No)

This automation parses the action and calls the addon API to record the response.

## YAML Automation

```yaml
alias: ConEd Payment Claim - Record Yes/No
description: Record payee claim response when user taps Yes or No on payment notification
trigger:
  - platform: event
    event_type: mobile_app_notification_action
condition:
  - condition: template
    value_template: "{{ trigger.event.data.action starts with 'CONED_CLAIM_' }}"
action:
  - variables:
      action: "{{ trigger.event.data.action }}"
      parts: "{{ action.split('_') }}"
      # parts: ['CONED', 'CLAIM', 'YES' or 'NO', payment_id, payee_id]
      claimed: "{{ parts[2] == 'YES' }}"
      payment_id: "{{ parts[3] | int }}"
      payee_id: "{{ parts[4] | int }}"
  - service: rest_command.coned_payee_claim
    data:
      payment_id: "{{ payment_id }}"
      payee_id: "{{ payee_id }}"
      claimed: "{{ claimed }}"
```

## REST Command

Add to `configuration.yaml` (or create a `rest_command.yaml` and include it):

```yaml
rest_command:
  coned_payee_claim:
    method: POST
    url: !secret coned_ingress_url  # e.g. http://localhost:8123/api/coned/ingress/core_coned
    content_type: "application/json"
    payload: >
      {
        "payee_id": "{{ payee_id }}",
        "claimed": {{ claimed | lower }}
      }
    # For Ingress, path is relative to base; append the API path:
    # In HA, use a template or full URL in secrets
```

**Alternative using a full URL in secrets** (`secrets.yaml`):

```yaml
coned_ingress_base: "http://homeassistant.local:8123/api/coned/ingress/core_coned"
```

Then in `configuration.yaml`:

```yaml
rest_command:
  coned_payee_claim:
    method: POST
    url: "{{ config.coned_ingress_base }}/api/payments/{{ payment_id }}/payee-claim"
    content_type: "application/json"
    payload: '{"payee_id": {{ payee_id }}, "claimed": {{ claimed }}}'
```

**Note:** `rest_command` does not support Jinja in `url` directly in older HA versions. Use a template-based approach or a script that builds the URL and calls `http.request`.

### Simpler approach: Script + HTTP

```yaml
script:
  coned_payee_claim:
    sequence:
      - variables:
          action: "{{ action }}"
          parts: "{{ action.split('_') }}"
          claimed: "{{ parts[2] == 'YES' }}"
          payment_id: "{{ parts[3] }}"
          payee_id: "{{ parts[4] }}"
      - service: http.request
        method: POST
        url: "http://localhost:8123/api/coned/ingress/core_coned/api/payments/{{ payment_id }}/payee-claim"
        headers:
          Authorization: "Bearer {{ state_attr('person.xxx', 'user_id') }}"
        content_type: "application/json"
        data:
          payee_id: "{{ payee_id | int }}"
          claimed: "{{ claimed }}"
```

Replace `core_coned` with your addon slug. For Ingress, the request is sent to HA which proxies to the addon; auth may use the HA token from the notification context.

### Recommended: use `coned.api_call` if the addon exposes it

If the addon provides a dedicated script/helper, use that instead. Otherwise the HTTP approach above works.

---

**Purpose:** 1-line doc for payment claim automation setup.
