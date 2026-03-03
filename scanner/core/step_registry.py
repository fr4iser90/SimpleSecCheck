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
        self.websocket_manager = websocket_manager
        self.steps: Dict[str, Step] = {}  # {step_name: Step}
        self.step_counter = 0
        self.lock = asyncio.Lock()
        
        # Use LOGS_DIR_IN_CONTAINER environment variable (NO FALLBACK!)
        logs_dir_env = os.getenv("LOGS_DIR_IN_CONTAINER")
        if not logs_dir_env:
            raise ValueError("LOGS_DIR_IN_CONTAINER environment variable is required but not set")
        self.logs_dir = Path(logs_dir_env)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.steps_log = self.logs_dir / "steps.log"
        
        # Initialize steps.log (JSON Lines format - one JSON object per line)
        if not self.steps_log.exists():
            with open(self.steps_log, "w", encoding="utf-8") as f:
                f.write(f'{{"init": "SimpleSecCheck Steps Log", "timestamp": "{datetime.now().isoformat()}"}}\n')
        else:
            # Read existing steps from log (e.g., Git Clone step written before orchestrator starts)
            self._load_existing_steps()
    
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
        log_line = f"⊘ Step {step.number}: {step.message}"
        self._write_to_log(log_line)
        
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
            step_dict = {
                "number": step.number,
                "name": step.name,
                "status": step.status.value,  # 'pending', 'running', 'completed', 'failed', 'skipped'
                "message": step.message,
                "started_at": step.started_at.isoformat() if step.started_at else None,
                "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                "timestamp": datetime.now().isoformat()
            }
            with open(self.steps_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(step_dict) + "\n")
        except Exception as e:
            print(f"[Step Registry] Error writing to steps.log: {e}")
    
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
