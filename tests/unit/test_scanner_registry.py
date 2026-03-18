"""
Unit tests for scanner registry module.

Tests cover:
- Scanner registration
- Scanner filtering by target type and scan type
- Condition-based filtering
- Step calculation
- Class-based auto-registration
- Edge cases and error handling
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


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def clean_registry():
    """Clear registry before and after each test."""
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
            enabled=True,
            priority=i  # Different priorities
        ))
    return scanners


# ============================================================================
# Tests for ScannerRegistry.register()
# ============================================================================

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
            enabled=False,
            priority=10
        )
        ScannerRegistry.register(new_scanner)
        
        assert len(ScannerRegistry._scanners) == 1
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
            enabled=True,
            priority=5,
            requires_condition="IS_NATIVE",
            python_class="scanner.plugins.full.FullScanner"
        )
        
        ScannerRegistry.register(scanner)
        
        registered = ScannerRegistry._scanners["FullScanner"]
        assert registered.requires_condition == "IS_NATIVE"
        assert registered.python_class == "scanner.plugins.full.FullScanner"


# ============================================================================
# Tests for ScannerRegistry.get_scanners_for_target()
# ============================================================================

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
            enabled=True
        )
        secrets_scanner = Scanner(
            name="SecretsScanner",
            capabilities=[secrets_capability],
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
    
    def test_get_scanners_with_condition_none_provided(self, clean_registry):
        """Test scanner with condition when conditions dict is None."""
        capability = ScannerCapability(
            scan_type=ScanType.CODE,
            supported_targets=[TargetType.GIT_REPO],
            supported_artifacts=[]
        )
        conditional_scanner = Scanner(
            name="ConditionalScanner",
            capabilities=[capability],
            enabled=True,
            requires_condition="IS_NATIVE"
        )
        
        ScannerRegistry.register(conditional_scanner)
        
        # With conditions=None - should not return scanner
        scanners = ScannerRegistry.get_scanners_for_target(
            TargetType.GIT_REPO,
            conditions=None
        )
        assert len(scanners) == 0
    
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
    
    def test_get_scanners_capability_no_target_match(self, clean_registry):
        """Test that capability without target match is skipped."""
        capability = ScannerCapability(
            scan_type=ScanType.CODE,
            supported_targets=[TargetType.LOCAL_MOUNT],  # Different target
            supported_artifacts=[]
        )
        scanner = Scanner(
            name="LocalScanner",
            capabilities=[capability],
            enabled=True
        )
        
        ScannerRegistry.register(scanner)
        
        scanners = ScannerRegistry.get_scanners_for_target(TargetType.GIT_REPO)
        assert len(scanners) == 0


# ============================================================================
# Tests for ScannerRegistry.get_scanners_for_type()
# ============================================================================

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
            enabled=True
        )
        secrets_scanner = Scanner(
            name="SecretsScanner",
            capabilities=[secrets_capability],
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
            enabled=False
        )
        
        ScannerRegistry.register(disabled_scanner)
        
        scanners = ScannerRegistry.get_scanners_for_type(ScanType.CODE)
        assert len(scanners) == 0
    
    def test_get_scanners_for_type_sorted_by_priority(self, clean_registry):
        """Test that scanners are sorted by priority."""
        capability = ScannerCapability(
            scan_type=ScanType.CODE,
            supported_targets=[TargetType.GIT_REPO],
            supported_artifacts=[]
        )
        
        scanner1 = Scanner(
            name="Scanner1",
            capabilities=[capability],
            enabled=True,
            priority=10
        )
        scanner2 = Scanner(
            name="Scanner2",
            capabilities=[capability],
            enabled=True,
            priority=5
        )
        
        ScannerRegistry.register(scanner1)
        ScannerRegistry.register(scanner2)
        
        scanners = ScannerRegistry.get_scanners_for_type(ScanType.CODE)
        
        assert len(scanners) == 2
        assert scanners[0].priority == 5  # Lower priority first
        assert scanners[1].priority == 10
    
    def test_get_scanners_for_type_empty_registry(self, clean_registry):
        """Test getting scanners for type from empty registry."""
        scanners = ScannerRegistry.get_scanners_for_type(ScanType.CODE)
        assert len(scanners) == 0


# ============================================================================
# Tests for ScannerRegistry.get_total_steps()
# ============================================================================

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
        
        # StepDefinitionsRegistry: git + init + artifact + completion + scanner_count
        assert steps == 5
    
    def test_get_total_steps_without_git_clone(self, clean_registry, sample_scanner):
        """Test calculating steps without git clone."""
        ScannerRegistry.register(sample_scanner)
        
        steps = ScannerRegistry.get_total_steps(
            target_type=TargetType.GIT_REPO,
            scan_types=[ScanType.CODE],
            has_git_clone=False,
            collect_metadata=False
        )
        
        assert steps == 5  # git_repo always includes Git Clone step + pipeline + 1 scanner
    
    def test_get_total_steps_with_metadata(self, clean_registry, sample_scanner):
        """Test calculating steps with metadata collection."""
        ScannerRegistry.register(sample_scanner)
        
        steps = ScannerRegistry.get_total_steps(
            target_type=TargetType.GIT_REPO,
            scan_types=[ScanType.CODE],
            has_git_clone=False,
            collect_metadata=True
        )
        
        assert steps == 6
    
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
        
        assert steps == 8
    
    def test_get_total_steps_no_scanners(self, clean_registry):
        """Test calculating steps with no matching scanners."""
        steps = ScannerRegistry.get_total_steps(
            target_type=TargetType.GIT_REPO,
            scan_types=[ScanType.CODE],
            has_git_clone=False,
            collect_metadata=False
        )
        
        assert steps == 4
    
    def test_get_total_steps_with_conditions(self, clean_registry):
        """Test calculating steps with conditional scanners."""
        capability = ScannerCapability(
            scan_type=ScanType.CODE,
            supported_targets=[TargetType.GIT_REPO],
            supported_artifacts=[]
        )
        
        conditional_scanner = Scanner(
            name="ConditionalScanner",
            capabilities=[capability],
            enabled=True,
            requires_condition="IS_NATIVE"
        )
        
        ScannerRegistry.register(conditional_scanner)
        
        # Without condition - should not count scanner
        steps = ScannerRegistry.get_total_steps(
            target_type=TargetType.GIT_REPO,
            scan_types=[ScanType.CODE],
            has_git_clone=False,
            collect_metadata=False,
            conditions=None
        )
        assert steps == 4
        
        steps = ScannerRegistry.get_total_steps(
            target_type=TargetType.GIT_REPO,
            scan_types=[ScanType.CODE],
            has_git_clone=False,
            collect_metadata=False,
            conditions={"IS_NATIVE": True}
        )
        assert steps == 5


# ============================================================================
# Tests for ScannerRegistry.get_all_scanners()
# ============================================================================

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
    
    def test_get_all_scanners_includes_disabled(self, clean_registry):
        """Test that get_all_scanners includes disabled scanners."""
        enabled_scanner = Scanner(
            name="Enabled",
            capabilities=[],
            enabled=True
        )
        disabled_scanner = Scanner(
            name="Disabled",
            capabilities=[],
            enabled=False
        )
        
        ScannerRegistry.register(enabled_scanner)
        ScannerRegistry.register(disabled_scanner)
        
        scanners = ScannerRegistry.get_all_scanners()
        assert len(scanners) == 2


# ============================================================================
# Tests for ScannerRegistry.get_scanner()
# ============================================================================

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


# ============================================================================
# Tests for ScannerRegistry.register_from_class()
# ============================================================================

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
    
    def test_register_from_class_plugin_name_transformation(self, clean_registry):
        """Test plugin module path -> display name transformation (e.g. BanditScanner from plugins.bandit)."""
        class BanditScanner:
            CAPABILITIES = []
            PRIORITY = 0
            SCRIPT_PATH = "/app/test.sh"
            __name__ = "BanditScanner"
            __module__ = "scanner.plugins.bandit.scanner"
        
        ScannerRegistry.register_from_class(BanditScanner)
        
        scanner = ScannerRegistry.get_scanner("Bandit")
        assert scanner is not None
    
    @patch('scanner.core.scanner_assets.manager.ScannerAssetsManager')
    @patch('scanner.core.scanner_registry.Path')
    def test_register_from_class_with_manifest(self, mock_path_class, mock_assets_manager_class, clean_registry):
        """Test registering with manifest.yaml name."""
        # Mock manifest loading
        mock_manifest = MagicMock()
        mock_manifest.id = "test"
        mock_manifest.display_name = "ManifestScanner"
        
        mock_assets_manager_instance = MagicMock()
        mock_assets_manager_instance.get_manifest.return_value = mock_manifest
        mock_assets_manager_class.return_value = mock_assets_manager_instance
        
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_class.return_value = mock_path_instance
        
        class TestScannerClass:
            CAPABILITIES = []
            PRIORITY = 0
            SCRIPT_PATH = "/app/test.sh"
            __name__ = "TestScannerClass"
            __module__ = "scanner.plugins.test.scanner"
        
        ScannerRegistry.register_from_class(TestScannerClass)
        
        scanner = ScannerRegistry.get_scanner("ManifestScanner")
        assert scanner is not None
    
    @patch('scanner.core.scanner_assets.manager.ScannerAssetsManager')
    @patch('scanner.core.scanner_registry.Path')
    def test_register_from_class_manifest_loading_failure(self, mock_path_class, mock_assets_manager_class, clean_registry):
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_class.return_value = mock_path_instance
        mock_assets_manager_class.side_effect = Exception("Manifest load failed")

        class TestScannerClass:
            CAPABILITIES = []
            PRIORITY = 0
            SCRIPT_PATH = "/app/test.sh"
            __name__ = "TestScannerClass"
            __module__ = "scanner.plugins.test.scanner"

        with pytest.raises(RuntimeError, match="manifest"):
            ScannerRegistry.register_from_class(TestScannerClass)
    
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
            __module__ = "scanner.plugins.test.scanner"
        
        ScannerRegistry.register_from_class(ConditionalScannerClass)
        
        scanner = ScannerRegistry.get_scanner("ConditionalScanner")
        assert scanner.requires_condition == "IS_NATIVE"
    
    def test_register_from_class_sets_python_class(self, clean_registry):
        """Test register_from_class sets python_class from module."""
        class TestScannerClass:
            SCANNER_NAME = "TestScanner"
            CAPABILITIES = []
            PRIORITY = 0
            __name__ = "TestScannerClass"
            __module__ = "scanner.plugins.test.scanner"
        
        ScannerRegistry.register_from_class(TestScannerClass)
        
        scanner = ScannerRegistry.get_scanner("TestScanner")
        assert scanner.python_class == "scanner.plugins.test.scanner.TestScannerClass" 
    
    def test_register_from_class_manifest_path_not_exists(self, clean_registry):
        """Plugin folder without manifest.yaml → RuntimeError."""
        class TestScannerClass:
            CAPABILITIES = []
            PRIORITY = 0
            SCRIPT_PATH = "/app/test.sh"
            __name__ = "TestScannerClass"
            __module__ = "scanner.plugins.nonexistent_plugin_xyz.scanner"

        with pytest.raises(RuntimeError, match="manifest"):
            ScannerRegistry.register_from_class(TestScannerClass)
    
    def test_register_from_class_non_plugin_module(self, clean_registry):
        class TestScannerClass:
            SCANNER_NAME = "TestScanner"
            CAPABILITIES = []
            PRIORITY = 0
            SCRIPT_PATH = "/app/test.sh"
            __name__ = "TestScannerClass"
            __module__ = "some.other.module"

        with pytest.raises(RuntimeError, match="manifest"):
            ScannerRegistry.register_from_class(TestScannerClass)


# ============================================================================
# Integration Tests
# ============================================================================

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
        
        assert steps == 6
    
    def test_complex_filtering_scenario(self, clean_registry):
        """Test complex filtering with multiple conditions."""
        # Create scanners with different configurations
        scanners_config = [
            {
                "name": "CodeScanner1",
                "scan_type": ScanType.CODE,
                "target": TargetType.GIT_REPO,
                "enabled": True,
                "priority": 1,
                "condition": None
            },
            {
                "name": "CodeScanner2",
                "scan_type": ScanType.CODE,
                "target": TargetType.GIT_REPO,
                "enabled": True,
                "priority": 0,
                "condition": "IS_NATIVE"
            },
            {
                "name": "SecretsScanner",
                "scan_type": ScanType.SECRETS,
                "target": TargetType.GIT_REPO,
                "enabled": True,
                "priority": 2,
                "condition": None
            },
            {
                "name": "DisabledScanner",
                "scan_type": ScanType.CODE,
                "target": TargetType.GIT_REPO,
                "enabled": False,
                "priority": 0,
                "condition": None
            }
        ]
        
        for config in scanners_config:
            capability = ScannerCapability(
                scan_type=config["scan_type"],
                supported_targets=[config["target"]],
                supported_artifacts=[]
            )
            scanner = Scanner(
                name=config["name"],
                capabilities=[capability],
                enabled=config["enabled"],
                priority=config["priority"],
                requires_condition=config["condition"]
            )
            ScannerRegistry.register(scanner)
        
        # Test 1: Get CODE scanners without condition
        scanners = ScannerRegistry.get_scanners_for_target(
            TargetType.GIT_REPO,
            scan_types=[ScanType.CODE]
        )
        assert len(scanners) == 1
        assert scanners[0].name == "CodeScanner1"
        
        # Test 2: Get CODE scanners with IS_NATIVE condition
        scanners = ScannerRegistry.get_scanners_for_target(
            TargetType.GIT_REPO,
            scan_types=[ScanType.CODE],
            conditions={"IS_NATIVE": True}
        )
        assert len(scanners) == 2
        assert scanners[0].name == "CodeScanner2"  # Lower priority first
        assert scanners[1].name == "CodeScanner1"
        
        # Test 3: Get SECRETS scanners
        scanners = ScannerRegistry.get_scanners_for_target(
            TargetType.GIT_REPO,
            scan_types=[ScanType.SECRETS]
        )
        assert len(scanners) == 1
        assert scanners[0].name == "SecretsScanner"