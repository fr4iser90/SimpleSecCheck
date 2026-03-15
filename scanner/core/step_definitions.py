"""
Step Definitions Registry
Similar to ScannerRegistry - defines all scan steps, not hardcoded in orchestrator!
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Callable
from abc import ABC, abstractmethod


class StepType(Enum):
    """Step type enumeration"""
    GIT_CLONE = "git_clone"
    INITIALIZATION = "initialization"
    SCANNER = "scanner"
    METADATA_COLLECTION = "metadata_collection"
    COMPLETION = "completion"


@dataclass
class StepDefinition:
    """Step definition - similar to Scanner definition"""
    name: str
    step_type: StepType
    enabled: bool = True
    priority: int = 0
    requires_target_type: Optional[List[str]] = None  # Only run for specific target types
    requires_condition: Optional[str] = None  # Optional condition (e.g., "collect_metadata")
    execute_func: Optional[Callable] = None  # Function to execute the step


class StepDefinitionsRegistry:
    """Central registry for all step definitions - dynamically extensible"""
    _steps: Dict[str, StepDefinition] = {}
    
    @classmethod
    def register(cls, step: StepDefinition):
        """Register a step definition"""
        cls._steps[step.name] = step
    
    @classmethod
    def get_steps_for_scan(
        cls,
        target_type: str,
        collect_metadata: bool,
        scanner_count: int
    ) -> List[StepDefinition]:
        """
        Get all enabled steps for a scan configuration.
        
        Args:
            target_type: Target type (e.g., "git_repo", "local_mount")
            collect_metadata: Whether metadata collection is enabled
            scanner_count: Number of scanners that will run
        
        Returns:
            List of step definitions in execution order
        """
        steps = []
        
        for step in cls._steps.values():
            if not step.enabled:
                continue
            
            # Check if step requires specific target type
            if step.requires_target_type:
                if target_type not in step.requires_target_type:
                    continue
            
            # Check if step requires condition
            if step.requires_condition:
                if step.requires_condition == "collect_metadata" and not collect_metadata:
                    continue
            
            steps.append(step)
        
        # Sort by priority
        return sorted(steps, key=lambda s: s.priority)
    
    @classmethod
    def get_total_steps(
        cls,
        target_type: str,
        collect_metadata: bool,
        scanner_count: int
    ) -> int:
        """Calculate total number of steps for a scan"""
        steps = cls.get_steps_for_scan(target_type, collect_metadata, scanner_count)
        return len(steps) + scanner_count  # Add scanner steps
    
    @classmethod
    def get_all_steps(cls) -> List[StepDefinition]:
        """Get all registered step definitions"""
        return list(cls._steps.values())
    
    @classmethod
    def get_step(cls, name: str) -> Optional[StepDefinition]:
        """Get a specific step definition by name"""
        return cls._steps.get(name)


# Register default steps
def register_default_steps():
    """Register default step definitions"""
    
    # Git Clone Step - only for git_repo
    StepDefinitionsRegistry.register(StepDefinition(
        name="Git Clone",
        step_type=StepType.GIT_CLONE,
        priority=1,
        requires_target_type=["git_repo"]
    ))
    
    # Initialization Step - always runs
    StepDefinitionsRegistry.register(StepDefinition(
        name="Initialization",
        step_type=StepType.INITIALIZATION,
        priority=2
    ))
    
    # Metadata Collection Step - only if enabled
    StepDefinitionsRegistry.register(StepDefinition(
        name="Metadata Collection",
        step_type=StepType.METADATA_COLLECTION,
        priority=100,  # After scanners
        requires_condition="collect_metadata"
    ))
    
    # Completion Step - always runs last
    StepDefinitionsRegistry.register(StepDefinition(
        name="Completion",
        step_type=StepType.COMPLETION,
        priority=1000  # Always last
    ))


# Auto-register on import
register_default_steps()
