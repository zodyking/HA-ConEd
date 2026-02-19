/**
 * Timezone utility - converts UTC timestamps to browser's local time
 */
export function getCurrentTime(): Date {
  return new Date()
}

export function formatTimestamp(
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
    if (isNaN(date.getTime())) return String(timestamp)
    const defaultOptions: Intl.DateTimeFormatOptions = {
      year: 'numeric', month: 'long', day: 'numeric',
      hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true, ...options
    }
    return date.toLocaleString('en-US', defaultOptions)
  } catch {
    return String(timestamp)
  }
}

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
    if (isNaN(date.getTime())) return String(timestamp)
    const defaultOptions: Intl.DateTimeFormatOptions = {
      year: 'numeric', month: 'long', day: 'numeric', ...options
    }
    return date.toLocaleDateString('en-US', defaultOptions)
  } catch {
    return String(timestamp)
  }
}

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
    if (isNaN(date.getTime())) return String(timestamp)
    const defaultOptions: Intl.DateTimeFormatOptions = {
      hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true, ...options
    }
    return date.toLocaleTimeString('en-US', defaultOptions)
  } catch {
    return String(timestamp)
  }
}

export function getCurrentDate(options?: Intl.DateTimeFormatOptions): string {
  return formatDate(new Date(), options)
}

export function getCurrentTimeFormatted(options?: Intl.DateTimeFormatOptions): string {
  return formatTime(new Date(), options)
}

export const formatTZ = formatTimestamp
