# Step Registry Architecture - Current State & Problems

## Current Architecture (PROBLEMATIC)

```mermaid
graph TB
    subgraph "Step Registry (step_registry.py)"
        SR[StepRegistry]
        SR --> |manages| Steps[Step Objects]
        SR --> |writes| Log[steps.log JSON]
        SR --> |sends| WS[WebSocket Updates]
    end
    
    subgraph "Orchestrator (orchestrator.py) - HARDCODED STEPS!"
        OR[ScanOrchestrator]
        OR --> |hardcoded| GC[Git Clone Step<br/>if target_type == GIT_REPO]
        OR --> |hardcoded| INIT[Initialization Step]
        OR --> |hardcoded| METADATA[Metadata Collection Step]
        OR --> |hardcoded| COMP[Completion Step]
        OR --> |dynamic| SCANNERS[Scanner Steps<br/>from ScannerRegistry]
    end
    
    subgraph "Scanner Registry (scanner_registry.py)"
        SCR[ScannerRegistry]
        SCR --> |registers| S[Scanner Objects]
        SCR --> |provides| OR
    end
    
    OR --> |registers| SR
    SCR --> |provides scanners| OR
    
    style GC fill:#ff6b6b
    style INIT fill:#ff6b6b
    style METADATA fill:#ff6b6b
    style COMP fill:#ff6b6b
    style SCANNERS fill:#51cf66
```

## Problems

### 1. **Hardcoded Steps in Orchestrator**
- `Git Clone` - hardcoded in `_pre_register_all_steps()` and `_run_git_clone()` with `if self.target_type == TargetType.GIT_REPO`
- `Initialization` - hardcoded in `_pre_register_all_steps()` and `run_scan()`
- `Metadata Collection` - hardcoded in `_pre_register_all_steps()` and `_collect_metadata()`
- `Completion` - hardcoded in `_pre_register_all_steps()` and `run_scan()`

### 2. **No Step Registry System**
- Steps are NOT defined in a registry (like ScannerRegistry)
- Steps are hardcoded in Orchestrator logic
- Cannot dynamically add/remove steps
- Cannot reuse steps across different orchestrators

### 3. **Mixed Concerns**
- Orchestrator mixes:
  - Step definition (what steps exist)
  - Step execution (how to run steps)
  - Step tracking (registering with StepRegistry)

## Where Steps Are Defined

### Current State:
- **Git Clone**: `scanner/core/orchestrator.py` lines 459-500, 594-233
- **Initialization**: `scanner/core/orchestrator.py` lines 516-523, 598-601
- **Metadata Collection**: `scanner/core/orchestrator.py` lines 545-553, 400-449
- **Completion**: `scanner/core/orchestrator.py` lines 559-567, 625-636
- **Scanner Steps**: `scanner/core/scanner_registry.py` (dynamic, clean!)

### Step Registry:
- **File**: `scanner/core/step_registry.py`
- **Purpose**: Only tracks/manages Steps, does NOT define them
- **Methods**: `start_step()`, `complete_step()`, `fail_step()`, `skip_step()`

## ContainerSpec Issue

In `container_spec.py` line 218-219:
```python
# Add git branch if provided (only for git_repo)
if git_branch:
    environment["GIT_BRANCH"] = git_branch
```

**This is OK** - it's just setting an environment variable. The comment is misleading though - it's not checking `target_type`, just setting the env var if provided.

## Solution: Step Registry System

Steps should be defined in a registry (like ScannerRegistry):

```mermaid
graph TB
    subgraph "Step Registry System (NEW)"
        STEPREG[StepRegistry<br/>similar to ScannerRegistry]
        STEPREG --> |registers| STEPS[Step Definitions]
        STEPS --> GC_STEP[GitCloneStep]
        STEPS --> INIT_STEP[InitializationStep]
        STEPS --> METADATA_STEP[MetadataCollectionStep]
        STEPS --> COMP_STEP[CompletionStep]
    end
    
    subgraph "Orchestrator (CLEAN)"
        OR[ScanOrchestrator]
        OR --> |gets steps from| STEPREG
        OR --> |executes| STEPS
        OR --> |tracks| SR[StepRegistry<br/>tracking only]
    end
    
    STEPREG --> |provides steps| OR
    OR --> |registers execution| SR
    
    style STEPREG fill:#51cf66
    style OR fill:#51cf66
    style SR fill:#51cf66
```

## Files Structure

```
scanner/core/
├── step_registry.py          # Step tracking (current - OK)
├── step_definitions.py       # Step definitions (NEW - like ScannerRegistry)
├── steps/
│   ├── __init__.py
│   ├── git_clone_step.py     # GitCloneStep class
│   ├── initialization_step.py # InitializationStep class
│   ├── metadata_step.py       # MetadataCollectionStep class
│   └── completion_step.py     # CompletionStep class
└── orchestrator.py            # Only executes steps, doesn't define them
```
