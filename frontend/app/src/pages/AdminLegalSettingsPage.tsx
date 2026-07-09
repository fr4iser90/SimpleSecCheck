import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../utils/apiClient'
import { useTranslation } from '../i18n'

interface LegalConfig {
  enabled: boolean
  locale: string
  cookie_notice_enabled: boolean
  company_name: string
  legal_representative: string
  address: string
  email: string
  phone: string
  vat_id: string
  privacy_contact_email: string
  impressum_custom: string
  privacy_custom: string
  terms_enabled: boolean
  terms_custom: string
  hosting_provider: string
  email_provider: string
}

const LEGAL_WARNING_KEYS: Record<string, string> = {
  missing_company_name: 'legal.warnings.missing_company_name',
  missing_address: 'legal.warnings.missing_address',
  missing_email: 'legal.warnings.missing_email',
  terms_recommended: 'legal.warnings.terms_recommended',
}

const EMPTY: LegalConfig = {
  enabled: false,
  locale: 'de',
  cookie_notice_enabled: true,
  company_name: '',
  legal_representative: '',
  address: '',
  email: '',
  phone: '',
  vat_id: '',
  privacy_contact_email: '',
  impressum_custom: '',
  privacy_custom: '',
  terms_enabled: true,
  terms_custom: '',
  hosting_provider: '',
  email_provider: '',
}

export default function AdminLegalSettingsPage() {
  const { t } = useTranslation()
  const [config, setConfig] = useState<LegalConfig>(EMPTY)
  const [warnings, setWarnings] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    void loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await apiFetch('/api/admin/config/legal')
      if (!response.ok) throw new Error('Failed to load legal configuration')
      const data = await response.json()
      setConfig({ ...EMPTY, ...data.config })
      setWarnings(data.warnings || [])
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value, type } = e.target
    const checked = (e.target as HTMLInputElement).checked
    setConfig((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }))
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      const response = await apiFetch('/api/admin/config/legal', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })
      if (!response.ok) {
        const err = await response.json().catch(() => ({}))
        throw new Error(err.detail || 'Failed to save')
      }
      const data = await response.json()
      setConfig({ ...EMPTY, ...data.config })
      setWarnings(data.warnings || [])
      setSuccess(t('legal.adminSaved'))
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="admin-settings-page">
        <h1>{t('legal.adminTitle')}</h1>
        <p>{t('common.loading')}</p>
      </div>
    )
  }

  return (
    <div className="admin-settings-page">
      <h1>{t('legal.adminTitle')}</h1>
      <p className="admin-settings-page__intro">{t('legal.adminIntro')}</p>

      {error && <div className="form-info-box error">{error}</div>}
      {success && <div className="form-info-box success">{success}</div>}
      {warnings.length > 0 && (
        <div className="form-info-box error">
          <strong>{t('legal.adminWarnings')}</strong>
          <ul>
            {warnings.map((w) => (
              <li key={w}>{LEGAL_WARNING_KEYS[w] ? t(LEGAL_WARNING_KEYS[w]) : w}</li>
            ))}
          </ul>
        </div>
      )}

      <form onSubmit={handleSave} className="admin-settings-form">
        <div className="form-group">
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input type="checkbox" name="enabled" checked={config.enabled} onChange={handleChange} />
            {t('legal.adminEnable')}
          </label>
        </div>

        {config.enabled && (
          <>
            <div className="form-group">
              <label>{t('legal.adminLocale')}</label>
              <select name="locale" value={config.locale} onChange={handleChange}>
                <option value="de">Deutsch (DE)</option>
                <option value="en">English</option>
              </select>
            </div>

            <div className="form-group">
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input
                  type="checkbox"
                  name="cookie_notice_enabled"
                  checked={config.cookie_notice_enabled}
                  onChange={handleChange}
                />
                {t('legal.adminCookieNotice')}
              </label>
            </div>

            <div className="form-group">
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input
                  type="checkbox"
                  name="terms_enabled"
                  checked={config.terms_enabled}
                  onChange={handleChange}
                />
                {t('legal.adminTermsEnable')}
              </label>
            </div>

            <h3>{t('legal.adminImpressumSection')}</h3>
            <div className="form-group">
              <label>{t('legal.adminCompanyName')}</label>
              <input name="company_name" value={config.company_name} onChange={handleChange} />
            </div>
            <div className="form-group">
              <label>{t('legal.adminRepresentative')}</label>
              <input
                name="legal_representative"
                value={config.legal_representative}
                onChange={handleChange}
              />
            </div>
            <div className="form-group">
              <label>{t('legal.adminAddress')}</label>
              <textarea name="address" value={config.address} onChange={handleChange} rows={3} />
            </div>
            <div className="form-group">
              <label>{t('legal.adminEmail')}</label>
              <input type="email" name="email" value={config.email} onChange={handleChange} />
            </div>
            <div className="form-group">
              <label>{t('legal.adminPhone')}</label>
              <input name="phone" value={config.phone} onChange={handleChange} />
            </div>
            <div className="form-group">
              <label>{t('legal.adminVat')}</label>
              <input name="vat_id" value={config.vat_id} onChange={handleChange} />
            </div>

            <h3>{t('legal.adminPrivacySection')}</h3>
            <div className="form-group">
              <label>{t('legal.adminPrivacyEmail')}</label>
              <input
                type="email"
                name="privacy_contact_email"
                value={config.privacy_contact_email}
                onChange={handleChange}
                placeholder={config.email || 'privacy@…'}
              />
            </div>
            <div className="form-group">
              <label>{t('legal.adminHosting')}</label>
              <input
                name="hosting_provider"
                value={config.hosting_provider}
                onChange={handleChange}
              />
            </div>
            <div className="form-group">
              <label>{t('legal.adminEmailProvider')}</label>
              <input
                name="email_provider"
                value={config.email_provider}
                onChange={handleChange}
              />
            </div>

            <div className="form-group">
              <label>{t('legal.adminImpressumCustom')}</label>
              <textarea
                name="impressum_custom"
                value={config.impressum_custom}
                onChange={handleChange}
                rows={4}
              />
            </div>
            <div className="form-group">
              <label>{t('legal.adminPrivacyCustom')}</label>
              <textarea
                name="privacy_custom"
                value={config.privacy_custom}
                onChange={handleChange}
                rows={6}
              />
            </div>

            {config.terms_enabled && (
              <div className="form-group">
                <label>{t('legal.adminTermsCustom')}</label>
                <textarea name="terms_custom" value={config.terms_custom} onChange={handleChange} rows={6} />
              </div>
            )}

            <p className="form-help-text info">
              {t('legal.adminPreview')}{' '}
              <Link to="/legal/impressum" target="_blank" rel="noreferrer">
                {t('legal.footer.impressum')}
              </Link>
              {' · '}
              <Link to="/legal/privacy" target="_blank" rel="noreferrer">
                {t('legal.footer.privacy')}
              </Link>
              {config.terms_enabled && (
                <>
                  {' · '}
                  <Link to="/legal/terms" target="_blank" rel="noreferrer">
                    {t('legal.footer.terms')}
                  </Link>
                </>
              )}
            </p>
          </>
        )}

        <button type="submit" className="primary" disabled={saving}>
          {saving ? t('legal.adminSaving') : t('legal.adminSave')}
        </button>
      </form>
    </div>
  )
}
