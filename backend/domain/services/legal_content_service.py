"""
Legal content service — generates Impressum and privacy policy text from configuration.

Templates are informational defaults for DE/EU self-hosted deployments. Operators remain
responsible for legal accuracy; custom markdown overrides take precedence.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


DEFAULT_LEGAL_CONFIG: Dict[str, Any] = {
    "enabled": False,
    "locale": "de",
    "cookie_notice_enabled": True,
    "company_name": "",
    "legal_representative": "",
    "address": "",
    "email": "",
    "phone": "",
    "vat_id": "",
    "privacy_contact_email": "",
    "impressum_custom": "",
    "privacy_custom": "",
    "terms_enabled": True,
    "terms_custom": "",
    "hosting_provider": "",
    "email_provider": "",
}


def deployment_has_user_accounts(state_config: Optional[Dict[str, Any]]) -> bool:
    """True when this instance is expected to have registered/logged-in users."""
    if not state_config:
        return False
    use_case = state_config.get("use_case") or ""
    if use_case in ("network_intern", "public_web", "enterprise"):
        return True
    auth_cfg = state_config.get("auth") or {}
    if auth_cfg.get("allow_self_registration"):
        return True
    auth_mode = state_config.get("AUTH_MODE") or state_config.get("auth_mode") or "free"
    return auth_mode in ("basic", "jwt")


def normalize_legal_config(
    raw: Optional[Dict[str, Any]],
    state_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Merge stored config with defaults."""
    cfg = dict(DEFAULT_LEGAL_CONFIG)
    if isinstance(raw, dict):
        cfg.update({k: v for k, v in raw.items() if k in DEFAULT_LEGAL_CONFIG})
    if not cfg.get("privacy_contact_email") and cfg.get("email"):
        cfg["privacy_contact_email"] = cfg["email"]
    if cfg.get("enabled") and deployment_has_user_accounts(state_config):
        cfg["terms_enabled"] = True
    return cfg


