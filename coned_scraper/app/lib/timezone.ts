/**
 * Timezone utility - converts UTC timestamps to browser's local time
 * No server dependency - uses browser's system time directly
 */

/**
 * Get current time in browser's timezone (for live clocks)
 */
export function getCurrentTime(): Date {
  return new Date()
}

/**
 * Format a UTC timestamp to browser's local time
 * Assumes timestamps from server are in UTC
 */
export function formatTimestamp(
  timestamp: string | Date,
  options?: Intl.DateTimeFormatOptions
): string {
  try {
    let date: Date
    
    if (typeof timestamp === 'string') {
      // If timestamp doesn't have timezone info, assume it's UTC
      const hasTimezone = timestamp.includes('Z') || timestamp.includes('+') || /T.*-\d{2}:\d{2}$/.test(timestamp)
      if (!hasTimezone && timestamp.includes('T')) {
        // Append Z to treat as UTC
        date = new Date(timestamp + 'Z')
      } else {
        date = new Date(timestamp)
      }
    } else {
      date = timestamp
    }
    
    // Validate date
    if (isNaN(date.getTime())) {
      return String(timestamp)
    }
    
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
    
    // toLocaleString automatically converts to browser's local timezone
    return date.toLocaleString('en-US', defaultOptions)
  } catch (error) {
    console.error('Failed to format timestamp:', error)
    return String(timestamp)
  }
}

/**
 * Format a UTC timestamp to local date only
 */
export function formatDate(
  timestamp: string | Date,
  options?: Intl.DateTimeFormatOptions
): string {
  try {
    let date: Date
    
    if (typeof timestamp === 'string') {
      const hasTimezone = timestamp.includes('Z') || timestamp.includes('+') || /T.*-\d{2}:\d{2}$/.test(timestamp)
      if (!hasTimezone && timestamp.includes('T')) {
        date = new Date(timestamp + 'Z')
      } else {
        date = new Date(timestamp)
      }
    } else {
      date = timestamp
    }
    
    if (isNaN(date.getTime())) {
      return String(timestamp)
    }
    
    const defaultOptions: Intl.DateTimeFormatOptions = {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      ...options
    }
    
    return date.toLocaleDateString('en-US', defaultOptions)
  } catch (error) {
    console.error('Failed to format date:', error)
    return String(timestamp)
  }
}

/**
 * Format a UTC timestamp to local time only
 */
export function formatTime(
  timestamp: string | Date,
  options?: Intl.DateTimeFormatOptions
): string {
  try {
    let date: Date
    
    if (typeof timestamp === 'string') {
      const hasTimezone = timestamp.includes('Z') || timestamp.includes('+') || /T.*-\d{2}:\d{2}$/.test(timestamp)
      if (!hasTimezone && timestamp.includes('T')) {
        date = new Date(timestamp + 'Z')
      } else {
        date = new Date(timestamp)
      }
    } else {
      date = timestamp
    }
    
    if (isNaN(date.getTime())) {
      return String(timestamp)
    }
    
    const defaultOptions: Intl.DateTimeFormatOptions = {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
      ...options
    }
    
    return date.toLocaleTimeString('en-US', defaultOptions)
  } catch (error) {
    console.error('Failed to format time:', error)
    return String(timestamp)
  }
}

/**
 * Get current date formatted
 */
export function getCurrentDate(options?: Intl.DateTimeFormatOptions): string {
  return formatDate(new Date(), options)
}

/**
 * Get current time formatted
 */
export function getCurrentTimeFormatted(options?: Intl.DateTimeFormatOptions): string {
  return formatTime(new Date(), options)
}

// Legacy exports for compatibility - these now just call the sync versions
export async function getTimeOffset(): Promise<number> {
  return 0 // No longer used - browser handles timezone
}

export function clearTimezoneCache() {
  // No-op - no cache needed anymore
}

// Alias for backward compatibility with async calls
export const formatTZ = formatTimestamp
