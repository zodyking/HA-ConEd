/**
 * Timezone utility for consistent timestamp formatting across the app
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api'

let cachedTimezone: string | null = null
let timezonePromise: Promise<string> | null = null

/**
 * Get the configured timezone from the API
 */
export async function getTimezone(): Promise<string> {
  // Return cached value if available
  if (cachedTimezone) {
    return cachedTimezone
  }

  // Return existing promise if already fetching
  if (timezonePromise) {
    return timezonePromise
  }

  // Fetch timezone from API
  timezonePromise = fetch(`${API_BASE_URL}/app-settings`)
    .then(response => response.json())
    .then(data => {
      cachedTimezone = data.timezone || 'America/New_York'
      timezonePromise = null
      return cachedTimezone
    })
    .catch(error => {
      console.error('Failed to fetch timezone:', error)
      cachedTimezone = 'America/New_York'
      timezonePromise = null
      return cachedTimezone
    })

  return timezonePromise
}

/**
 * Format a timestamp using the configured timezone
 */
export async function formatTimestamp(
  timestamp: string | Date,
  options?: Intl.DateTimeFormatOptions
): Promise<string> {
  try {
    const timezone = await getTimezone()
    const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp
    
    const defaultOptions: Intl.DateTimeFormatOptions = {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
      timeZone: timezone,
      ...options
    }
    
    return date.toLocaleString('en-US', defaultOptions)
  } catch (error) {
    console.error('Failed to format timestamp:', error)
    return String(timestamp)
  }
}

/**
 * Format a date (without time) using the configured timezone
 */
export async function formatDate(
  timestamp: string | Date,
  options?: Intl.DateTimeFormatOptions
): Promise<string> {
  try {
    const timezone = await getTimezone()
    const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp
    
    const defaultOptions: Intl.DateTimeFormatOptions = {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      timeZone: timezone,
      ...options
    }
    
    return date.toLocaleDateString('en-US', defaultOptions)
  } catch (error) {
    console.error('Failed to format date:', error)
    return String(timestamp)
  }
}

/**
 * Format a time (without date) using the configured timezone
 */
export async function formatTime(
  timestamp: string | Date,
  options?: Intl.DateTimeFormatOptions
): Promise<string> {
  try {
    const timezone = await getTimezone()
    const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp
    
    const defaultOptions: Intl.DateTimeFormatOptions = {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
      timeZone: timezone,
      ...options
    }
    
    return date.toLocaleTimeString('en-US', defaultOptions)
  } catch (error) {
    console.error('Failed to format time:', error)
    return String(timestamp)
  }
}

/**
 * Clear the cached timezone (call after timezone settings change)
 */
export function clearTimezoneCache() {
  cachedTimezone = null
  timezonePromise = null
}

