# TTS Message Examples

Each TTS message uses the format **(prefix), (message)**. Below are example outputs for each message type.

**Default prefix:** `Message from Con Edison.`

---

## new_bill

**Template:** `New bill is available for {month_range}.`

**Placeholder:** `{month_range}` — e.g. `Jan - Feb`, `Dec - Jan`

**Example output:**
> Message from Con Edison., New bill is available for Jan - Feb.

---

## payment_received

**Template:** `Payment of {amount} was received.`

**Placeholder:** `{amount}` — e.g. `$115.23`, `$250.00`

**Example output:**
> Message from Con Edison., Payment of $115.23 was received.

---

## balance_alert

**Template:** `Account balance is {balance}.`

**Placeholder:** `{balance}` — e.g. `$716.99`, `$0.00`

**Example output:**
> Message from Con Edison., Account balance is $716.99.
