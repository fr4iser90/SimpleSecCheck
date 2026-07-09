"""
Legal pages API — public content and admin configuration.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.deps.actor_context import get_admin_user, ActorContext
from domain.services.legal_content_service import (
    build_public_legal_response,
    legal_config_from_system_state,
    normalize_legal_config,
    upgrade_legal_terms_for_accounts,
    validate_legal_config,
)
from infrastructure.container import get_system_state_repository_dependency
from domain.repositories.system_state_repository import SystemStateRepository

router = APIRouter(prefix="/api", tags=["legal"])


class LegalConfigBody(BaseModel):
    enabled: Optional[bool] = None
    locale: Optional[str] = Field(default=None, description="de | en")
    cookie_notice_enabled: Optional[bool] = None
    company_name: Optional[str] = None
    legal_representative: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    vat_id: Optional[str] = None
    privacy_contact_email: Optional[str] = None
    impressum_custom: Optional[str] = None
    privacy_custom: Optional[str] = None
    terms_enabled: Optional[bool] = None
    terms_custom: Optional[str] = None
    hosting_provider: Optional[str] = None
    email_provider: Optional[str] = None


class LegalConfigResponse(BaseModel):
    config: Dict[str, Any]
    warnings: List[str] = Field(default_factory=list)
    public: Dict[str, Any] = Field(description="Rendered public legal payload")


@router.get("/legal", summary="Public legal pages content")
async def get_public_legal(
    system_state_repo: SystemStateRepository = Depends(get_system_state_repository_dependency),
) -> Dict[str, Any]:
    await upgrade_legal_terms_for_accounts(system_state_repo)
    state = await system_state_repo.get_singleton()
    state_config = state.config if state else None
    cfg = legal_config_from_system_state(state_config)
    return build_public_legal_response(cfg, state_config=state_config)


@router.get("/admin/config/legal", response_model=LegalConfigResponse)
async def get_admin_legal_config(
    actor_context: ActorContext = Depends(get_admin_user),
    system_state_repo: SystemStateRepository = Depends(get_system_state_repository_dependency),
) -> LegalConfigResponse:
    await upgrade_legal_terms_for_accounts(system_state_repo)
    state = await system_state_repo.get_singleton()
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System state not found")
    state_config = state.config
    cfg = legal_config_from_system_state(state_config)
    return LegalConfigResponse(
        config=cfg,
        warnings=validate_legal_config(cfg, state_config),
        public=build_public_legal_response(cfg, state_config=state_config),
    )


@router.put("/admin/config/legal", response_model=LegalConfigResponse)
async def update_admin_legal_config(
    body: LegalConfigBody,
    actor_context: ActorContext = Depends(get_admin_user),
    system_state_repo: SystemStateRepository = Depends(get_system_state_repository_dependency),
) -> LegalConfigResponse:
    state = await system_state_repo.get_singleton()
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System state not found")

    config = dict(state.config or {})
    legal_cfg = normalize_legal_config(config.get("legal"), config)
    updates = body.model_dump(exclude_unset=True)
    legal_cfg.update(updates)
    if legal_cfg.get("enabled") and config:
        legal_cfg = normalize_legal_config(legal_cfg, config)
    config["legal"] = legal_cfg
    state.config = config
    await system_state_repo.save(state)

    return LegalConfigResponse(
        config=legal_cfg,
        warnings=validate_legal_config(legal_cfg, config),
        public=build_public_legal_response(legal_cfg, state_config=config),
    )
