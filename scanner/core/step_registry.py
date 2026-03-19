"""
Step Registry
Direct step communication - no log parsing!
Modern approach: Steps register themselves and communicate directly via WebSocket
"""
import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum


class StepStatus(Enum):
    """Step status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SubStepType(Enum):
    """Substep type enumeration for UI categorization"""
    PHASE = "phase"  # Large workflow steps (e.g., "Scanning Dependencies", "Scanning Secrets")
    ACTION = "action"  # Technical actions (e.g., "Loading Rules", "Parsing Files")
    OUTPUT = "output"  # Report/artifact generation (e.g., "Generating JSON Report")


def _utc_now() -> datetime:
    """Current instant in UTC (timezone-aware)."""
    return datetime.now(timezone.utc)


def _step_time_to_iso_z(dt: Optional[datetime]) -> Optional[str]:
    """Serialize step time as ISO-8601 UTC ending with Z (unambiguous for UI/API)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def _parse_log_time(s: Optional[str]) -> Optional[datetime]:
    """Parse timestamps from steps.log; naive strings are treated as UTC."""
    if not s:
        return None
    s = str(s).strip()
    if s.endswith("Z") or s.endswith("z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except (ValueError, AttributeError):
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _to_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """PostgreSQL timestamp without time zone: store UTC wall time."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _substep_type_value(substep) -> str:
    """Return JSON-serializable string for substep type (never pass Enum to json.dumps)."""
    st = getattr(substep, "substep_type", None)
    if st is not None and hasattr(st, "value"):
        v = st.value
        return v if isinstance(v, str) else str(v)
    return "action"


def _json_serializable(obj: Any) -> Any:
    """Convert enums/datetimes to JSON-serializable values; recurse into dicts/lists."""
    if isinstance(obj, Enum):
        return obj.value if isinstance(obj.value, (str, int, float, bool, type(None))) else str(obj.value)
    if isinstance(obj, datetime):
        return _step_time_to_iso_z(obj)
    if hasattr(obj, "isoformat") and callable(getattr(obj, "isoformat")):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_serializable(v) for v in obj]
    return obj


@dataclass
class SubStep:
    """Sub-step definition (nested within a main step)"""
    name: str
    status: StepStatus = StepStatus.PENDING
    message: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    substep_type: SubStepType = SubStepType.ACTION  # Default to ACTION


@dataclass
class Step:
    """Step definition"""
    number: int
    name: str
    status: StepStatus = StepStatus.PENDING
    message: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    substeps: List[SubStep] = field(default_factory=list)
    timeout_seconds: Optional[int] = None  # Max duration from manifest (for scanner steps)


class StepRegistry:
    """
    Modern step registry - direct communication, no log parsing!
    Steps register themselves and send updates directly via WebSocket
    """
    
    def __init__(self, scan_id: str, results_dir: Path, websocket_manager=None):
        """
        Initialize step registry
        
        Args:
            scan_id: Scan identifier (timestamp format)
            results_dir: Path to scan results directory
            websocket_manager: Optional WebSocket manager for real-time updates
        """
        self.scan_id = scan_id
        self.results_dir = results_dir
        
        # CRITICAL: Validate that results_dir contains scan_id
        # This ensures we never write to /app/results/logs/ directly
        # Results directory MUST be /app/results/{scan_id}/
        if not scan_id or scan_id not in str(results_dir):
            raise ValueError(
                f"CRITICAL: results_dir must contain scan_id! "
                f"scan_id={scan_id}, results_dir={results_dir}. "
                f"This prevents writing to /app/results/logs/ directly. "
                f"Results directory structure must be: /app/results/{{scan_id}}/logs/steps.log"
            )
        
        self.websocket_manager = websocket_manager
        self.steps: Dict[str, Step] = {}  # {step_name: Step}
        self.step_counter = 0
        
        # CRITICAL: Always create logs inside scan-specific directory
        # Structure: /app/results/{scan_id}/logs/steps.log
        self.logs_dir = self.results_dir / "logs"
        self._debug = os.environ.get("STEP_REGISTRY_DEBUG", "").strip().lower() in ("1", "true", "yes")

        if self._debug:
            print(f"[Step Registry] Initializing: scan_id={scan_id}, results_dir={self.results_dir}")

        # Create directories
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.steps_log = self.logs_dir / "steps.log"

        # Optional DB mirror when POSTGRES_* is set (built URL; no DATABASE_URL env)
        from scanner.config.db_url import database_url_from_postgres_env

        self.database_url = database_url_from_postgres_env()
        self._db_pool = None
        
        # Initialize steps.log (JSON Lines format - one JSON object per line)
        if not self.steps_log.exists():
            with open(self.steps_log, "w", encoding="utf-8") as f:
                f.write(
                    f'{{"init": "SimpleSecCheck Steps Log", "timestamp": "{_step_time_to_iso_z(_utc_now())}"}}\n'
                )
        else:
            # Read existing steps from log (e.g., Git Clone step written before orchestrator starts)
            self._load_existing_steps()

    async def _ensure_db_pool(self):
        if not self.database_url:
            return None
        if self._db_pool is None:
            try:
                import asyncpg
                from scanner.config.db_url import asyncpg_connect_kwargs

                self._db_pool = await asyncpg.create_pool(
                    self.database_url, min_size=1, max_size=4, **asyncpg_connect_kwargs()
                )
            except Exception as e:
                print(f"[Step Registry] DB pool init failed: {e}")
                self._db_pool = None
        return self._db_pool
    
    def start_step(self, step_name: str, message: str = "") -> int:
        """
        Start a step and return its number
        
        Args:
            step_name: Name of the step (e.g., "Semgrep", "Initialization")
            message: Optional message for the step
        
        Returns:
            Step number
        """
        if step_name not in self.steps:
            self.step_counter += 1
            self.steps[step_name] = Step(
                number=self.step_counter,
                name=step_name,
                status=StepStatus.RUNNING,
                message=message or f"Running {step_name}...",
                started_at=_utc_now(),
            )
        
        step = self.steps[step_name]
        step.status = StepStatus.RUNNING
        step.started_at = _utc_now()
        
        # Write to steps.log (structured JSON format)
        self._write_to_log(step)
        
        # Send WebSocket update
        asyncio.create_task(self._send_update())
        
        return step.number
    
    def complete_step(self, step_name: str, message: str = ""):
        """
        Mark a step as completed
        
        Args:
            step_name: Name of the step
            message: Optional completion message
        """
        if step_name not in self.steps:
            # Step wasn't started, start it first
            self.start_step(step_name, message)
        
        step = self.steps[step_name]
        step.status = StepStatus.COMPLETED
        step.completed_at = _utc_now()
        if message:
            step.message = message
        
        # Write to steps.log (structured JSON format)
        self._write_to_log(step)
        
        # Send WebSocket update
        asyncio.create_task(self._send_update())
    
    def fail_step(self, step_name: str, message: str = ""):
        """
        Mark a step as failed
        
        Args:
            step_name: Name of the step
            message: Optional error message
        """
        if step_name not in self.steps:
            # Step wasn't started, start it first
            self.start_step(step_name, message)
        
        step = self.steps[step_name]
        step.status = StepStatus.FAILED
        step.completed_at = _utc_now()
        if message:
            step.message = message
        
        # Write to steps.log (structured JSON format)
        self._write_to_log(step)
        
        # Send WebSocket update
        asyncio.create_task(self._send_update())
    
    def skip_step(self, step_name: str, reason: str = ""):
        """
        Mark a step as skipped
        
        Args:
            step_name: Name of the step
            reason: Optional reason for skipping
        """
        if step_name not in self.steps:
            self.step_counter += 1
            self.steps[step_name] = Step(
                number=self.step_counter,
                name=step_name,
                status=StepStatus.SKIPPED,
                message=reason or f"{step_name} skipped",
                started_at=_utc_now(),
                completed_at=_utc_now(),
            )
        else:
            step = self.steps[step_name]
            step.status = StepStatus.SKIPPED
            step.completed_at = _utc_now()
            if reason:
                step.message = reason
        
        # Write to steps.log
        step = self.steps[step_name]
        self._write_to_log(step)
        
        # Send WebSocket update
        asyncio.create_task(self._send_update())

    def set_step_pending_for_run(self, step_name: str) -> None:
        """Clear step to pending for a new container run (DB/log). Skips admin-disabled (SKIPPED)."""
        if step_name not in self.steps:
            return
        st = self.steps[step_name]
        if st.status == StepStatus.SKIPPED:
            return
        st.status = StepStatus.PENDING
        st.message = f"{step_name}... (pending)"
        st.started_at = None
        st.completed_at = None
        st.substeps = []
        self._write_to_log(st)

    def apply_checkpoint_restored_step(self, step_name: str, skip_reason: str = "") -> None:
        """Mark scanner step completed from checkpoint (single write, DB + log)."""
        now = _utc_now()
        if step_name not in self.steps:
            return
        st = self.steps[step_name]
        st.status = StepStatus.COMPLETED
        st.started_at = now
        st.completed_at = now
        st.substeps = []
        msg = "Restored from checkpoint (artifact + config verified)"
        if skip_reason and skip_reason != "ok":
            msg = f"{msg} ({skip_reason})"
        st.message = msg
        self._write_to_log(st)
    
    def get_steps_for_frontend(self) -> List[dict]:
        """
        Get steps formatted for frontend

        Returns:
            List of step dictionaries
        """
        steps_list = []
        for step in sorted(self.steps.values(), key=lambda s: s.number):
            duration_seconds = None
            if step.started_at and step.completed_at:
                sa, sc = step.started_at, step.completed_at
                if sa.tzinfo is None:
                    sa = sa.replace(tzinfo=timezone.utc)
                if sc.tzinfo is None:
                    sc = sc.replace(tzinfo=timezone.utc)
                delta = (sc - sa).total_seconds()
                duration_seconds = max(0, int(delta))
            elif step.started_at and step.status == StepStatus.RUNNING:
                sa = step.started_at
                if sa.tzinfo is None:
                    sa = sa.replace(tzinfo=timezone.utc)
                delta = (_utc_now() - sa).total_seconds()
                duration_seconds = max(0, int(delta))
            step_dict = {
                "number": step.number,
                "name": step.name,
                "status": step.status.value,
                "message": step.message,
                "started_at": _step_time_to_iso_z(step.started_at),
                "substeps": [
                    {
                        "name": substep.name,
                        "status": substep.status.value,
                        "message": substep.message,
                        "started_at": _step_time_to_iso_z(substep.started_at),
                        "completed_at": _step_time_to_iso_z(substep.completed_at),
                    }
                    for substep in step.substeps
                ],
                "duration_seconds": duration_seconds,
                "timeout_seconds": getattr(step, "timeout_seconds", None),
            }
            steps_list.append(step_dict)
        return steps_list
    
    def get_total_steps(self) -> int:
        """Get total number of registered steps"""
        return self.step_counter
    
    def get_progress_percentage(self) -> int:
        """
        Calculate progress percentage based on step statuses
        
        Returns:
            Progress percentage (0-100)
        """
        total_steps = self.get_total_steps()
        if total_steps == 0:
            return 0
        
        completed = sum(1 for step in self.steps.values() if step.status == StepStatus.COMPLETED)
        running = sum(1 for step in self.steps.values() if step.status == StepStatus.RUNNING)
        failed = sum(1 for step in self.steps.values() if step.status == StepStatus.FAILED)
        
        # Progress = (completed + failed + (running * 0.5)) / total_steps
        # Running step counts as 50% progress
        progress = (completed + failed + (running * 0.5)) / total_steps
        
        return round(progress * 100)
    
    def get_step(self, step_name: str) -> Optional[Step]:
        """Get a step by name"""
        return self.steps.get(step_name)
    
    def start_substep(self, step_name: str, substep_name: str, message: str = "", substep_type: SubStepType = SubStepType.ACTION):
        """
        Start a substep within a main step
        
        Args:
            step_name: Name of the parent step
            substep_name: Name of the substep
            message: Optional message for the substep
            substep_type: Type of substep (PHASE, ACTION, OUTPUT)
        """
        if step_name not in self.steps:
            # Parent step doesn't exist, create it first
            self.start_step(step_name, f"Running {step_name}...")
        
        step = self.steps[step_name]
        
        # Check if substep already exists
        existing_substep = None
        for substep in step.substeps:
            if substep.name == substep_name:
                existing_substep = substep
                break
        
        if existing_substep:
            # Update existing substep
            existing_substep.status = StepStatus.RUNNING
            existing_substep.started_at = _utc_now()
            existing_substep.substep_type = substep_type
            if message:
                existing_substep.message = message
        else:
            # Create new substep
            new_substep = SubStep(
                name=substep_name,
                status=StepStatus.RUNNING,
                message=message or f"Running {substep_name}...",
                started_at=_utc_now(),
                substep_type=substep_type,
            )
            step.substeps.append(new_substep)
        
        # Write to log
        self._write_to_log(step)
        
        # Send WebSocket update
        asyncio.create_task(self._send_update())
    
    def complete_substep(self, step_name: str, substep_name: str, message: str = ""):
        """
        Mark a substep as completed
        
        Args:
            step_name: Name of the parent step
            substep_name: Name of the substep
            message: Optional completion message
        """
        if step_name not in self.steps:
            return
        
        step = self.steps[step_name]
        
        # Find substep
        for substep in step.substeps:
            if substep.name == substep_name:
                substep.status = StepStatus.COMPLETED
                substep.completed_at = _utc_now()
                if message:
                    substep.message = message
                break
        
        # Write to log
        self._write_to_log(step)
        
        # Send WebSocket update
        asyncio.create_task(self._send_update())
    
    def fail_substep(self, step_name: str, substep_name: str, message: str = ""):
        """
        Mark a substep as failed
        
        Args:
            step_name: Name of the parent step
            substep_name: Name of the substep
            message: Optional error message
        """
        if step_name not in self.steps:
            return
        
        step = self.steps[step_name]
        
        # Find substep
        for substep in step.substeps:
            if substep.name == substep_name:
                substep.status = StepStatus.FAILED
                substep.completed_at = _utc_now()
                if message:
                    substep.message = message
                break
        
        # Write to log
        self._write_to_log(step)
        
        # Send WebSocket update
        asyncio.create_task(self._send_update())
    
    def update_substep(self, step_name: str, substep_name: str, message: str = ""):
        """
        Update a substep message (status remains unchanged)
        
        Args:
            step_name: Name of the parent step
            substep_name: Name of the substep
            message: New message
        """
        if step_name not in self.steps:
            return
        
        step = self.steps[step_name]
        
        # Find substep
        for substep in step.substeps:
            if substep.name == substep_name:
                if message:
                    substep.message = message
                break
        
        # Write to log
        self._write_to_log(step)
        
        # Send WebSocket update
        asyncio.create_task(self._send_update())
    
    def _load_existing_steps(self):
        """Load existing steps from steps.log (JSON Lines format - no regex parsing!)"""
        import json
        try:
            with open(self.steps_log, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        # Parse JSON line (structured format - no regex needed!)
                        step_data = json.loads(line)
                        
                        # Skip init line
                        if "init" in step_data:
                            continue
                        
                        # Extract step data
                        step_number = step_data.get("number")
                        step_name = step_data.get("name")
                        status_str = step_data.get("status", "pending")
                        message = step_data.get("message", "")
                        started_at_str = step_data.get("started_at")
                        completed_at_str = step_data.get("completed_at")
                        
                        if not step_number or not step_name:
                            continue
                        
                        # Convert status string to enum
                        status_map = {
                            "pending": StepStatus.PENDING,
                            "running": StepStatus.RUNNING,
                            "completed": StepStatus.COMPLETED,
                            "failed": StepStatus.FAILED,
                            "skipped": StepStatus.SKIPPED
                        }
                        status = status_map.get(status_str, StepStatus.PENDING)
                        
                        # Parse timestamps
                        started_at = None
                        completed_at = None
                        if started_at_str:
                            started_at = _parse_log_time(started_at_str)
                        if completed_at_str:
                            completed_at = _parse_log_time(completed_at_str)
                        
                        # Load substeps if present
                        substeps = []
                        substeps_data = step_data.get("substeps", [])
                        for substep_data in substeps_data:
                            substep_status_str = substep_data.get("status", "pending")
                            substep_status = status_map.get(substep_status_str, StepStatus.PENDING)
                            substep_started_at = None
                            substep_completed_at = None
                            if substep_data.get("started_at"):
                                substep_started_at = _parse_log_time(substep_data["started_at"])
                            if substep_data.get("completed_at"):
                                substep_completed_at = _parse_log_time(substep_data["completed_at"])
                            substep_type_str = substep_data.get("type", "action")
                            substep_type = SubStepType.ACTION  # Default
                            try:
                                substep_type = SubStepType(substep_type_str)
                            except ValueError:
                                pass
                            
                            substeps.append(SubStep(
                                name=substep_data.get("name", ""),
                                status=substep_status,
                                message=substep_data.get("message", ""),
                                started_at=substep_started_at,
                                completed_at=substep_completed_at,
                                substep_type=substep_type
                            ))
                        
                        timeout_seconds = step_data.get("timeout_seconds")
                        if timeout_seconds is not None and not isinstance(timeout_seconds, int):
                            try:
                                timeout_seconds = int(timeout_seconds)
                            except (ValueError, TypeError):
                                timeout_seconds = None
                        # Register step if not already registered
                        if step_name not in self.steps:
                            self.steps[step_name] = Step(
                                number=step_number,
                                name=step_name,
                                status=status,
                                message=message,
                                started_at=started_at,
                                completed_at=completed_at,
                                substeps=substeps,
                                timeout_seconds=timeout_seconds,
                            )
                            # Update step_counter to highest step number
                            if step_number > self.step_counter:
                                self.step_counter = step_number
                        else:
                            # Update existing step with latest substeps
                            self.steps[step_name].substeps = substeps
                    except json.JSONDecodeError:
                        # Skip invalid JSON lines (e.g., old format lines)
                        continue
        except Exception as e:
            print(f"[Step Registry] Error loading existing steps: {e}")
    
    def _write_to_log(self, step: Step):
        """Write step as JSON line to steps.log file (structured format, no parsing needed!)"""
        try:
            import json
            import os
            
            # Ensure directory exists
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            
            step_dict = {
                "number": step.number,
                "name": step.name,
                "status": step.status.value,
                "message": step.message,
                "started_at": _step_time_to_iso_z(step.started_at),
                "completed_at": _step_time_to_iso_z(step.completed_at),
                "substeps": [
                    {
                        "name": substep.name,
                        "status": substep.status.value,
                        "message": substep.message,
                        "started_at": _step_time_to_iso_z(substep.started_at),
                        "completed_at": _step_time_to_iso_z(substep.completed_at),
                        "type": _substep_type_value(substep),
                    }
                    for substep in step.substeps
                ],
                "timestamp": _step_time_to_iso_z(_utc_now()),
                "timeout_seconds": getattr(step, "timeout_seconds", None),
            }
            step_dict = _json_serializable(step_dict)

            # Write to file
            with open(self.steps_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(step_dict) + "\n")
            if self._debug:
                print(f"[Step Registry] Wrote step {step.number} to {self.steps_log}")
        except Exception as e:
            print(f"[Step Registry] Error writing to steps.log: {e}")
            import traceback
            traceback.print_exc()

        # Mirror to DB when POSTGRES_* is set (non-blocking)
        if self.database_url:
            try:
                asyncio.create_task(self._upsert_step_db(step))
            except RuntimeError:
                # If no event loop, skip DB write
                pass

    async def _upsert_step_db(self, step: Step):
        pool = await self._ensure_db_pool()
        if not pool:
            return
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO scan_steps (
                        scan_id, step_number, step_name, status, message, started_at, completed_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                    ON CONFLICT (scan_id, step_number)
                    DO UPDATE SET
                        step_name = EXCLUDED.step_name,
                        status = EXCLUDED.status,
                        message = EXCLUDED.message,
                        started_at = COALESCE(EXCLUDED.started_at, scan_steps.started_at),
                        completed_at = COALESCE(EXCLUDED.completed_at, scan_steps.completed_at),
                        updated_at = NOW()
                    """,
                    self.scan_id,
                    step.number,
                    step.name,
                    step.status.value,
                    step.message,
                    _to_naive_utc(step.started_at),
                    _to_naive_utc(step.completed_at),
                )
        except Exception as e:
            print(f"[Step Registry] DB upsert failed: {e}")
    
    async def _send_update(self):
        """Send step update via WebSocket"""
        if not self.websocket_manager:
            return
        
        try:
            steps = self.get_steps_for_frontend()
            await self.websocket_manager.send_step_update(
                self.scan_id,
                {
                    "steps": steps,
                    "total_steps": self.get_total_steps(),
                    "progress_percentage": self.get_progress_percentage()
                }
            )
        except Exception as e:
            print(f"[Step Registry] Error sending WebSocket update: {e}")
