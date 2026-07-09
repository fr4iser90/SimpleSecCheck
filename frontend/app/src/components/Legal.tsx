import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { resolveApiUrl } from '../utils/resolveApiUrl'
import { useTranslation } from '../i18n'

export interface LegalFooterLink {
  slug: string
  label: string
}

export interface LegalPublicConfig {
  enabled: boolean
  locale?: string
  cookie_notice_enabled?: boolean
  footer_links?: LegalFooterLink[]
}

const COOKIE_DISMISS_KEY = 'ssc_cookie_notice_dismissed'

const FOOTER_SLUG_KEYS: Record<string, string> = {
  impressum: 'legal.footer.impressum',
  privacy: 'legal.footer.privacy',
  terms: 'legal.footer.terms',
}

export function useLegalConfig() {
  const [legal, setLegal] = useState<LegalPublicConfig | null>(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const res = await fetch(resolveApiUrl('/api/legal'))
        if (!res.ok) return
        const data = await res.json()
        if (!cancelled) setLegal(data)
      } catch {
        /* optional */
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [])

  return legal
}

export function CookieNotice({ legal }: { legal: LegalPublicConfig | null }) {
  const { t } = useTranslation()
  const [dismissed, setDismissed] = useState(() => {
    try {
      return sessionStorage.getItem(COOKIE_DISMISS_KEY) === '1'
    } catch {
      return false
    }
  })

  if (!legal?.enabled || !legal.cookie_notice_enabled || dismissed) {
    return null
  }

  const dismiss = () => {
    try {
      sessionStorage.setItem(COOKIE_DISMISS_KEY, '1')
    } catch {
      /* ignore */
    }
    setDismissed(true)
  }

  return (
    <div className="cookie-notice" role="region" aria-label={t('legal.cookieNoticeAria')}>
      <p>{t('legal.cookieNoticeText')}</p>
      <div className="cookie-notice__actions">
        <Link to="/legal/privacy" className="cookie-notice__link">
          {t('legal.privacyLink')}
        </Link>
        <button type="button" className="cookie-notice__btn" onClick={dismiss}>
          {t('legal.dismiss')}
        </button>
      </div>
    </div>
  )
}

export default function LegalFooterLinks({ legal }: { legal: LegalPublicConfig | null }) {
  const { t } = useTranslation()

  if (!legal?.enabled || !legal.footer_links?.length) {
    return null
  }

  return (
    <>
      {legal.footer_links.map((link) => (
        <span key={link.slug} className="app-footer-minimal__legal-group">
          <span className="app-footer-minimal__sep" aria-hidden>
            ·
          </span>
          <Link to={`/legal/${link.slug}`}>
            {FOOTER_SLUG_KEYS[link.slug] ? t(FOOTER_SLUG_KEYS[link.slug]) : link.label}
          </Link>
        </span>
      ))}
    </>
  )
}
