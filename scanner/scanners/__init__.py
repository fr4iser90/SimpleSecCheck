"""
Scanner Implementations
Python implementations of scanner scripts

Auto-registers all scanners on import via dynamic discovery.
"""
import importlib
import pkgutil

try:
    from scanner.core.scanner_registry import ScannerRegistry
except ImportError:
    from core.scanner_registry import ScannerRegistry


def _discover_scanner_modules():
    """Discover all scanner modules and register scanner classes."""
    package_name = __name__
    package = importlib.import_module(package_name)

    for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
        if not is_pkg:
            continue
        try:
            scanner_module = importlib.import_module(f"{module_name}.scanner")
        except Exception:
            continue

        for attr in dir(scanner_module):
            if not attr.endswith("Scanner"):
                continue
            scanner_class = getattr(scanner_module, attr)
            try:
                ScannerRegistry.register_from_class(scanner_class)
            except Exception:
                continue


_discover_scanner_modules()

__all__ = []
