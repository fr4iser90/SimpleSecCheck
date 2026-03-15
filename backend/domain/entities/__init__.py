"""
Domain Entities

This module contains the core domain entities for the SimpleSecCheck backend.
These entities represent the business concepts and contain business logic.
"""
from .target_type import TargetType
from .scan import Scan, ScanType, ScanStatus

__all__ = [
    "TargetType",
    "Scan",
    "ScanType",
    "ScanStatus",
]