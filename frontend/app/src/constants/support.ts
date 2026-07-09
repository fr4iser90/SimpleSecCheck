export const GITHUB_REPO = 'https://github.com/fr4iser90/SimpleSecCheck'

/** PayPal Send link — override at build time via VITE_SUPPORT_DONATE_URL if needed. */
const donateFromEnv = import.meta.env.VITE_SUPPORT_DONATE_URL as string | undefined

export const PAYPAL_DONATE_URL = donateFromEnv?.trim() || 'https://www.paypal.me/SupportMySnacks'
