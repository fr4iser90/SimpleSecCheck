"""
Legal content service — config, validation, and template rendering from content/legal/*.md.

Operator data lives in system_state.config.legal. Boilerplate text lives in
content/legal/{de,en}/*.md with {{placeholders}}. Custom admin markdown overrides templates.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
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

PAGE_TITLES: Dict[str, Dict[str, str]] = {
    "de": {
        "impressum": "Impressum",
        "privacy": "Datenschutzerklärung",
        "terms": "Nutzungsbedingungen",
    },
    "en": {
        "impressum": "Legal Notice",
        "privacy": "Privacy Policy",
        "terms": "Terms of Service",
    },
}

COOKIE_NOTICE_TEXT: Dict[str, str] = {
    "de": (
        "Diese Website verwendet technisch notwendige Cookies für Anmeldung und "
        "Sitzungsverwaltung. Details in der Datenschutzerklärung."
    ),
    "en": (
        "This site uses essential cookies for login and session management. "
        "See the privacy policy."
    ),
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


def legal_locale_folder(locale: str) -> str:
    """Map config locale to content/legal subfolder (de | en)."""
    return "de" if (locale or "de").lower().startswith("de") else "en"


def legal_templates_root() -> Path:
    """Resolve content/legal directory (Docker image, compose mount, or repo checkout)."""
    env_dir = os.environ.get("LEGAL_CONTENT_DIR", "").strip()
    candidates = [
        Path(env_dir) if env_dir else None,
        Path("/app/content/legal"),
        Path("/project/content/legal"),
        Path(__file__).resolve().parents[3] / "content" / "legal",
    ]
    for path in candidates:
        if path is not None and path.is_dir():
            return path
    raise FileNotFoundError(
        "Legal templates directory not found. Expected content/legal in the repo or LEGAL_CONTENT_DIR."
    )


@lru_cache(maxsize=32)
def _load_template_file(locale_folder: str, page: str) -> str:
    path = legal_templates_root() / locale_folder / f"{page}.md"
    if not path.is_file():
        raise FileNotFoundError(f"Missing legal template: {path}")
    return path.read_text(encoding="utf-8")


def load_legal_template(locale: str, page: str) -> str:
    """Load raw markdown template for a legal page."""
    return _load_template_file(legal_locale_folder(locale), page)


def substitute_template(template: str, variables: Dict[str, str]) -> str:
    """Replace {{key}} placeholders in a template."""
    result = template
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", value)
    return result.strip()


def _contact_block(cfg: Dict[str, Any], locale: str = "de") -> str:
    lines = []
    if cfg.get("company_name"):
        lines.append(str(cfg["company_name"]))
    if cfg.get("legal_representative"):
        if locale.startswith("de"):
            lines.append(f"Vertreten durch: {cfg['legal_representative']}")
        else:
            lines.append(f"Represented by: {cfg['legal_representative']}")
    if cfg.get("address"):
        lines.append(str(cfg["address"]).replace("\n", ", "))
    if cfg.get("email"):
        lines.append(
            f"E-Mail: {cfg['email']}" if locale.startswith("de") else f"Email: {cfg['email']}"
        )
    if cfg.get("phone"):
        lines.append(
            f"Telefon: {cfg['phone']}" if locale.startswith("de") else f"Phone: {cfg['phone']}"
        )
    if cfg.get("vat_id"):
        lines.append(
            f"USt-IdNr.: {cfg['vat_id']}" if locale.startswith("de") else f"VAT ID: {cfg['vat_id']}"
        )
    if not lines:
        return (
            "_Bitte Impressumsdaten in den Admin-Einstellungen ergänzen._"
            if locale.startswith("de")
            else "_Please complete legal notice details in Admin → Legal & Compliance._"
        )
    return "\n\n".join(lines)


def template_variables(cfg: Dict[str, Any], locale: str, app_name: str) -> Dict[str, str]:
    """Build placeholder map for content/legal templates."""
    folder = legal_locale_folder(locale)
    contact_email = cfg.get("privacy_contact_email") or cfg.get("email") or "privacy@example.com"
    operator = cfg.get("company_name") or (
        "Betreiber dieser Instanz" if folder == "de" else "Operator of this instance"
    )
    hosting = cfg.get("hosting_provider") or (
        "vom Betreiber (siehe Impressum)" if folder == "de" else "the operator (see legal notice)"
    )
    email_provider = cfg.get("email_provider") or (
        "vom Betreiber konfigurierter SMTP-Dienst"
        if folder == "de"
        else "SMTP service configured by the operator"
    )
    contact = cfg.get("email") or ("kontakt@example.de" if folder == "de" else "contact@example.com")
    responsible = cfg.get("legal_representative") or cfg.get("company_name") or "—"

    return {
        "company_name": str(cfg.get("company_name") or ""),
        "legal_representative": str(cfg.get("legal_representative") or ""),
        "address": str(cfg.get("address") or ""),
        "email": str(cfg.get("email") or ""),
        "phone": str(cfg.get("phone") or ""),
        "vat_id": str(cfg.get("vat_id") or ""),
        "contact_block": _contact_block(cfg, folder),
        "responsible": str(responsible),
        "operator": str(operator),
        "privacy_contact": str(contact_email),
        "hosting": str(hosting),
        "email_provider": str(email_provider),
        "contact": str(contact),
        "app_name": app_name,
    }


def render_legal_page(
    page: str,
    cfg: Dict[str, Any],
    locale: str,
    app_name: str = "SimpleSecCheck",
) -> str:
    """Render one legal page from custom markdown or content/legal template."""
    custom_key = {
        "impressum": "impressum_custom",
        "privacy": "privacy_custom",
        "terms": "terms_custom",
    }.get(page)
    if custom_key and str(cfg.get(custom_key, "")).strip():
        return str(cfg[custom_key]).strip()

    template = load_legal_template(locale, page)
    return substitute_template(template, template_variables(cfg, locale, app_name))


def render_impressum_de(cfg: Dict[str, Any], app_name: str = "SimpleSecCheck") -> str:
    return render_legal_page("impressum", cfg, "de", app_name)


def render_impressum_en(cfg: Dict[str, Any], app_name: str = "SimpleSecCheck") -> str:
    return render_legal_page("impressum", cfg, "en", app_name)


def render_privacy_de(cfg: Dict[str, Any], app_name: str = "SimpleSecCheck") -> str:
    return render_legal_page("privacy", cfg, "de", app_name)


def render_privacy_en(cfg: Dict[str, Any], app_name: str = "SimpleSecCheck") -> str:
    return render_legal_page("privacy", cfg, "en", app_name)


def render_terms_de(cfg: Dict[str, Any], app_name: str = "SimpleSecCheck") -> str:
    return render_legal_page("terms", cfg, "de", app_name)


def render_terms_en(cfg: Dict[str, Any], app_name: str = "SimpleSecCheck") -> str:
    return render_legal_page("terms", cfg, "en", app_name)


def build_legal_pages(cfg: Dict[str, Any], app_name: str = "SimpleSecCheck") -> Dict[str, Any]:
    """Build public legal page payloads."""
    folder = legal_locale_folder(cfg.get("locale") or "de")
    titles = PAGE_TITLES[folder]
    pages: Dict[str, Any] = {
        "impressum": {
            "title": titles["impressum"],
            "content": render_legal_page("impressum", cfg, cfg.get("locale") or "de", app_name),
        },
        "privacy": {
            "title": titles["privacy"],
            "content": render_legal_page("privacy", cfg, cfg.get("locale") or "de", app_name),
        },
    }
    if cfg.get("terms_enabled"):
        pages["terms"] = {
            "title": titles["terms"],
            "content": render_legal_page("terms", cfg, cfg.get("locale") or "de", app_name),
        }
    return pages


def build_footer_links(cfg: Dict[str, Any]) -> List[Dict[str, str]]:
    if not cfg.get("enabled"):
        return []
    folder = legal_locale_folder(cfg.get("locale") or "de")
    titles = PAGE_TITLES[folder]
    links = [
        {"slug": "impressum", "label": titles["impressum"]},
        {"slug": "privacy", "label": titles["privacy"]},
    ]
    if cfg.get("terms_enabled"):
        links.append({"slug": "terms", "label": titles["terms"]})
    return links


def build_public_legal_response(
    cfg: Dict[str, Any],
    app_name: str = "SimpleSecCheck",
    state_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    cfg = normalize_legal_config(cfg, state_config)
    enabled = bool(cfg.get("enabled"))
    terms_on = bool(cfg.get("terms_enabled")) and enabled
    folder = legal_locale_folder(cfg.get("locale") or "de")
    return {
        "enabled": enabled,
        "locale": cfg.get("locale", "de"),
        "terms_enabled": terms_on,
        "require_terms_acceptance": terms_on,
        "cookie_notice_enabled": bool(cfg.get("cookie_notice_enabled")) and enabled,
        "cookie_notice_text": COOKIE_NOTICE_TEXT[folder],
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
