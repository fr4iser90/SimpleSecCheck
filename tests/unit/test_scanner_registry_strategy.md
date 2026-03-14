# Testing Strategy: scanner/core/scanner_registry.py

## Overview
This document outlines comprehensive test coverage for the scanner registry module, which is critical for scanner discovery, registration, and filtering logic.

---

## Test-Worthy Functions/Classes

### 1. `ScannerRegistry.register()`
**Type:** Unit Test  
**Priority:** HIGH  
**Rationale:** Core registration logic - must ensure scanners are properly stored and can be retrieved.

**Test Cases:**
- Register a single scanner successfully
- Register multiple scanners with different names
- Register scanner with same name (should overwrite)
- Register scanner with all optional fields (priority, requires_condition, python_class)
- Register scanner with minimal required fields

**Branches to Cover:**
- Normal registration path
- Overwrite existing scanner path

---

### 2. `ScannerRegistry.get_scanners_for_target()`
**Type:** Unit Test / Service Test  
**Priority:** CRITICAL  
**Rationale:** Core filtering logic with multiple conditional branches - critical for scan workflow.

**Test Cases:**
- Get scanners for target type with no filters
- Get scanners filtered by scan_types
- Get scanners with condition requirements (IS_NATIVE, etc.)
- Exclude disabled scanners
- Return scanners sorted by priority
- Handle empty registry
- Handle target type with no matching scanners
- Handle condition mismatch (scanner requires condition but not provided)
- Handle condition mismatch (scanner requires condition but condition is False)
- Handle multiple capabilities per scanner
- Handle scanner matching multiple scan_types

**Branches to Cover:**
- `if not scanner.enabled: continue` (line 103)
- `if scanner.requires_condition:` (line 106)
- `if not conditions or not conditions.get(...):` (line 107)
- `if target_type not in capability.supported_targets: continue` (line 112)
- `if scan_types and capability.scan_type not in scan_types: continue` (line 114)
- `if matches: scanners.append(scanner)` (line 118)
- Sorting by priority (line 120)

---

### 3. `ScannerRegistry.get_scanners_for_type()`
**Type:** Unit Test  
**Priority:** HIGH  
**Rationale:** Filtering by scan type - simpler than get_scanners_for_target but still critical.

