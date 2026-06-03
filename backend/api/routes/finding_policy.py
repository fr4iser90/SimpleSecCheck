"""
Finding policy API — schema and validation for agents.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from api.deps.actor_context import get_authenticated_user, ActorContext
from domain.policies.finding_policy import DEFAULT_FINDING_POLICY_PATH
from domain.policies.finding_policy_schema import (
    get_finding_policy_schema,
    parse_tools_query,
)

router = APIRouter(
    prefix="/api/v1/finding-policy",
    tags=["finding-policy"],
    responses={
        401: {"description": "Unauthorized"},
    },
)


class FindingPolicySchemaResponse(BaseModel):
    """Finding policy JSON structure for automation agents."""

    schema_version: str = Field(description="Schema document version")
    default_path: str = Field(description="Default relative path in scanned repository")
    format: str = Field(description="File format (json)")
    rules: Dict[str, Any] = Field(description="Root validation rules")
    policy_key_aliases: Dict[str, str] = Field(
        default_factory=dict,
        description="Deprecated top-level keys mapped to canonical policy_key",
    )
    notes: list[str] = Field(description="Important behavioral notes")
    path_match_hints: Dict[str, str] = Field(
        default_factory=dict,
        description="Per-tool notes on what path_regex (or tool-specific keys) match",
    )
    tools: Dict[str, Any] = Field(
        description="policy_key -> block schema (matchers, accepted_findings, …)",
    )
    minimal_example: Dict[str, Any] = Field(description="Minimal valid policy fragment")


class FindingPolicyValidateRequest(BaseModel):
    """Validate a finding-policy.json object (e.g. before commit)."""

    policy: Dict[str, Any] = Field(description="Parsed policy root object")
    dry_run_findings: Optional[Dict[str, List[Dict[str, Any]]]] = Field(
        None,
        description="Optional map policy_key -> raw finding dicts for match dry-run",
    )


class FindingPolicyValidateResponse(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    dry_run: Dict[str, Any] = Field(default_factory=dict)
    known_policy_keys: List[str] = Field(default_factory=list)
    aliases: Dict[str, str] = Field(default_factory=dict)


@router.get(
    "/schema",
    response_model=FindingPolicySchemaResponse,
    summary="Get finding policy JSON schema",
    description=(
        "Return the finding-policy.json structure used by SimpleSecCheck scanners. "
        "Cache this response in agents; it does not depend on a scan_id. "
        "Optional query `tools` filters to comma-separated policy_key values "
        "(e.g. semgrep,gitleaks). Requires API key or user JWT."
    ),
)
async def get_finding_policy_schema_endpoint(
    tools: Optional[str] = Query(
        None,
        description="Comma-separated policy_key filter, e.g. semgrep,gitleaks",
    ),
    _actor: ActorContext = Depends(get_authenticated_user),
) -> FindingPolicySchemaResponse:
    tools_filter = parse_tools_query(tools)
    data = get_finding_policy_schema(tools_filter=tools_filter)
    return FindingPolicySchemaResponse(**data)


@router.post(
    "/validate",
    response_model=FindingPolicyValidateResponse,
    summary="Validate finding policy JSON",
    description=(
        "Validate policy structure, regex fields, and known policy_key values. "
        "Optional dry_run_findings tests whether rules would accept sample findings."
    ),
)
async def validate_finding_policy_endpoint(
    body: FindingPolicyValidateRequest,
    _actor: ActorContext = Depends(get_authenticated_user),
) -> FindingPolicyValidateResponse:
    try:
        from scanner.core.finding_policy_validate import validate_policy_data
    except ImportError as exc:
        raise RuntimeError("Scanner package required for policy validation") from exc

    result = validate_policy_data(
        body.policy,
        sample_findings=body.dry_run_findings,
    )
    return FindingPolicyValidateResponse(**result)
