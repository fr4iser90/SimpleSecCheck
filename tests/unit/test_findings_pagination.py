"""Unit tests for findings pagination helpers."""
import importlib.util
import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


def _load_module(name: str, rel_path: str):
    spec = importlib.util.spec_from_file_location(name, _BACKEND / rel_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def pagination_module():
    """Load pagination helper without full app imports."""
    mock_schemas = type(sys)("api.schemas.scan_schemas")

    class ScanFindingItemSchema:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class ScanFindingsPaginationSchema:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    mock_schemas.ScanFindingItemSchema = ScanFindingItemSchema
    mock_schemas.ScanFindingsPaginationSchema = ScanFindingsPaginationSchema
    sys.modules["api.schemas.scan_schemas"] = mock_schemas
    return _load_module(
        "findings_pagination",
        "application/helpers/findings_pagination.py",
    )


def _item(severity: str, path: str = "a.py", rule_id: str = "r1"):
    from api.schemas.scan_schemas import ScanFindingItemSchema

    return ScanFindingItemSchema(
        tool="semgrep",
        severity=severity,
        path=path,
        line="1",
        message="msg",
        rule_id=rule_id,
    )


def test_sort_findings_severity_desc(pagination_module):
    items = [
        _item("LOW"),
        _item("CRITICAL"),
        _item("HIGH"),
    ]
    sorted_items = pagination_module.sort_findings(items)
    assert [f.severity for f in sorted_items] == ["CRITICAL", "HIGH", "LOW"]


def test_paginate_no_overlap(pagination_module):
    items = pagination_module.sort_findings(
        [_item("HIGH", path=f"f{i}.py") for i in range(5)]
    )
    page1 = pagination_module.paginate_findings(items, limit=2, offset=0)
    page2 = pagination_module.paginate_findings(items, limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 2
    assert {f.path for f in page1}.isdisjoint({f.path for f in page2})


def test_severity_filter(pagination_module):
    items = [
        _item("CRITICAL"),
        _item("LOW"),
        _item("HIGH"),
    ]
    filtered = pagination_module.filter_findings_by_severity(
        items, {"CRITICAL", "HIGH"}
    )
    assert len(filtered) == 2
    assert all(f.severity in ("CRITICAL", "HIGH") for f in filtered)


def test_build_pagination_meta_next_path(pagination_module):
    meta = pagination_module.build_pagination_meta(
        scan_id="scan-1",
        total=100,
        limit=50,
        offset=0,
        returned_count=50,
        severity="CRITICAL,HIGH",
    )
    assert meta.has_more is True
    assert meta.next_path == "/api/v1/scans/scan-1/findings?limit=50&offset=50&severity=CRITICAL%2CHIGH"


def test_build_pagination_meta_no_more(pagination_module):
    meta = pagination_module.build_pagination_meta(
        scan_id="scan-1",
        total=30,
        limit=50,
        offset=0,
        returned_count=30,
    )
    assert meta.has_more is False
    assert meta.next_path is None
