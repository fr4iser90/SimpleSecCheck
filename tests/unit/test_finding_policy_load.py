"""Finding policy load — alias resolution and validation logging."""
import json
import tempfile
from pathlib import Path

from scanner.core.finding_policy import load_policy


def test_load_policy_maps_owasp_alias(tmp_path):
    policy = {
        "owasp_dependency_check": {
            "accepted_findings": [{"rule_id": "GHSA-test", "reason": "dev only"}],
        }
    }
    path = tmp_path / "finding-policy.json"
    path.write_text(json.dumps(policy), encoding="utf-8")
    loaded = load_policy(str(path))
    assert "owasp_dc" in loaded
    assert "owasp_dependency_check" not in loaded
