/**
 * Time offset utility for manual time adjustment across the app
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api'

let cachedTimeOffset: number | null = null
let timeOffsetPromise: Promise<number> | null = null

/**
 * Get the configured time offset from the API (in hours)
 */
export async function getTimeOffset(): Promise<number> {
  // Return cached value if available
  if (cachedTimeOffset !== null) {
    return cachedTimeOffset
  }

  // Return existing promise if already fetching
  if (timeOffsetPromise) {
    return timeOffsetPromise
  }

  // Fetch time offset from API
  timeOffsetPromise = fetch(`${API_BASE_URL}/app-settings`)
    .then(response => response.json())
    .then(data => {
      const offset = parseFloat(data.time_offset_hours || 0)
      cachedTimeOffset = offset
      timeOffsetPromise = null
      return offset as number
    })
    .catch(error => {
      console.error('Failed to fetch time offset:', error)
      const offset = 0
      cachedTimeOffset = offset
      timeOffsetPromise = null
      return offset as number
    })

  return timeOffsetPromise
}

/**
 * Apply time offset to a date
 */
function applyTimeOffset(date: Date, offsetHours: number): Date {
  const adjusted = new Date(date)
  adjusted.setHours(adjusted.getHours() + offsetHours)
  return adjusted
}

/**
 * Format a timestamp using the configured time offset
 */
export async function formatTimestamp(
  timestamp: string | Date,
  options?: Intl.DateTimeFormatOptions
): Promise<string> {
  try {
    const offsetHours = await getTimeOffset()
    const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp
    const adjustedDate = applyTimeOffset(date, offsetHours)
    
    const defaultOptions: Intl.DateTimeFormatOptions = {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
      ...options
    }
    
    return adjustedDate.toLocaleString('en-US', defaultOptions)
  } catch (error) {
    console.error('Failed to format timestamp:', error)
    return String(timestamp)
  }
}

/**
 * Format a date (without time) using the configured time offset
 */
export async function formatDate(
  timestamp: string | Date,
  options?: Intl.DateTimeFormatOptions
): Promise<string> {
  try {
    const offsetHours = await getTimeOffset()
    const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp
    const adjustedDate = applyTimeOffset(date, offsetHours)
    
    const defaultOptions: Intl.DateTimeFormatOptions = {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      ...options
    }
    
    return adjustedDate.toLocaleDateString('en-US', defaultOptions)
  } catch (error) {
    console.error('Failed to format date:', error)
    return String(timestamp)
  }
}

/**
 * Format a time (without date) using the configured time offset
 */
export async function formatTime(
  timestamp: string | Date,
  options?: Intl.DateTimeFormatOptions
): Promise<string> {
  try {
    const offsetHours = await getTimeOffset()
    const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp
    const adjustedDate = applyTimeOffset(date, offsetHours)
    
    const defaultOptions: Intl.DateTimeFormatOptions = {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
      ...options
    }
    
    return adjustedDate.toLocaleTimeString('en-US', defaultOptions)
  } catch (error) {
    console.error('Failed to format time:', error)
    return String(timestamp)
  }
}

/**
 * Clear the cached time offset (call after time offset settings change)
 */
export function clearTimezoneCache() {
  cachedTimeOffset = null
  timeOffsetPromise = null
}

