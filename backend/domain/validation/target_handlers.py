"""
Target handlers - plugin-style per target_type.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from domain.entities.scan_target import ScanTarget


class TargetHandler(ABC):
    @property
    @abstractmethod
    def target_type(self) -> str:
        pass

    def validate_source(self, source: str) -> None:
        if not source or not source.strip():
            raise ValueError("source is required")

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return dict(config or {})

    def prepare_scan_params(self, target: ScanTarget) -> Dict[str, Any]:
        return {
            "target_url": target.source,
            "target_type": target.type,
            "config": target.config,
        }


class GitTargetHandler(TargetHandler):
    @property
    def target_type(self) -> str:
        return "git_repo"

    def validate_source(self, source: str) -> None:
        super().validate_source(source)
        if "github.com" not in source and "gitlab.com" not in source:
            raise ValueError("Git source must be a GitHub or GitLab URL")

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        from domain.value_objects.target_config_schemas import GitTargetConfig
        c = GitTargetConfig(**(config or {}))
        return c.model_dump()

    def prepare_scan_params(self, target: ScanTarget) -> Dict[str, Any]:
        params = super().prepare_scan_params(target)
        params.setdefault("config", {})["branch"] = target.config.get("branch", "main")
        return params


class ContainerTargetHandler(TargetHandler):
    @property
    def target_type(self) -> str:
        return "container_registry"

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        from domain.value_objects.target_config_schemas import ContainerTargetConfig
        c = ContainerTargetConfig(**(config or {}))
        return c.model_dump()


class LocalTargetHandler(TargetHandler):
    @property
    def target_type(self) -> str:
        return "local_mount"

    def validate_source(self, source: str) -> None:
        super().validate_source(source)
        if not source.startswith("/"):
            raise ValueError("Local source must be an absolute path")

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        from domain.value_objects.target_config_schemas import LocalTargetConfig
        c = LocalTargetConfig(**(config or {}))
        return c.model_dump()


def get_target_handler(target_type: str) -> Optional[TargetHandler]:
    return _HANDLERS.get(target_type)


def validate_target_source_and_config(target_type: str, source: str, config: Dict[str, Any]) -> Dict[str, Any]:
    from domain.entities.target_type import TargetType
    if not TargetType.is_valid(target_type):
        raise ValueError(
            f"Invalid target type: {target_type!r}. Valid types: {', '.join(TargetType.get_all_values())}"
        )
    handler = get_target_handler(target_type)
    if not handler:
        raise ValueError(f"No handler for target type: {target_type}")
    handler.validate_source(source)
    return handler.validate_config(config)


_HANDLERS: Dict[str, TargetHandler] = {
    "git_repo": GitTargetHandler(),
    "container_registry": ContainerTargetHandler(),
    "local_mount": LocalTargetHandler(),
}
