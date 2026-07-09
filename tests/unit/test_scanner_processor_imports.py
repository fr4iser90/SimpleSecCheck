"""Ensure report processors import in the scanner runtime (needs shared/ on PYTHONPATH)."""


def test_bandit_report_processor_imports_with_shared_on_path():
    """Regression: scanner image must ship shared/ so generate-html-report can load processors."""
    from scanner.plugins.bandit.processor import REPORT_PROCESSOR

    assert REPORT_PROCESSOR.name == "Bandit"
    assert REPORT_PROCESSOR.json_file == "report.json"
    assert REPORT_PROCESSOR.summary_func is not None

    sample = {
        "results": [
            {
                "test_id": "B608",
                "issue_severity": "MEDIUM",
                "filename": "src/main.py",
                "line_number": 10,
                "issue_text": "Possible SQL injection",
            }
        ]
    }
    parsed = REPORT_PROCESSOR.summary_func(sample)
    assert isinstance(parsed, list)
    assert len(parsed) == 1


def test_get_processor_helper_imports_without_shared_fails_clearly():
    """Document expected import chain: processor -> ai_normalizer_utils -> shared."""
    import importlib

    mod = importlib.import_module("scanner.output.ai_normalizer_utils")
    assert hasattr(mod, "normalize_finding_fields")
