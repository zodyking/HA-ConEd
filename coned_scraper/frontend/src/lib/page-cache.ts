/**
 * Last successful ledger/history payloads for stale-while-revalidate.
 * Memory covers tab changes in this session; localStorage survives reloads.
 * Store view data only — never credentials or secrets.
 */

export interface PageCacheEntry<T> {
  savedAt: number
  payload: T
}

const memory = new Map<string, PageCacheEntry<unknown>>()
const STORAGE_PREFIX = 'ha-coned:page-cache:v1:'

export const LEDGER_CACHE_KEY = 'ledger'
export const HISTORY_CACHE_KEY = 'history'

export function readPageCache<T>(
  key: string,
  isPayload: (value: unknown) => value is T,
): PageCacheEntry<T> | null {
  const mem = memory.get(key)
  if (mem && isPayload(mem.payload)) {
    return mem as PageCacheEntry<T>
  }

  try {
    const raw = localStorage.getItem(STORAGE_PREFIX + key)
    if (!raw) return null
    const parsed: unknown = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object') return null
    const savedAt = (parsed as { savedAt?: unknown }).savedAt
    const payload = (parsed as { payload?: unknown }).payload
    if (typeof savedAt !== 'number' || !isPayload(payload)) return null
    const entry: PageCacheEntry<T> = { savedAt, payload }
    memory.set(key, entry)
    return entry
  } catch {
    return null
  }
}

export function writePageCache<T>(key: string, payload: T): void {
  const entry: PageCacheEntry<T> = { savedAt: Date.now(), payload }
  memory.set(key, entry)
  try {
    localStorage.setItem(STORAGE_PREFIX + key, JSON.stringify(entry))
  } catch {
    // Quota or blocked storage: this session still uses the memory copy.
  }
}
