"""
Step Registry
Direct step communication - no log parsing!
Modern approach: Steps register themselves and communicate directly via WebSocket
"""
import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from enum import Enum


class StepStatus(Enum):
    """Step status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Step:
    """Step definition"""
    number: int
    name: str
    status: StepStatus = StepStatus.PENDING
    message: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


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
        # This keeps results/ clean - only contains {scan_id}/ folders
        self.logs_dir = self.results_dir / "logs"
        
        # DEBUG: Log directory creation
        print(f"[Step Registry] Initializing StepRegistry:")
        print(f"[Step Registry]   scan_id: {scan_id}")
        print(f"[Step Registry]   results_dir: {self.results_dir}")
        print(f"[Step Registry]   logs_dir: {self.logs_dir}")
        print(f"[Step Registry]   steps_log: {self.logs_dir / 'steps.log'}")
        print(f"[Step Registry]   results_dir exists: {self.results_dir.exists()}")
        
        # Create directories
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.steps_log = self.logs_dir / "steps.log"
        
        # DEBUG: Verify directories were created
        print(f"[Step Registry] After mkdir:")
        print(f"[Step Registry]   results_dir exists: {self.results_dir.exists()}")
        print(f"[Step Registry]   logs_dir exists: {self.logs_dir.exists()}")
        print(f"[Step Registry]   steps_log path: {self.steps_log}")

        # Production DB support (optional)
        self.environment = os.getenv("ENVIRONMENT", "dev").lower()
        self.database_url = os.getenv("DATABASE_URL")
        self._db_pool = None
        
        # Initialize steps.log (JSON Lines format - one JSON object per line)
        if not self.steps_log.exists():
            with open(self.steps_log, "w", encoding="utf-8") as f:
                f.write(f'{{"init": "SimpleSecCheck Steps Log", "timestamp": "{datetime.now().isoformat()}"}}\n')
        else:
            # Read existing steps from log (e.g., Git Clone step written before orchestrator starts)
            self._load_existing_steps()

    async def _ensure_db_pool(self):
        if self.environment != "prod" or not self.database_url:
            return None
        if self._db_pool is None:
            try:
                import asyncpg
                self._db_pool = await asyncpg.create_pool(self.database_url, min_size=1, max_size=4)
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
                started_at=datetime.now()
            )
        
        step = self.steps[step_name]
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now()
        
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
        step.completed_at = datetime.now()
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
        step.completed_at = datetime.now()
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
                started_at=datetime.now(),
                completed_at=datetime.now()
            )
        else:
            step = self.steps[step_name]
            step.status = StepStatus.SKIPPED
            step.completed_at = datetime.now()
            if reason:
                step.message = reason
        
        # Write to steps.log
        step = self.steps[step_name]
        self._write_to_log(step)
        
        # Send WebSocket update
        asyncio.create_task(self._send_update())
    
    def get_steps_for_frontend(self) -> List[dict]:
        """
        Get steps formatted for frontend
        
        Returns:
            List of step dictionaries
        """
        steps_list = []
        for step in sorted(self.steps.values(), key=lambda s: s.number):
            steps_list.append({
                "number": step.number,
                "name": step.name,
                "status": step.status.value,
                "message": step.message
            })
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
                            try:
                                started_at = datetime.fromisoformat(started_at_str)
                            except (ValueError, AttributeError):
                                pass
                        if completed_at_str:
                            try:
                                completed_at = datetime.fromisoformat(completed_at_str)
                            except (ValueError, AttributeError):
                                pass
                        
                        # Register step if not already registered
                        if step_name not in self.steps:
                            self.steps[step_name] = Step(
                                number=step_number,
                                name=step_name,
                                status=status,
                                message=message,
                                started_at=started_at,
                                completed_at=completed_at
                            )
                            # Update step_counter to highest step number
                            if step_number > self.step_counter:
                                self.step_counter = step_number
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
            
            # DEBUG: Log file path and directory existence
            print(f"[Step Registry] Writing step to: {self.steps_log}")
            print(f"[Step Registry] Logs directory exists: {self.logs_dir.exists()}")
            print(f"[Step Registry] Results directory exists: {self.results_dir.exists()}")
            print(f"[Step Registry] Steps log file exists: {self.steps_log.exists()}")
            
            # Ensure directory exists
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            
            step_dict = {
                "number": step.number,
                "name": step.name,
                "status": step.status.value,  # 'pending', 'running', 'completed', 'failed', 'skipped'
                "message": step.message,
                "started_at": step.started_at.isoformat() if step.started_at else None,
                "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                "timestamp": datetime.now().isoformat()
            }
            
            # Write to file
            with open(self.steps_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(step_dict) + "\n")
            
            # DEBUG: Verify file was written
            if self.steps_log.exists():
                file_size = os.path.getsize(self.steps_log)
                print(f"[Step Registry] Successfully wrote step to {self.steps_log} (size: {file_size} bytes)")
            else:
                print(f"[Step Registry] ERROR: File {self.steps_log} does not exist after write!")
                
        except Exception as e:
            print(f"[Step Registry] Error writing to steps.log: {e}")
            import traceback
            traceback.print_exc()

        # In prod, also write directly to DB (non-blocking)
        if self.environment == "prod" and self.database_url:
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
                    step.started_at,
                    step.completed_at,
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
