"""
Typed config schemas per target_type.

Validated per type; serialized as JSON in DB.
Single place for validation – no untyped config dump.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class GitTargetConfig(BaseModel):
    """Config for target_type=git_repo."""
    branch: str = Field(default="main", description="Branch to scan")
    scanners: Optional[List[str]] = Field(default=None, description="Scanner names to run; empty/None = use defaults")
    # auth_token: optional, stored separately/encrypted in real impl


class ContainerTargetConfig(BaseModel):
    """Config for target_type=container_registry."""
    tag: str = Field(default="latest", description="Image tag")
    scanners: Optional[List[str]] = Field(default=None, description="Scanner names to run; empty/None = use defaults")
    # registry inferred from source (docker.io, ghcr.io, etc.)


class LocalTargetConfig(BaseModel):
    """Config for target_type=local_mount. Admin-only; allowlist enforced elsewhere."""
    path: str = Field(..., description="Absolute path on host (subject to allowlist)")
    scanners: Optional[List[str]] = Field(default=None, description="Scanner names to run; empty/None = use defaults")


# Registry: target_type -> config model class (for validate_config)
TARGET_CONFIG_MODELS = {
    "git_repo": GitTargetConfig,
    "container_registry": ContainerTargetConfig,
    "local_mount": LocalTargetConfig,
}
