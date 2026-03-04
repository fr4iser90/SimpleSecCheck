import type { FrontendConfig } from '../hooks/useConfig'

export const shouldUseSessionEndpoints = (config: FrontendConfig | null): boolean => {
  return Boolean(config?.is_production || config?.features.session_management)
}

export const getReportEndpoint = (
  scanId: string | null | undefined,
  config: FrontendConfig | null,
): string => {
  if (!scanId) {
    return '/api/scan/report'
  }

  return shouldUseSessionEndpoints(config)
    ? `/api/my-results/${scanId}/report`
    : `/api/results/${scanId}/report`
}