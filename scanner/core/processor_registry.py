"""Report Processor Registry
Provides a generic registry for tool-specific report processors.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Any
import importlib
import pkgutil


@dataclass
class ReportProcessor:
    name: str
    summary_func: Callable[..., Any]
    html_func: Optional[Callable[..., str]] = None
    ai_normalizer: Optional[Callable[[Any], List[Dict[str, Any]]]] = None
    json_file: Optional[str] = None
    html_file: Optional[str] = None
    extra_files: Optional[List[str]] = None


class ProcessorRegistry:
    _processors: Dict[str, ReportProcessor] = {}

    @classmethod
    def register(cls, processor: ReportProcessor):
        cls._processors[processor.name] = processor

    @classmethod
    def all(cls) -> List[ReportProcessor]:
        return list(cls._processors.values())


def register_default_processors():
    """Register built-in processors used by generate-html-report."""
    _discover_processors()


def _discover_processors():
    """Auto-discover processors from scanner modules."""
    try:
        package = importlib.import_module("scanner.plugins")
    except ImportError:
        # Fallback: processors are registered manually in generate-html-report.py
        return
    
    for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
        if not is_pkg:
            continue
        try:
            processor_module = importlib.import_module(f"{module_name}.processor")
        except Exception:
            continue
        report_processor = getattr(processor_module, "REPORT_PROCESSOR", None)
        if report_processor:
            ProcessorRegistry.register(report_processor)
