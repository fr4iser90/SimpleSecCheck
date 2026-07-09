# Legal page templates

Markdown templates for Impressum, privacy policy, and terms of service.

- **Locale folders:** `de/`, `en/` — one file per page (`impressum.md`, `privacy.md`, `terms.md`).
- **Placeholders:** `{{company_name}}`, `{{contact_block}}`, `{{operator}}`, etc. are filled from Admin → Legal & Compliance (`system_state.config.legal`).
- **Overrides:** Custom Markdown in admin (`impressum_custom`, `privacy_custom`, `terms_custom`) replaces the template entirely.
- **Loader:** `backend/domain/services/legal_content_service.py` reads these files at runtime.

Edit the `.md` files here — not Python strings — when updating boilerplate legal text.
