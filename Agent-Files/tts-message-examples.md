# TTS Message Examples

Each TTS message uses the format **(prefix), (message)**. Below are example outputs for each message type.

**Default prefix:** `Message from Con Edison.`

---

## new_bill

**Template:** `Your new Con Edison bill for {month_range} is now available.`

**Placeholder:** `{month_range}` — e.g. `Jan - Feb`, `Dec - Jan`

**Example output:**
> Message from Con Edison., Your new Con Edison bill for Jan - Feb is now available.

---

## payment_received

**Template:** `Good news — your payment of {amount} has been received. Your account balance is now {balance}.`

**Placeholders:**
- `{amount}` — e.g. `$115.23`, `$250.00`
- `{balance}` — e.g. `$716.99`, `$0.00` (account balance after payment)

**Example output:**
> Message from Con Edison., Good news — your payment of $115.23 has been received. Your account balance is now $716.99.
