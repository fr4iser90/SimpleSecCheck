# Legal Considerations

SimpleSecCheck performs **active security scans**. You must have explicit authorization for every target.

## Website legal pages (DE/EU hosting)

When you operate a **publicly reachable** instance (especially in Germany/EU), you typically need:

- **Impressum** (§ 5 TMG) — operator contact details
- **Datenschutzerklärung** (GDPR Art. 13/14) — when processing personal data (login, sessions, logs)
- **Cookie notice** — for auth-only cookies (`refresh_token`, `session_id`) a short informational banner is usually sufficient; no marketing tracker consent required

SimpleSecCheck supports this **optionally**:

1. **Setup Wizard → Step 4 (Legal)** — auto-suggested for `public_web`, `network_intern`, `enterprise`
2. **Admin → Legal & Compliance** — edit Impressum/Datenschutz anytime
3. **Footer links** — `/legal/impressum`, `/legal/privacy`, `/legal/terms` (AGB) when enabled
4. **Sign-up** — checkbox for AGB + Datenschutz when legal pages are on and accounts exist

| Phase | Impressum | Datenschutz | AGB | AVV / Löschung |
|-------|-----------|-------------|-----|----------------|
| Lokal / privat | ❌ | ❌ | ❌ | ❌ |
| Öffentliche Demo (DE) | ✅ | ✅ | optional | ❌ |
| Echte Accounts + Login | ✅ | ✅ | ✅ (Registrierung) | Hosting/E-Mail in Admin |

Templates are starting points only — verify with your legal advisor. Boilerplate text lives in **`content/legal/{de,en}/*.md`** (Markdown with `{{placeholders}}` filled from Admin → Legal). Use custom Markdown fields in admin to override a page entirely.

For **solo/internal** deployments, leave legal pages disabled.

## Allowed Use (Examples)

- ✅ Systems you own or operate
- ✅ Authorized penetration tests with written consent
- ✅ Bug bounty targets **within** program scope

## Not Allowed

- ❌ Third-party systems without permission
- ❌ Public websites you do not own
- ❌ Private repositories without authorization

## Responsibility

You are responsible for:

- Ensuring a lawful basis for scanning
- Complying with local regulations (e.g., GDPR in the EU, CFAA in the US)
- Respecting terms of service for external platforms

**Disclaimer:** SimpleSecCheck is provided for authorized security testing only. The authors are not responsible for misuse.