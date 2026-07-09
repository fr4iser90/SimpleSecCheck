export const GITHUB_REPO = 'https://github.com/fr4iser90/SimpleSecCheck'

/** Set at build time, e.g. Ko-fi / GitHub Sponsors / PayPal. */
const donateFromEnv = import.meta.env.VITE_SUPPORT_DONATE_URL as string | undefined

export const SUPPORT_DONATE_URL = donateFromEnv?.trim() || ''
export const HAS_DONATE_LINK = SUPPORT_DONATE_URL.length > 0