def legal_config_from_system_state(state_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not state_config:
        return normalize_legal_config(None)
    return normalize_legal_config(state_config.get("legal"), state_config)


async def upgrade_legal_terms_for_accounts(system_state_repo) -> None:
    """Persist terms_enabled when legal is on and the deployment has user accounts."""
    from domain.repositories.system_state_repository import SystemStateRepository

    if not isinstance(system_state_repo, SystemStateRepository):
        return
    state = await system_state_repo.get_singleton()
    if not state or not state.config:
        return
    config = dict(state.config)
    legal_raw = config.get("legal") or {}
    if not isinstance(legal_raw, dict) or not legal_raw.get("enabled"):
        return
    if not deployment_has_user_accounts(config):
        return
    if legal_raw.get("terms_enabled") is True:
        return
    legal_raw = dict(legal_raw)
    legal_raw["terms_enabled"] = True
    config["legal"] = legal_raw
    state.config = config
    await system_state_repo.save(state)


def _contact_block(cfg: Dict[str, Any], locale: str = "de") -> str:
    lines = []
    if cfg.get("company_name"):
        lines.append(cfg["company_name"])
    if cfg.get("legal_representative"):
        if locale.startswith("de"):
            lines.append(f"Vertreten durch: {cfg['legal_representative']}")
        else:
            lines.append(f"Represented by: {cfg['legal_representative']}")
    if cfg.get("address"):
        lines.append(cfg["address"].replace("\n", ", "))
    if cfg.get("email"):
        lines.append(f"E-Mail: {cfg['email']}" if locale.startswith("de") else f"Email: {cfg['email']}")
    if cfg.get("phone"):
        lines.append(f"Telefon: {cfg['phone']}" if locale.startswith("de") else f"Phone: {cfg['phone']}")
    if cfg.get("vat_id"):
        lines.append(f"USt-IdNr.: {cfg['vat_id']}" if locale.startswith("de") else f"VAT ID: {cfg['vat_id']}")
    if not lines:
        return (
            "_Bitte Impressumsdaten in den Admin-Einstellungen ergänzen._"
            if locale.startswith("de")
            else "_Please complete legal notice details in Admin → Legal & Compliance._"
        )
    return "\n\n".join(lines)


def render_impressum_de(cfg: Dict[str, Any]) -> str:
    if cfg.get("impressum_custom", "").strip():
        return cfg["impressum_custom"].strip()

    contact = _contact_block(cfg, "de")
    responsible = cfg.get("legal_representative") or cfg.get("company_name") or "—"
    return f"""## Impressum

Angaben gemäß § 5 TMG

{contact}

### Verantwortlich für den Inhalt nach § 55 Abs. 2 RStV

{responsible}

---

_Diese Vorlage dient als Ausgangspunkt. Prüfe die Angaben mit deinem Rechtsberater._
"""


def render_privacy_de(cfg: Dict[str, Any], app_name: str = "SimpleSecCheck") -> str:
    if cfg.get("privacy_custom", "").strip():
        return cfg["privacy_custom"].strip()

    contact_email = cfg.get("privacy_contact_email") or cfg.get("email") or "privacy@example.com"
    operator = cfg.get("company_name") or "Betreiber dieser Instanz"
    hosting = cfg.get("hosting_provider") or "vom Betreiber (siehe Impressum)"
    email_provider = cfg.get("email_provider") or "vom Betreiber konfigurierter SMTP-Dienst"

    return f"""## Datenschutzerklärung

### 1. Verantwortlicher

{operator}

Kontakt Datenschutz: {contact_email}

### 2. Welche Daten wir verarbeiten

Bei Nutzung von {app_name} können folgende personenbezogene Daten verarbeitet werden:

- **Kontodaten** (E-Mail, Benutzername, Passwort-Hash) bei Registrierung/Login
- **Sitzungsdaten** (technisch notwendige Cookies: `refresh_token`, `session_id`)
- **Scan-Metadaten** (Ziele, Ergebnisse, die du einreichst)
- **Server-Logs** (IP-Adresse, Zeitstempel, User-Agent) zur Sicherheit und Fehleranalyse

### 3. Cookies

Wir setzen **technisch notwendige Cookies** für Anmeldung und Gast-Sitzungen ein.
Diese Cookies sind für den Betrieb erforderlich und benötigen nach gängiger Auslegung
keine separate Einwilligung. Es werden keine Marketing- oder Tracking-Cookies eingesetzt.

### 4. Registrierung & Vertragsschluss

Bei Registrierung stimmst du den **Nutzungsbedingungen** zu. Die Verarbeitung deiner
Kontodaten erfolgt zur Bereitstellung des Accounts (Art. 6 Abs. 1 lit. b DSGVO).

### 5. Speicherdauer & Löschung

- **Kontodaten:** bis zur Löschung deines Accounts oder auf Anfrage
- **Server-Logs:** in der Regel 7–30 Tage (Sicherheit/Fehleranalyse)
- **Scan-Ergebnisse:** solange du sie aufbewahrst bzw. bis du sie löschst

Du kannst jederzeit die **Löschung deines Accounts** verlangen ({contact_email}).

### 6. Auftragsverarbeiter (AVV)

Sofern externe Dienstleister eingesetzt werden, werden diese nur im Rahmen von
Auftragsverarbeitungsverträgen (Art. 28 DSGVO) genutzt, z. B.:

- **Hosting:** {hosting}
- **E-Mail-Versand:** {email_provider}

Details zu Subprozessoren kannst du beim Verantwortlichen anfragen.

### 7. Rechtsgrundlagen (DSGVO)

- Art. 6 Abs. 1 lit. b DSGVO — Vertrag/Nutzungsverhältnis (Login, Scans)
- Art. 6 Abs. 1 lit. f DSGVO — berechtigtes Interesse (Sicherheit, Logs)

### 8. Deine Rechte

Du hast das Recht auf Auskunft, Berichtigung, Löschung, Einschränkung, Datenübertragbarkeit
und Widerspruch. Beschwerden kannst du bei einer Datenschutz-Aufsichtsbehörde einreichen.

### 9. Hosting

Diese Instanz wird vom Betreiber selbst gehostet. Details im Impressum.

---

_Vorlage — passe den Text an deinen konkreten Betrieb an (z. B. SMTP-Anbieter, Analytics)._
"""


def render_terms_de(cfg: Dict[str, Any], app_name: str = "SimpleSecCheck") -> str:
    if cfg.get("terms_custom", "").strip():
        return cfg["terms_custom"].strip()
    operator = cfg.get("company_name") or "Betreiber"
    contact = cfg.get("email") or "kontakt@example.de"
    return f"""## Nutzungsbedingungen (AGB)

Stand: bei Veröffentlichung auf dieser Instanz

### 1. Geltungsbereich

Diese Nutzungsbedingungen gelten für die Nutzung von **{app_name}**, betrieben durch
**{operator}**. Mit Registrierung oder Login akzeptierst du diese Bedingungen.

### 2. Leistungsbeschreibung

{app_name} ist eine Security-Scanning-Plattform. Der Betreiber stellt die Software
„wie besehen“ zur Verfügung und kann Funktionen, Limits oder Verfügbarkeit anpassen.

### 3. Registrierung & Account

- Du musst wahrheitsgemäße Angaben machen und deine Zugangsdaten geheim halten.
- Du bist für alle Aktivitäten unter deinem Account verantwortlich.
- Der Betreiber kann Accounts bei Missbrauch sperren oder löschen.

### 4. Erlaubte Nutzung (Scanning)

Du darfst **ausschließlich Systeme scannen, die dir gehören oder für die du
ausdrückliche schriftliche Erlaubnis hast** (eigene Infrastruktur, autorisierte
Pentests, Bug-Bounty innerhalb des Programms).

**Untersagt** sind insbesondere:
- Scans ohne Einwilligung des Betreibers des Zielsystems
- Denial-of-Service, Datenzerstörung oder andere rechtswidrige Eingriffe
- Umgehung von Rate-Limits, Sperren oder Sicherheitsmechanismen

### 5. Pflichten des Nutzers

- Einhaltung geltender Gesetze (u. a. StGB, DSGVO, CFAA-Äquivalente im Ausland)
- Keine Weitergabe von Scan-Ergebnissen, die personenbezogene Daten Dritter enthalten,
  ohne Rechtsgrundlage
- Meldung erkannter Sicherheitslücken in der Plattform an {contact}

### 6. Haftung

Der Betreiber haftet unbeschränkt nur bei Vorsatz und grober Fahrlässigkeit.
Für leichte Fahrlässigkeit haftet der Betreiber nur bei Verletzung wesentlicher
Vertragspflichten, begrenzt auf vorhersehbare Schäden. Scan-Ergebnisse sind
Hilfsmittel — du bleibst für die Bewertung und Nutzung verantwortlich.

### 7. Verfügbarkeit & Änderungen

Es gibt keinen Anspruch auf ununterbrochene Verfügbarkeit. Der Betreiber kann
diese Bedingungen anpassen; wesentliche Änderungen werden auf der Website bekannt gegeben.

### 8. Kündigung & Löschung

Du kannst deinen Account jederzeit löschen lassen ({contact}).
Der Betreiber kann das Nutzungsverhältnis bei schwerwiegendem Verstoß fristlos beenden.

### 9. Datenschutz

Es gilt die Datenschutzerklärung auf dieser Website (`/legal/privacy`).

### 10. Schlussbestimmungen

Es gilt deutsches Recht. Gerichtsstand ist — soweit zulässig — der Sitz des Betreibers.

---

_Vorlage — für produktiven Betrieb mit echten Nutzern rechtlich prüfen lassen._
"""


def render_impressum_en(cfg: Dict[str, Any]) -> str:
    if cfg.get("impressum_custom", "").strip():
        return cfg["impressum_custom"].strip()

    contact = _contact_block(cfg, "en")
    responsible = cfg.get("legal_representative") or cfg.get("company_name") or "—"
    return f"""## Legal Notice

Information pursuant to applicable provider identification laws (e.g. TMG in Germany).

{contact}

### Responsible for content

{responsible}

---

_Template only — verify with qualified legal counsel for your jurisdiction._
"""


def render_privacy_en(cfg: Dict[str, Any], app_name: str = "SimpleSecCheck") -> str:
    if cfg.get("privacy_custom", "").strip():
        return cfg["privacy_custom"].strip()

    contact_email = cfg.get("privacy_contact_email") or cfg.get("email") or "privacy@example.com"
    operator = cfg.get("company_name") or "Operator of this instance"
    hosting = cfg.get("hosting_provider") or "the operator (see legal notice)"
    email_provider = cfg.get("email_provider") or "SMTP service configured by the operator"

    return f"""## Privacy Policy

### 1. Controller

{operator}

Privacy contact: {contact_email}

### 2. Data we process

When using {app_name}, we may process:

- **Account data** (email, username, password hash) when you register or sign in
- **Session data** (essential cookies: `refresh_token`, `session_id`)
- **Scan metadata** (targets and results you submit)
- **Server logs** (IP address, timestamps, user agent) for security and troubleshooting

### 3. Cookies

We use **strictly necessary cookies** for login and guest sessions. We do not use
marketing or analytics cookies. Essential cookies are required for the service to function.

### 4. Registration & contract

By registering you accept the **terms of service**. Account data is processed to
provide the service (GDPR Art. 6(1)(b) where applicable).

### 5. Retention & deletion

- **Account data:** until you delete your account or request deletion
- **Server logs:** typically 7–30 days (security / operations)
- **Scan results:** as long as you keep them or until you delete them

You may request **account deletion** at any time: {contact_email}

### 6. Processors (sub-processors)

External providers, if any, are used under data processing agreements (GDPR Art. 28), e.g.:

- **Hosting:** {hosting}
- **Email delivery:** {email_provider}

Contact the controller for an up-to-date list of sub-processors.

### 7. Legal bases (GDPR)

- Art. 6(1)(b) — performance of contract (login, scans)
- Art. 6(1)(f) — legitimate interests (security, logs)

### 8. Your rights

You may have rights of access, rectification, erasure, restriction, portability, and
objection. You may lodge a complaint with a supervisory authority.

### 9. Hosting

This instance is operated by the provider named in the legal notice.

---

_Template — adapt to your hosting, email provider, and jurisdiction._
"""


def render_terms_en(cfg: Dict[str, Any], app_name: str = "SimpleSecCheck") -> str:
    if cfg.get("terms_custom", "").strip():
        return cfg["terms_custom"].strip()
    operator = cfg.get("company_name") or "Operator"
    contact = cfg.get("email") or "contact@example.com"
    return f"""## Terms of Service

Effective when published on this instance.

### 1. Scope

These terms govern use of **{app_name}**, operated by **{operator}**.
By registering or signing in you accept these terms.

### 2. Service description

{app_name} is a security scanning platform. The service is provided **as is**;
features, limits, and availability may change.

### 3. Registration & accounts

- You must provide accurate information and keep credentials confidential.
- You are responsible for activity under your account.
- The operator may suspend or delete accounts for abuse.

### 4. Permitted use (scanning)

You may **only scan systems you own or have explicit written authorization to test**
(own infrastructure, authorized pentests, in-scope bug bounty programs).

**Prohibited** includes:
- Scanning without the target owner's consent
- Denial-of-service, data destruction, or other unlawful interference
- Bypassing rate limits, blocks, or security controls

### 5. User obligations

- Comply with applicable laws
- Do not share scan results containing third-party personal data without legal basis
- Report platform security issues to {contact}

### 6. Liability

To the extent permitted by law, liability is limited for negligence; scan results are
aids only — you remain responsible for evaluation and use.

### 7. Availability & changes

No guarantee of uninterrupted availability. Material changes to these terms will be
announced on this site.

### 8. Termination & deletion

You may request account deletion at any time ({contact}).
The operator may terminate for serious breach.

### 9. Privacy

The privacy policy at `/legal/privacy` applies.

### 10. Governing law

Applicable law is that of the operator's jurisdiction unless mandatory consumer
protections require otherwise.

---

_Template — have terms reviewed before production use with real users._
"""


def build_legal_pages(cfg: Dict[str, Any], app_name: str = "SimpleSecCheck") -> Dict[str, Any]:
    """Build public legal page payloads."""
    locale = (cfg.get("locale") or "de").lower()
    pages: Dict[str, Any] = {}

    if locale.startswith("de"):
        pages["impressum"] = {"title": "Impressum", "content": render_impressum_de(cfg)}
        pages["privacy"] = {"title": "Datenschutzerklärung", "content": render_privacy_de(cfg, app_name)}
        if cfg.get("terms_enabled"):
            pages["terms"] = {"title": "Nutzungsbedingungen", "content": render_terms_de(cfg, app_name)}
    else:
        pages["impressum"] = {"title": "Legal Notice", "content": render_impressum_en(cfg)}
        pages["privacy"] = {"title": "Privacy Policy", "content": render_privacy_en(cfg, app_name)}
        if cfg.get("terms_enabled"):
            pages["terms"] = {"title": "Terms of Service", "content": render_terms_en(cfg, app_name)}

    return pages


def build_footer_links(cfg: Dict[str, Any]) -> List[Dict[str, str]]:
    if not cfg.get("enabled"):
        return []
    locale = (cfg.get("locale") or "de").lower()
    links = [
        {"slug": "impressum", "label": "Impressum" if locale.startswith("de") else "Legal Notice"},
        {"slug": "privacy", "label": "Datenschutz" if locale.startswith("de") else "Privacy"},
    ]
    if cfg.get("terms_enabled"):
        links.append({
            "slug": "terms",
            "label": "Nutzungsbedingungen" if locale.startswith("de") else "Terms",
        })
    return links


def build_public_legal_response(
    cfg: Dict[str, Any],
    app_name: str = "SimpleSecCheck",
    state_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    cfg = normalize_legal_config(cfg, state_config)
    enabled = bool(cfg.get("enabled"))
    terms_on = bool(cfg.get("terms_enabled")) and enabled
    return {
        "enabled": enabled,
        "locale": cfg.get("locale", "de"),
        "terms_enabled": terms_on,
        "require_terms_acceptance": terms_on,
        "cookie_notice_enabled": bool(cfg.get("cookie_notice_enabled")) and enabled,
        "cookie_notice_text": (
            "Diese Website verwendet technisch notwendige Cookies für Anmeldung und "
            "Sitzungsverwaltung. Details in der Datenschutzerklärung."
            if (cfg.get("locale") or "de").startswith("de")
            else "This site uses essential cookies for login and session management. See the privacy policy."
        ),
        "pages": build_legal_pages(cfg, app_name) if enabled else {},
        "footer_links": build_footer_links(cfg),
    }


def validate_legal_config(
    cfg: Dict[str, Any],
    state_config: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Return validation warning codes (translate in frontend via legal.warnings.*)."""
    warnings: List[str] = []
    if not cfg.get("enabled"):
        return warnings
    if not cfg.get("company_name"):
        warnings.append("missing_company_name")
    if not cfg.get("address"):
        warnings.append("missing_address")
    if not cfg.get("email"):
        warnings.append("missing_email")
    if deployment_has_user_accounts(state_config) and not cfg.get("terms_enabled"):
        warnings.append("terms_recommended")
    return warnings
