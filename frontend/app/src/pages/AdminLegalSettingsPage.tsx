import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import AdminPageShell from '../components/AdminPageShell'
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

function CheckboxField({
  name,
  checked,
  label,
  onChange,
}: {
  name: string
  checked: boolean
  label: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
}) {
  return (
    <div className="form-group">
      <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
        <input type="checkbox" name={name} checked={checked} onChange={onChange} />
        <span>{label}</span>
      </label>
    </div>
  )
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

  return (
    <AdminPageShell
      title={t('legal.adminTitle')}
      subtitle="Impressum, privacy policy, and terms for public instances."
      calloutTitle="Quick reference"
      callout={
        <dl className="page-kv-list">
          <div>
            <dt>Footer links</dt>
            <dd>Shown in the app shell when legal pages are enabled. Labels follow the UI language.</dd>
          </div>
          <div>
            <dt>Document language</dt>
            <dd>Legal page content uses the locale below — independent of the UI language.</dd>
          </div>
          <div>
            <dt>Cookie notice</dt>
            <dd>Essential session cookies only; text follows the user&apos;s UI language.</dd>
          </div>
        </dl>
      }
      error={error}
      success={success}
      loading={loading}
      loadingText={t('common.loading')}
    >
      <div className="admin-settings-container">
        {warnings.length > 0 && (
          <div className="form-info-box warning" style={{ marginBottom: '1.25rem' }}>
            <strong>{t('legal.adminWarnings')}</strong>
            <ul style={{ margin: '0.5rem 0 0', paddingLeft: '1.25rem' }}>
              {warnings.map((w) => (
                <li key={w}>{LEGAL_WARNING_KEYS[w] ? t(LEGAL_WARNING_KEYS[w]) : w}</li>
              ))}
            </ul>
          </div>
        )}

        <form onSubmit={handleSave} className="settings-form">
          <div className="settings-section">
            <h3>{t('legal.adminGeneralSection')}</h3>
            <CheckboxField
              name="enabled"
              checked={config.enabled}
              label={t('legal.adminEnable')}
              onChange={handleChange}
            />

            {config.enabled && (
              <>
                <div className="form-group">
                  <label htmlFor="legal-locale">{t('legal.adminLocale')}</label>
                  <select
                    id="legal-locale"
                    name="locale"
                    value={config.locale}
                    onChange={handleChange}
                  >
                    <option value="de">Deutsch (DE)</option>
                    <option value="en">English</option>
                  </select>
                </div>

                <CheckboxField
                  name="cookie_notice_enabled"
                  checked={config.cookie_notice_enabled}
                  label={t('legal.adminCookieNotice')}
                  onChange={handleChange}
                />

                <CheckboxField
                  name="terms_enabled"
                  checked={config.terms_enabled}
                  label={t('legal.adminTermsEnable')}
                  onChange={handleChange}
                />
              </>
            )}
          </div>

          {config.enabled && (
            <>
              <div className="settings-section">
                <h3>{t('legal.adminImpressumSection')}</h3>
                <p className="section-description">{t('legal.adminImpressumSectionDesc')}</p>

                <div className="form-group">
                  <label htmlFor="legal-company">{t('legal.adminCompanyName')}</label>
                  <input
                    id="legal-company"
                    name="company_name"
                    value={config.company_name}
                    onChange={handleChange}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="legal-representative">{t('legal.adminRepresentative')}</label>
                  <input
                    id="legal-representative"
                    name="legal_representative"
                    value={config.legal_representative}
                    onChange={handleChange}
                  />
                  <p className="form-hint">{t('legal.adminRepresentativeHint')}</p>
                </div>

                <div className="form-group">
                  <label htmlFor="legal-address">{t('legal.adminAddress')}</label>
                  <textarea
                    id="legal-address"
                    name="address"
                    value={config.address}
                    onChange={handleChange}
                    rows={4}
                    placeholder={t('legal.adminAddressPlaceholder')}
                  />
                  <p className="form-hint">{t('legal.adminAddressHint')}</p>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="legal-email">{t('legal.adminEmail')}</label>
                    <input
                      id="legal-email"
                      type="email"
                      name="email"
                      value={config.email}
                      onChange={handleChange}
                      placeholder={t('legal.adminEmailPlaceholder')}
                    />
                    <p className="form-hint">{t('legal.adminEmailHint')}</p>
                  </div>
                  <div className="form-group">
                    <label htmlFor="legal-phone">{t('legal.adminPhone')}</label>
                    <input
                      id="legal-phone"
                      name="phone"
                      value={config.phone}
                      onChange={handleChange}
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label htmlFor="legal-vat">{t('legal.adminVat')}</label>
                  <input
                    id="legal-vat"
                    name="vat_id"
                    value={config.vat_id}
                    onChange={handleChange}
                  />
                </div>
              </div>

              <div className="settings-section">
                <h3>{t('legal.adminPrivacySection')}</h3>
                <p className="section-description">{t('legal.adminPrivacySectionDesc')}</p>

                <div className="form-group">
                  <label htmlFor="legal-privacy-email">{t('legal.adminPrivacyEmail')}</label>
                  <input
                    id="legal-privacy-email"
                    type="email"
                    name="privacy_contact_email"
                    value={config.privacy_contact_email}
                    onChange={handleChange}
                    placeholder={config.email || 'privacy@…'}
                  />
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="legal-hosting">{t('legal.adminHosting')}</label>
                    <input
                      id="legal-hosting"
                      name="hosting_provider"
                      value={config.hosting_provider}
                      onChange={handleChange}
                      placeholder="Hetzner Online GmbH, …"
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="legal-email-provider">{t('legal.adminEmailProvider')}</label>
                    <input
                      id="legal-email-provider"
                      name="email_provider"
                      value={config.email_provider}
                      onChange={handleChange}
                      placeholder="SMTP / Resend"
                    />
                  </div>
                </div>
              </div>

              <div className="settings-section">
                <h3>{t('legal.adminAdvancedSection')}</h3>
                <p className="section-description">{t('legal.adminAdvancedSectionDesc')}</p>

                <div className="form-group">
                  <label htmlFor="legal-impressum-custom">{t('legal.adminImpressumCustom')}</label>
                  <textarea
                    id="legal-impressum-custom"
                    name="impressum_custom"
                    value={config.impressum_custom}
                    onChange={handleChange}
                    rows={4}
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="legal-privacy-custom">{t('legal.adminPrivacyCustom')}</label>
                  <textarea
                    id="legal-privacy-custom"
                    name="privacy_custom"
                    value={config.privacy_custom}
                    onChange={handleChange}
                    rows={6}
                  />
                </div>

                {config.terms_enabled && (
                  <div className="form-group">
                    <label htmlFor="legal-terms-custom">{t('legal.adminTermsCustom')}</label>
                    <textarea
                      id="legal-terms-custom"
                      name="terms_custom"
                      value={config.terms_custom}
                      onChange={handleChange}
                      rows={6}
                    />
                  </div>
                )}

                <p className="section-description">
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
              </div>
            </>
          )}

          <div className="form-actions">
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? t('legal.adminSaving') : t('legal.adminSave')}
            </button>
          </div>
        </form>
      </div>
    </AdminPageShell>
  )
}
