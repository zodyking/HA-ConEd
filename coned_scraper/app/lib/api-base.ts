/**
 * Returns the API base URL for fetch calls.
 * Under HA ingress (subpath), derives from current location so relative requests resolve correctly.
 */
export function getApiBase(): string {
  if (typeof window === 'undefined') {
    return process.env.NEXT_PUBLIC_API_URL || '/api'
  }
  const pathname = window.location.pathname.replace(/\/$/, '')
  // Root or top-level: use explicit path
  if (!pathname || pathname === '/' || pathname === '/index') {
    return process.env.NEXT_PUBLIC_API_URL || '/api'
  }
  // Subpath (e.g. /api/hassio_ingress/XXX): append /api so fetch goes to same origin
  return pathname + '/api'
}
