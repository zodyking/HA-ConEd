type HassElement = Element & {
  hass?: { user?: { id?: string; name?: string; is_admin?: boolean } }
}

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

/** Documents to search: own, parent (panel iframe), top (nested iframe layouts). */
function getCandidateDocuments(): Document[] {
  const out: Document[] = []
  const seen = new Set<Document>()
  const add = (doc: Document | null | undefined) => {
    if (doc && !seen.has(doc)) {
      seen.add(doc)
      out.push(doc)
    }
  }
  try {
    add(typeof document !== 'undefined' ? document : undefined)
    if (typeof window !== 'undefined') {
      try {
        add(window.parent?.document)
      } catch {
        /* cross-origin */
      }
      try {
        if (window.top && window.top !== window)
          add(window.top.document)
      } catch {
        /* cross-origin */
      }
    }
  } catch {
    /* ignore */
  }
  return out
}

function findFirstHomeAssistant(): HassElement | null {
  for (const doc of getCandidateDocuments()) {
    const el = findHomeAssistant(doc)
    if (el) return el
  }
  return null
}

/**
 * Gets the current HA user's ID when running inside a Home Assistant panel iframe.
 * Returns null when not in HA or when hass.user.id is unavailable.
 * Traverses shadow DOM; checks document, parent, and top windows for nested iframes.
 */
export function getHaUserId(): string | null {
  try {
    if (typeof window === 'undefined') return null
    const el = findFirstHomeAssistant()
    return el?.hass?.user?.id ?? null
  } catch {
    return null
  }
}

/**
 * Current HA user's display name (`hass.user.name`), when available.
 */
export function getHaUserName(): string | null {
  try {
    if (typeof window === 'undefined') return null
    const el = findFirstHomeAssistant()
    const n = el?.hass?.user?.name
    if (n == null) return null
    const t = String(n).trim()
    return t || null
  } catch {
    return null
  }
}

/**
 * True when `hass.user.id` or `hass.user.name` is available.
 * `isInHaPanel()` can be true earlier (shell present) while this is still false.
 */
export function isHaUserIdentityReady(): boolean {
  return getHaUserId() != null || getHaUserName() != null
}

/**
 * Whether we're running inside Home Assistant (panel iframe or nested layout).
 */
export function isInHaPanel(): boolean {
  try {
    if (typeof window === 'undefined') return false
    return !!findFirstHomeAssistant()
  } catch {
    return false
  }
}

/**
 * Detects if the current HA user is an admin when running inside Home Assistant.
 */
export function getHaUserIsAdmin(): boolean {
  try {
    if (typeof window === 'undefined') return false
    const el = findFirstHomeAssistant()
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
