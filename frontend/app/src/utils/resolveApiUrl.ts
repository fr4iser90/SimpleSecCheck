/**
 * Build same-origin API URLs using the current page's scheme (https).
 * Prevents mixed-content blocks when the document has <base href="http://...">
 * or other tooling resolves root-relative paths as http on an https site.
 */
export function resolveApiUrl(pathOrUrl: string): string {
  if (typeof window === 'undefined') {
    return pathOrUrl
  }

  if (pathOrUrl.startsWith('http://') || pathOrUrl.startsWith('https://')) {
    if (window.location.protocol === 'https:' && pathOrUrl.startsWith('http://')) {
      return `https://${pathOrUrl.slice('http://'.length)}`
    }
    return pathOrUrl
  }

  const path = pathOrUrl.startsWith('/') ? pathOrUrl : `/${pathOrUrl}`
  return `${window.location.origin}${path}`
}
