import type { FrontendConfig } from '../hooks/useConfig'

export const shouldUseSessionEndpoints = (config: FrontendConfig | null): boolean => {
  return Boolean(config?.features.session_management)
}

/** Report requires session/JWT or ?share_token=; send cookies. */
export const getReportEndpoint = (
  scanId: string | null | undefined,
  _config: FrontendConfig | null,
): string => {
  if (!scanId) {
    return '/api/scan/report'
  }
  return `/api/results/${scanId}/report`
}