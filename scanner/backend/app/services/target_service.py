"""
Target classification helpers for WebUI/Runner.
Central place for target detection and validation logic.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


DOCKER_IMAGE_PATTERN = re.compile(
    r"^(?:[a-zA-Z0-9.-]+(?::\d+)?/)?"
    r"[a-z0-9]+(?:[._-][a-z0-9]+)*"
    r"(?:/[a-z0-9]+(?:[._-][a-z0-9]+)*)*"
    r"(?::[\w][\w.-]{0,127})?(?:@sha256:[a-f0-9]{64})?$"
)


GIT_URL_PATTERNS = [
    re.compile(r"^https?://(www\.)?github\.com/[\w\-.]+/[\w\-.]+"),
    re.compile(r"^https?://(www\.)?gitlab\.com/[\w\-.]+/[\w\-.]+"),
    re.compile(r"^git@(github|gitlab)\.com:[\w\-.]+/[\w\-.]+\.git$"),
]


@dataclass(frozen=True)
class TargetInfo:
    scan_type: str  # code, image, website, network
    is_git: bool
    is_image: bool
    is_local_path: bool
    is_website: bool
    is_network: bool


def is_git_url(value: str) -> bool:
    if not value or not value.strip():
        return False
    return any(pattern.match(value.strip()) for pattern in GIT_URL_PATTERNS)


def is_docker_image_ref(value: str) -> bool:
    if not value or value.startswith(("/", "./", "../")):
        return False
    if value.startswith(("http://", "https://")):
        return False
    return DOCKER_IMAGE_PATTERN.match(value.strip()) is not None


def is_dockerhub_image_ref(value: str) -> bool:
    trimmed = value.strip()
    if "/" not in trimmed:
        return True
    first = trimmed.split("/")[0]
    has_registry = "." in first or ":" in first
    if not has_registry:
        return True
    return first == "docker.io"


def normalize_scan_type(scan_type: str) -> str:
    normalized = (scan_type or "").lower()
    if normalized not in {"code", "website", "network", "image"}:
        return "code"
    return normalized


def guess_scan_type(target: str) -> str:
    clean_target = (target or "").strip()
    if clean_target == "network":
        return "network"
    if clean_target.startswith(("http://", "https://")):
        return "website"
    return "code"


def classify_target(scan_type: str, target: str) -> TargetInfo:
    normalized_scan_type = normalize_scan_type(scan_type)
    clean_target = (target or "").strip()
    is_network = normalized_scan_type == "network" or clean_target == "network"
    is_website = normalized_scan_type == "website" or clean_target.startswith(("http://", "https://"))
    is_git = normalized_scan_type == "code" and is_git_url(clean_target)
    is_image = normalized_scan_type == "image" or (
        normalized_scan_type == "code" and not is_git and is_docker_image_ref(clean_target)
    )
    is_local_path = normalized_scan_type == "code" and clean_target.startswith(("/", "./", "../"))
    return TargetInfo(
        scan_type=normalized_scan_type,
        is_git=is_git,
        is_image=is_image,
        is_local_path=is_local_path,
        is_website=is_website,
        is_network=is_network,
    )


def classify_target_from_target(target: str) -> TargetInfo:
    return classify_target(guess_scan_type(target), target)