**Test Cases:**
- Get scanners for specific scan type
- Exclude disabled scanners
- Return scanners sorted by priority
- Handle empty registry
- Handle scan type with no matching scanners
- Handle scanner with multiple capabilities (one matches, one doesn't)
- Handle scanner with multiple capabilities (both match)

**Branches to Cover:**
- `if not scanner.enabled: continue` (line 135)
- `if capability.scan_type == scan_type:` (line 138)
- `break` after first match (line 140)
- Sorting by priority (line 141)

---

### 4. `ScannerRegistry.get_total_steps()`
**Type:** Unit Test / Service Test  
**Priority:** HIGH  
**Rationale:** Critical for progress tracking and UI display - calculates total workflow steps.

**Test Cases:**
- Calculate steps with git clone enabled
- Calculate steps without git clone
- Calculate steps with metadata collection enabled
- Calculate steps without metadata collection
- Calculate steps with both git clone and metadata
- Calculate steps with no scanners matching
- Calculate steps with multiple scanners
- Verify step count includes: initialization, completion, scanners, optional steps

**Branches to Cover:**
- `if has_git_clone: steps += 1` (line 163)
- `if collect_metadata: steps += 1` (line 172)
- Always add initialization (line 166)
- Always add completion (line 175)
- Scanner count from `get_scanners_for_target()` (line 169)

---

### 5. `ScannerRegistry.get_all_scanners()`
**Type:** Unit Test  
**Priority:** LOW  
**Rationale:** Simple getter, but should verify it returns all registered scanners.

**Test Cases:**
- Get all scanners from empty registry
- Get all scanners with multiple registered scanners
- Verify returned list is independent copy (not reference)

**Branches to Cover:**
- Empty registry path
- Non-empty registry path

---

### 6. `ScannerRegistry.get_scanner()`
**Type:** Unit Test  
**Priority:** MEDIUM  
**Rationale:** Simple lookup, but critical for scanner retrieval by name.

**Test Cases:**
- Get scanner by name (exists)
- Get scanner by name (doesn't exist) - returns None
- Get scanner with exact name match
- Get scanner case-sensitive matching

**Branches to Cover:**
- Scanner exists: `return cls._scanners.get(name)`
- Scanner doesn't exist: returns None

---

### 7. `ScannerRegistry.register_from_class()`
**Type:** Unit Test / Integration Test  
**Priority:** CRITICAL  
**Rationale:** Complex auto-discovery logic with multiple fallback paths and manifest loading - critical for dynamic scanner registration.

**Test Cases:**
- Register scanner with SCANNER_NAME attribute
- Register scanner with NAME attribute (fallback)
- Register scanner with manifest.yaml name (fallback)
- Register scanner with class name transformation (fallback)
- Register scanner with OWASP class name transformation
- Register scanner with capabilities from class
- Register scanner with priority from class
- Register scanner with requires_condition from class
- Register scanner with script_path from class
- Handle manifest loading failure gracefully
- Handle module path parsing for plugin discovery
- Handle invalid module path gracefully
- Verify python_class is correctly formatted
- Test all name resolution fallback chain

**Branches to Cover:**
- `if not getattr(scanner_class, "SCANNER_NAME", None) and not getattr(scanner_class, "NAME", None):` (line 205)
- `if module and "scanner.plugins." in module:` (line 207)
- `if len(parts) >= 3 and parts[0] == "scanner" and parts[1] == "plugins":` (line 209)
- `if scanners_root.exists():` (line 216)
- `if manifest_path.exists():` (line 218)
- `if manifest:` (line 221)
- `except Exception: pass` (line 223) - manifest loading failure
- Name resolution fallback chain (lines 227-232)
- `or class_name.replace("Scanner", "").replace("OWASP", "OWASP Dependency Check")` (line 231)

---

## Test Implementation Examples

### Fixtures (conftest.py additions)

```python
import pytest
from scanner.core.scanner_registry import (
    ScannerRegistry,
    Scanner,
    ScannerCapability,
    ScanType,
    TargetType,
    ArtifactType
)

@pytest.fixture
def clean_registry():
    """Clear registry before each test."""
    ScannerRegistry._scanners.clear()
    yield
    ScannerRegistry._scanners.clear()

@pytest.fixture
def sample_scanner():
    """Create a sample scanner for testing."""
    capability = ScannerCapability(
        scan_type=ScanType.CODE,
        supported_targets=[TargetType.GIT_REPO, TargetType.LOCAL_MOUNT],
        supported_artifacts=[ArtifactType.PACKAGE_JSON]
    )
    return Scanner(
        name="TestScanner",
        capabilities=[capability],
        script_path="/app/scripts/test_scanner.sh",
        enabled=True,
        priority=0
    )

@pytest.fixture
def multiple_scanners():
    """Create multiple scanners with different priorities."""
    scanners = []
    for i in range(3):
        capability = ScannerCapability(
            scan_type=ScanType.CODE,
            supported_targets=[TargetType.GIT_REPO],
            supported_artifacts=[]
        )
        scanners.append(Scanner(
            name=f"Scanner{i}",
            capabilities=[capability],
            script_path=f"/app/scripts/scanner{i}.sh",
            enabled=True,
            priority=i  # Different priorities
        ))
    return scanners

@pytest.fixture
def mock_scanner_class():
    """Mock scanner class for register_from_class tests."""
    class MockScannerClass:
        SCANNER_NAME = "MockScanner"
        CAPABILITIES = [
            ScannerCapability(
                scan_type=ScanType.CODE,
                supported_targets=[TargetType.GIT_REPO],
                supported_artifacts=[]
            )
        ]
        PRIORITY = 5
        REQUIRES_CONDITION = None
        SCRIPT_PATH = "/app/scripts/mock.sh"
        __name__ = "MockScannerClass"
        __module__ = "scanner.plugins.mock.scanner"
    
    return MockScannerClass
```

---

### Test File: `tests/unit/test_scanner_registry.py`

```python
"""
Unit tests for scanner registry module.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from scanner.core.scanner_registry import (
    ScannerRegistry,
    Scanner,
    ScannerCapability,
    ScanType,
    TargetType,
    ArtifactType
)


class TestScannerRegistryRegister:
    """Tests for ScannerRegistry.register()"""
    
    def test_register_single_scanner(self, clean_registry, sample_scanner):
        """Test registering a single scanner."""
        ScannerRegistry.register(sample_scanner)
        
        assert len(ScannerRegistry._scanners) == 1
        assert ScannerRegistry._scanners["TestScanner"] == sample_scanner
    
    def test_register_multiple_scanners(self, clean_registry, multiple_scanners):
        """Test registering multiple scanners."""
        for scanner in multiple_scanners:
            ScannerRegistry.register(scanner)
        
        assert len(ScannerRegistry._scanners) == 3
        assert "Scanner0" in ScannerRegistry._scanners
        assert "Scanner1" in ScannerRegistry._scanners
        assert "Scanner2" in ScannerRegistry._scanners
    
    def test_register_overwrites_existing(self, clean_registry, sample_scanner):
        """Test that registering with same name overwrites."""
        ScannerRegistry.register(sample_scanner)
        
        new_scanner = Scanner(
            name="TestScanner",
            capabilities=[],
            script_path="/new/path.sh",
            enabled=False,
            priority=10
        )
        ScannerRegistry.register(new_scanner)
        
        assert len(ScannerRegistry._scanners) == 1
        assert ScannerRegistry._scanners["TestScanner"].script_path == "/new/path.sh"
        assert ScannerRegistry._scanners["TestScanner"].enabled is False
    
    def test_register_with_all_fields(self, clean_registry):
        """Test registering scanner with all optional fields."""
        capability = ScannerCapability(
            scan_type=ScanType.SECRETS,
            supported_targets=[TargetType.GIT_REPO],
            supported_artifacts=[]
        )
        scanner = Scanner(
            name="FullScanner",
            capabilities=[capability],
            script_path="/app/scripts/full.sh",
            enabled=True,
            priority=5,
            requires_condition="IS_NATIVE",
            python_class="scanner.plugins.full.FullScanner"
        )
        
        ScannerRegistry.register(scanner)
        
        registered = ScannerRegistry._scanners["FullScanner"]
        assert registered.requires_condition == "IS_NATIVE"
        assert registered.python_class == "scanner.plugins.full.FullScanner"


class TestScannerRegistryGetScannersForTarget:
    """Tests for ScannerRegistry.get_scanners_for_target()"""
    
    def test_get_scanners_no_filters(self, clean_registry, sample_scanner):
        """Test getting scanners with no filters."""
        ScannerRegistry.register(sample_scanner)
        
        scanners = ScannerRegistry.get_scanners_for_target(TargetType.GIT_REPO)
        
        assert len(scanners) == 1
        assert scanners[0].name == "TestScanner"
    
    def test_get_scanners_filtered_by_scan_type(self, clean_registry):
        """Test filtering scanners by scan type."""
        code_capability = ScannerCapability(
            scan_type=ScanType.CODE,
            supported_targets=[TargetType.GIT_REPO],
            supported_artifacts=[]
        )
        secrets_capability = ScannerCapability(
            scan_type=ScanType.SECRETS,
            supported_targets=[TargetType.GIT_REPO],
            supported_artifacts=[]
        )
        
        code_scanner = Scanner(
            name="CodeScanner",
            capabilities=[code_capability],
            script_path="/app/code.sh",
            enabled=True
        )
        secrets_scanner = Scanner(
            name="SecretsScanner",
            capabilities=[secrets_capability],
            script_path="/app/secrets.sh",
            enabled=True
        )
        
        ScannerRegistry.register(code_scanner)
        ScannerRegistry.register(secrets_scanner)
        
        scanners = ScannerRegistry.get_scanners_for_target(
            TargetType.GIT_REPO,
            scan_types=[ScanType.CODE]
        )
        
        assert len(scanners) == 1
        assert scanners[0].name == "CodeScanner"
    
    def test_get_scanners_excludes_disabled(self, clean_registry, sample_scanner):
        """Test that disabled scanners are excluded."""
        disabled_scanner = Scanner(
            name="DisabledScanner",
            capabilities=sample_scanner.capabilities,
            script_path="/app/disabled.sh",
            enabled=False
        )
        
        ScannerRegistry.register(sample_scanner)
        ScannerRegistry.register(disabled_scanner)
        
        scanners = ScannerRegistry.get_scanners_for_target(TargetType.GIT_REPO)
        
        assert len(scanners) == 1
        assert scanners[0].name == "TestScanner"
    
    def test_get_scanners_with_condition_required(self, clean_registry):
        """Test scanner with condition requirement."""
        capability = ScannerCapability(
            scan_type=ScanType.CODE,
            supported_targets=[TargetType.GIT_REPO],
            supported_artifacts=[]
        )
        conditional_scanner = Scanner(
            name="ConditionalScanner",
            capabilities=[capability],
            script_path="/app/conditional.sh",
            enabled=True,
            requires_condition="IS_NATIVE"
        )
        
        ScannerRegistry.register(conditional_scanner)
        
        # Without condition - should not return scanner
        scanners = ScannerRegistry.get_scanners_for_target(TargetType.GIT_REPO)
        assert len(scanners) == 0
        
        # With condition False - should not return scanner
        scanners = ScannerRegistry.get_scanners_for_target(
            TargetType.GIT_REPO,
            conditions={"IS_NATIVE": False}
        )
        assert len(scanners) == 0
        
        # With condition True - should return scanner
        scanners = ScannerRegistry.get_scanners_for_target(
            TargetType.GIT_REPO,
            conditions={"IS_NATIVE": True}
        )
        assert len(scanners) == 1
        assert scanners[0].name == "ConditionalScanner"
    
    def test_get_scanners_sorted_by_priority(self, clean_registry, multiple_scanners):
        """Test that scanners are returned sorted by priority."""
        # Reverse order registration
        for scanner in reversed(multiple_scanners):
            ScannerRegistry.register(scanner)
        
        scanners = ScannerRegistry.get_scanners_for_target(TargetType.GIT_REPO)
        
        assert len(scanners) == 3
        assert scanners[0].priority == 0
        assert scanners[1].priority == 1
        assert scanners[2].priority == 2
    
    def test_get_scanners_empty_registry(self, clean_registry):
        """Test getting scanners from empty registry."""
        scanners = ScannerRegistry.get_scanners_for_target(TargetType.GIT_REPO)
        assert len(scanners) == 0
    
    def test_get_scanners_no_matching_target(self, clean_registry, sample_scanner):
        """Test getting scanners for target type with no matches."""
        ScannerRegistry.register(sample_scanner)
        
        scanners = ScannerRegistry.get_scanners_for_target(TargetType.WEBSITE)
        assert len(scanners) == 0
    
    def test_get_scanners_multiple_capabilities(self, clean_registry):
        """Test scanner with multiple capabilities."""
        capability1 = ScannerCapability(
            scan_type=ScanType.CODE,
            supported_targets=[TargetType.GIT_REPO],
            supported_artifacts=[]
        )
        capability2 = ScannerCapability(
            scan_type=ScanType.SECRETS,
            supported_targets=[TargetType.GIT_REPO],
            supported_artifacts=[]
        )
        
        multi_scanner = Scanner(
            name="MultiScanner",
            capabilities=[capability1, capability2],
            script_path="/app/multi.sh",
            enabled=True
        )
        
        ScannerRegistry.register(multi_scanner)
        
        # Should match for CODE scan type
        scanners = ScannerRegistry.get_scanners_for_target(
            TargetType.GIT_REPO,
            scan_types=[ScanType.CODE]
        )
        assert len(scanners) == 1
        
        # Should match for SECRETS scan type
        scanners = ScannerRegistry.get_scanners_for_target(
            TargetType.GIT_REPO,
            scan_types=[ScanType.SECRETS]
        )
        assert len(scanners) == 1


class TestScannerRegistryGetScannersForType:
    """Tests for ScannerRegistry.get_scanners_for_type()"""
    
    def test_get_scanners_for_scan_type(self, clean_registry):
        """Test getting scanners for specific scan type."""
        code_capability = ScannerCapability(
            scan_type=ScanType.CODE,
            supported_targets=[TargetType.GIT_REPO],
            supported_artifacts=[]
        )
        secrets_capability = ScannerCapability(
            scan_type=ScanType.SECRETS,
            supported_targets=[TargetType.GIT_REPO],
            supported_artifacts=[]
        )
        
        code_scanner = Scanner(
            name="CodeScanner",
            capabilities=[code_capability],
            script_path="/app/code.sh",
            enabled=True
        )
        secrets_scanner = Scanner(
            name="SecretsScanner",
            capabilities=[secrets_capability],
            script_path="/app/secrets.sh",
            enabled=True
        )
        
        ScannerRegistry.register(code_scanner)
        ScannerRegistry.register(secrets_scanner)
        
        scanners = ScannerRegistry.get_scanners_for_type(ScanType.CODE)
        
        assert len(scanners) == 1
        assert scanners[0].name == "CodeScanner"
    
    def test_get_scanners_for_type_excludes_disabled(self, clean_registry):
        """Test that disabled scanners are excluded."""
        capability = ScannerCapability(
            scan_type=ScanType.CODE,
            supported_targets=[TargetType.GIT_REPO],
            supported_artifacts=[]
        )
        disabled_scanner = Scanner(
            name="DisabledScanner",
            capabilities=[capability],
            script_path="/app/disabled.sh",
            enabled=False
        )
        
        ScannerRegistry.register(disabled_scanner)
        
        scanners = ScannerRegistry.get_scanners_for_type(ScanType.CODE)
        assert len(scanners) == 0


class TestScannerRegistryGetTotalSteps:
    """Tests for ScannerRegistry.get_total_steps()"""
    
    def test_get_total_steps_with_git_clone(self, clean_registry, sample_scanner):
        """Test calculating steps with git clone enabled."""
        ScannerRegistry.register(sample_scanner)
        
        steps = ScannerRegistry.get_total_steps(
            target_type=TargetType.GIT_REPO,
            scan_types=[ScanType.CODE],
            has_git_clone=True,
            collect_metadata=False
        )
        
        # 1 (git clone) + 1 (init) + 1 (scanner) + 1 (completion) = 4
        assert steps == 4
    
    def test_get_total_steps_without_git_clone(self, clean_registry, sample_scanner):
        """Test calculating steps without git clone."""
        ScannerRegistry.register(sample_scanner)
        
        steps = ScannerRegistry.get_total_steps(
            target_type=TargetType.GIT_REPO,
            scan_types=[ScanType.CODE],
            has_git_clone=False,
            collect_metadata=False
        )
        
        # 1 (init) + 1 (scanner) + 1 (completion) = 3
        assert steps == 3
    
    def test_get_total_steps_with_metadata(self, clean_registry, sample_scanner):
        """Test calculating steps with metadata collection."""
        ScannerRegistry.register(sample_scanner)
        
        steps = ScannerRegistry.get_total_steps(
            target_type=TargetType.GIT_REPO,
            scan_types=[ScanType.CODE],
            has_git_clone=False,
            collect_metadata=True
        )
        
        # 1 (init) + 1 (scanner) + 1 (metadata) + 1 (completion) = 4
        assert steps == 4
    
    def test_get_total_steps_all_options(self, clean_registry, multiple_scanners):
        """Test calculating steps with all options enabled."""
        for scanner in multiple_scanners:
            ScannerRegistry.register(scanner)
        
        steps = ScannerRegistry.get_total_steps(
            target_type=TargetType.GIT_REPO,
            scan_types=[ScanType.CODE],
            has_git_clone=True,
            collect_metadata=True
        )
        
        # 1 (git clone) + 1 (init) + 3 (scanners) + 1 (metadata) + 1 (completion) = 7
        assert steps == 7
    
    def test_get_total_steps_no_scanners(self, clean_registry):
        """Test calculating steps with no matching scanners."""
        steps = ScannerRegistry.get_total_steps(
            target_type=TargetType.GIT_REPO,
            scan_types=[ScanType.CODE],
            has_git_clone=False,
            collect_metadata=False
        )
        
        # 1 (init) + 0 (scanners) + 1 (completion) = 2
        assert steps == 2


class TestScannerRegistryGetAllScanners:
    """Tests for ScannerRegistry.get_all_scanners()"""
    
    def test_get_all_scanners_empty(self, clean_registry):
        """Test getting all scanners from empty registry."""
        scanners = ScannerRegistry.get_all_scanners()
        assert len(scanners) == 0
    
    def test_get_all_scanners_multiple(self, clean_registry, multiple_scanners):
        """Test getting all scanners."""
        for scanner in multiple_scanners:
            ScannerRegistry.register(scanner)
        
        scanners = ScannerRegistry.get_all_scanners()
        assert len(scanners) == 3
    
    def test_get_all_scanners_returns_copy(self, clean_registry, sample_scanner):
        """Test that returned list is independent copy."""
        ScannerRegistry.register(sample_scanner)
        
        scanners1 = ScannerRegistry.get_all_scanners()
        scanners2 = ScannerRegistry.get_all_scanners()
        
        assert scanners1 is not scanners2
        assert scanners1 == scanners2


class TestScannerRegistryGetScanner:
    """Tests for ScannerRegistry.get_scanner()"""
    
    def test_get_scanner_exists(self, clean_registry, sample_scanner):
        """Test getting scanner that exists."""
        ScannerRegistry.register(sample_scanner)
        
        scanner = ScannerRegistry.get_scanner("TestScanner")
        assert scanner is not None
        assert scanner.name == "TestScanner"
    
    def test_get_scanner_not_exists(self, clean_registry):
        """Test getting scanner that doesn't exist."""
        scanner = ScannerRegistry.get_scanner("NonExistent")
        assert scanner is None
    
    def test_get_scanner_case_sensitive(self, clean_registry, sample_scanner):
        """Test that scanner lookup is case-sensitive."""
        ScannerRegistry.register(sample_scanner)
        
        scanner = ScannerRegistry.get_scanner("testscanner")  # lowercase
        assert scanner is None


class TestScannerRegistryRegisterFromClass:
    """Tests for ScannerRegistry.register_from_class()"""
    
    def test_register_from_class_with_scanner_name(self, clean_registry):
        """Test registering with SCANNER_NAME attribute."""
        class TestScannerClass:
            SCANNER_NAME = "ExplicitName"
            CAPABILITIES = [
                ScannerCapability(
                    scan_type=ScanType.CODE,
                    supported_targets=[TargetType.GIT_REPO],
                    supported_artifacts=[]
                )
            ]
            PRIORITY = 10
            SCRIPT_PATH = "/app/test.sh"
            __name__ = "TestScannerClass"
            __module__ = "scanner.plugins.test.scanner"
        
        ScannerRegistry.register_from_class(TestScannerClass)
        
        scanner = ScannerRegistry.get_scanner("ExplicitName")
        assert scanner is not None
        assert scanner.name == "ExplicitName"
        assert scanner.priority == 10
    
    def test_register_from_class_with_name_fallback(self, clean_registry):
        """Test registering with NAME attribute (fallback)."""
        class TestScannerClass:
            NAME = "NameFallback"
            CAPABILITIES = []
            PRIORITY = 0
            SCRIPT_PATH = "/app/test.sh"
            __name__ = "TestScannerClass"
            __module__ = "scanner.plugins.test.scanner"
        
        ScannerRegistry.register_from_class(TestScannerClass)
        
        scanner = ScannerRegistry.get_scanner("NameFallback")
        assert scanner is not None
    
    def test_register_from_class_with_class_name_fallback(self, clean_registry):
        """Test registering with class name transformation (fallback)."""
        class SemgrepScanner:
            CAPABILITIES = []
            PRIORITY = 0
            SCRIPT_PATH = "/app/test.sh"
            __name__ = "SemgrepScanner"
            __module__ = "scanner.plugins.semgrep.scanner"
        
        ScannerRegistry.register_from_class(SemgrepScanner)
        
        scanner = ScannerRegistry.get_scanner("Semgrep")
        assert scanner is not None
    
    def test_register_from_class_owasp_transformation(self, clean_registry):
        """Test OWASP class name transformation."""
        class OWASPDependencyCheckScanner:
            CAPABILITIES = []
            PRIORITY = 0
            SCRIPT_PATH = "/app/test.sh"
            __name__ = "OWASPDependencyCheckScanner"
            __module__ = "scanner.plugins.owasp.scanner"
        
        ScannerRegistry.register_from_class(OWASPDependencyCheckScanner)
        
        scanner = ScannerRegistry.get_scanner("OWASP Dependency Check")
        assert scanner is not None
    
    @patch('scanner.core.scanner_registry.ScannerAssetsManager')
    @patch('scanner.core.scanner_registry.Path')
    def test_register_from_class_with_manifest(self, mock_path, mock_assets_manager, clean_registry):
        """Test registering with manifest.yaml name."""
        # Mock manifest loading
        mock_manifest = MagicMock()
        mock_manifest.name = "ManifestScanner"
        
        mock_assets_manager_instance = MagicMock()
        mock_assets_manager_instance.get_manifest.return_value = mock_manifest
        mock_assets_manager.return_value = mock_assets_manager_instance
        
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        class TestScannerClass:
            CAPABILITIES = []
            PRIORITY = 0
            SCRIPT_PATH = "/app/test.sh"
            __name__ = "TestScannerClass"
            __module__ = "scanner.plugins.test.scanner"
        
        ScannerRegistry.register_from_class(TestScannerClass)
        
        scanner = ScannerRegistry.get_scanner("ManifestScanner")
        assert scanner is not None
    
    @patch('scanner.core.scanner_registry.ScannerAssetsManager')
    @patch('scanner.core.scanner_registry.Path')
    def test_register_from_class_manifest_loading_failure(self, mock_path, mock_assets_manager, clean_registry):
        """Test that manifest loading failure is handled gracefully."""
        # Mock manifest loading failure
        mock_assets_manager.side_effect = Exception("Manifest load failed")
        
        class TestScannerClass:
            CAPABILITIES = []
            PRIORITY = 0
            SCRIPT_PATH = "/app/test.sh"
            __name__ = "TestScannerClass"
            __module__ = "scanner.plugins.test.scanner"
        
        # Should not raise exception, should fall back to class name
        ScannerRegistry.register_from_class(TestScannerClass)
        
        scanner = ScannerRegistry.get_scanner("Test")
        assert scanner is not None
    
    def test_register_from_class_python_class_format(self, clean_registry):
        """Test that python_class is correctly formatted."""
        class TestScannerClass:
            SCANNER_NAME = "TestScanner"
            CAPABILITIES = []
            PRIORITY = 0
            SCRIPT_PATH = "/app/test.sh"
            __name__ = "TestScannerClass"
            __module__ = "scanner.plugins.test.scanner"
        
        ScannerRegistry.register_from_class(TestScannerClass)
        
        scanner = ScannerRegistry.get_scanner("TestScanner")
        assert scanner.python_class == "scanner.plugins.test.scanner.TestScannerClass"
    
    def test_register_from_class_with_requires_condition(self, clean_registry):
        """Test registering scanner with condition requirement."""
        class ConditionalScannerClass:
            SCANNER_NAME = "ConditionalScanner"
            CAPABILITIES = []
            PRIORITY = 0
            REQUIRES_CONDITION = "IS_NATIVE"
            SCRIPT_PATH = "/app/test.sh"
            __name__ = "ConditionalScannerClass"
            __module__ = "scanner.plugins.conditional.scanner"
        
        ScannerRegistry.register_from_class(ConditionalScannerClass)
        
        scanner = ScannerRegistry.get_scanner("ConditionalScanner")
        assert scanner.requires_condition == "IS_NATIVE"
```

---

## Integration Tests

### Test Scanner Discovery Workflow
**Type:** Integration Test  
**Priority:** HIGH

```python
class TestScannerDiscoveryIntegration:
    """Integration tests for scanner discovery and registration."""
    
    def test_full_scanner_discovery_workflow(self, clean_registry):
        """Test complete workflow: register -> filter -> retrieve."""
        # Register multiple scanners
        scanners = []
        for i, scan_type in enumerate([ScanType.CODE, ScanType.SECRETS, ScanType.DEPENDENCY]):
            capability = ScannerCapability(
                scan_type=scan_type,
                supported_targets=[TargetType.GIT_REPO],
                supported_artifacts=[]
            )
            scanner = Scanner(
                name=f"Scanner{i}",
                capabilities=[capability],
                script_path=f"/app/scanner{i}.sh",
                enabled=True,
                priority=i
            )
            scanners.append(scanner)
            ScannerRegistry.register(scanner)
        
        # Filter by target and scan type
        code_scanners = ScannerRegistry.get_scanners_for_target(
            TargetType.GIT_REPO,
            scan_types=[ScanType.CODE]
        )
        
        assert len(code_scanners) == 1
        assert code_scanners[0].name == "Scanner0"
        
        # Calculate total steps
        steps = ScannerRegistry.get_total_steps(
            target_type=TargetType.GIT_REPO,
            scan_types=[ScanType.CODE],
            has_git_clone=True,
            collect_metadata=True
        )
        
        assert steps == 5  # git clone + init + 1 scanner + metadata + completion
```

---

## Security & Edge Cases

### Test Cases for Security/Edge Cases:

1. **Malicious scanner name injection** - Test with special characters, SQL injection patterns
2. **Very long scanner names** - Test with extremely long names
3. **None/null values** - Test with None for optional parameters
4. **Empty lists** - Test with empty capabilities, empty target lists
5. **Invalid enum values** - Test with invalid ScanType/TargetType (if possible)
6. **Concurrent registration** - Test thread safety if applicable
7. **Memory leaks** - Test that registry doesn't grow unbounded

---

## Coverage Goals

- **Branch Coverage:** 100% (all if/else paths)
- **Function Coverage:** 100% (all public methods)
- **Condition Coverage:** 100% (all boolean conditions evaluated both ways)

---

## Notes

1. **State Management:** The registry uses class-level `_scanners` dict - tests must clean up between runs
2. **Dependencies:** `register_from_class()` depends on `ScannerAssetsManager` - must be mocked
3. **File System:** Manifest loading requires file system access - use mocks in unit tests
4. **Performance:** Consider testing with large numbers of scanners (1000+) for performance tests
