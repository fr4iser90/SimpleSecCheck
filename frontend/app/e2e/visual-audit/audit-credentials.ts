/** Fixed credentials used by the visual-audit setup wizard (not production secrets). */
export const AUDIT_ADMIN_EMAIL = 'admin@example.com'
export const AUDIT_ADMIN_PASSWORD = 'VisualAudit123!'
export const AUDIT_ADMIN_USERNAME = 'admin'

export const AUDIT_LEGAL = {
  enabled: true,
  locale: 'de',
  cookie_notice_enabled: true,
  terms_enabled: true,
  company_name: 'SimpleSecCheck Demo GmbH',
  legal_representative: 'Max Mustermann',
  address: 'Musterstraße 1\n10115 Berlin\nDeutschland',
  email: 'legal@simpleseccheck.example',
  phone: '+49 30 1234567',
  vat_id: 'DE123456789',
  privacy_contact_email: 'privacy@simpleseccheck.example',
} as const
