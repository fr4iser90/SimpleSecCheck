"""
GET /api/v1/finding-policy/schema — machine-readable finding policy JSON schema.
"""
from typing import Any, Dict, Optional

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
    notes: list[str] = Field(description="Important behavioral notes")
    path_match_hints: Dict[str, str] = Field(
        default_factory=dict,
        description="Per-tool notes on what path_regex matches",
    )
    tools: Dict[str, Any] = Field(description="policy_key -> allowed block properties")
    minimal_example: Dict[str, Any] = Field(description="Minimal valid policy fragment")


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
