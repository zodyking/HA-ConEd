/**
 * Returns the API base URL for fetch calls.
 * Under HA ingress (subpath), derives from current location so relative requests resolve correctly.
 */
export function getApiBase(): string {
  if (typeof window === 'undefined') {
    return '/api'
  }
  const pathname = window.location.pathname.replace(/\/$/, '')
  if (!pathname || pathname === '/' || pathname === '/index' || pathname === '/index.html') {
    return '/api'
  }
  return pathname + '/api'
}
