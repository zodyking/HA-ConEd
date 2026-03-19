type HassElement = Element & { hass?: { user?: { id?: string; is_admin?: boolean } } }

function findHomeAssistant(root: Document | ShadowRoot): HassElement | null {
  const el = root.querySelector?.('home-assistant') as HassElement | null
  if (el) return el
  const nodes = root.querySelectorAll?.('*') ?? []
  for (const node of nodes) {
    if (node.shadowRoot) {
      const found = findHomeAssistant(node.shadowRoot)
      if (found) return found
    }
  }
  return null
}

/**
 * Gets the current HA user's ID when running inside a Home Assistant panel iframe.
 * Returns null when not in HA or when hass.user.id is unavailable.
 * Traverses shadow DOM for modern HA frontend.
 */
export function getHaUserId(): string | null {
  try {
    if (typeof window === 'undefined') return null
    const doc = window.parent?.document ?? document
    const el = findHomeAssistant(doc)
    return el?.hass?.user?.id ?? null
  } catch {
    return null
  }
}

/**
 * Whether we're running inside a Home Assistant panel iframe (parent has home-assistant).
 * Traverses shadow DOM for modern HA frontend.
 */
export function isInHaPanel(): boolean {
  try {
    if (typeof window === 'undefined') return false
    const doc = window.parent?.document ?? document
    return !!findHomeAssistant(doc)
  } catch {
    return false
  }
}

/**
 * Detects if the current HA user is an admin when running inside a Home Assistant panel iframe.
 * Uses the parent window's hass object (hass.user.is_admin).
 * Returns false when not in HA or when the user is not an admin.
 * Traverses shadow DOM for modern HA frontend.
 */
export function getHaUserIsAdmin(): boolean {
  try {
    if (typeof window === 'undefined') return false
    const doc = window.parent?.document ?? document
    const el = findHomeAssistant(doc)
    return el?.hass?.user?.is_admin === true
  } catch {
    return false
  }
}

/**
 * Whether the Settings nav should be shown:
 * - Standalone (not in HA): true (full access)
 * - In HA: true only when user is admin
 */
export function shouldShowSettingsNav(): boolean {
  if (!isInHaPanel()) return true
  return getHaUserIsAdmin()
}

/**
 * Whether the admin PIN reset option should be shown (in HA as admin).
 * Only relevant when in HA panel; standalone has no HA admin concept.
 */
export function shouldShowAdminReset(): boolean {
  return isInHaPanel() && getHaUserIsAdmin()
}

/**
 * Waits for admin reset visibility (in HA as admin). Polls briefly because hass may load async.
 */
export function waitForAdminResetVisibility(options?: { maxAttempts?: number; intervalMs?: number }): Promise<boolean> {
  const { maxAttempts = 20, intervalMs = 100 } = options ?? {}
  return new Promise((resolve) => {
    let attempts = 0
    const check = () => {
      if (shouldShowAdminReset()) {
        resolve(true)
        return
      }
      if (!isInHaPanel()) {
        resolve(false)
        return
      }
      attempts++
      if (attempts >= maxAttempts) {
        resolve(false)
        return
      }
      setTimeout(check, intervalMs)
    }
    check()
  })
}

/**
 * Waits for Settings nav visibility to be determined.
 * - Standalone: resolves true immediately
 * - In HA: polls for hass.user.is_admin (hass may load async)
 */
export function waitForSettingsNavVisibility(options?: { maxAttempts?: number; intervalMs?: number }): Promise<boolean> {
  const { maxAttempts = 20, intervalMs = 100 } = options ?? {}
  return new Promise((resolve) => {
    let attempts = 0
    const check = () => {
      if (shouldShowSettingsNav()) {
        resolve(true)
        return
      }
      if (!isInHaPanel()) {
        resolve(false)
        return
      }
      attempts++
      if (attempts >= maxAttempts) {
        resolve(false)
        return
      }
      setTimeout(check, intervalMs)
    }
    check()
  })
}
