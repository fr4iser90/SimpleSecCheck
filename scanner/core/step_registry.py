"""
Step Registry
Direct step communication - no log parsing!
Modern approach: Steps register themselves and communicate directly via WebSocket
"""
import asyncio
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
        
        # Create logs directory
        self.logs_dir = results_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.steps_log = self.logs_dir / "steps.log"
        
        # Initialize steps.log
        with open(self.steps_log, "w", encoding="utf-8") as f:
            f.write(f"----- SimpleSecCheck Steps Log Initialized: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -----\n")
    
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
        
        # Write to steps.log
        log_line = f"⏳ Step {step.number}: {step.message}"
        self._write_to_log(log_line)
        
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
        
        # Write to steps.log
        log_line = f"✓ Step {step.number}: {step.message or f'{step_name} completed'}"
        self._write_to_log(log_line)
        
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
        
        # Write to steps.log
        log_line = f"❌ Step {step.number}: {step.message or f'{step_name} failed'}"
        self._write_to_log(log_line)
        
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
    
    def _write_to_log(self, line: str):
        """Write line to steps.log file"""
        try:
            with open(self.steps_log, "a", encoding="utf-8") as f:
                f.write(f"{line}\n")
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
                    "total_steps": self.get_total_steps()
                }
            )
        except Exception as e:
            print(f"[Step Registry] Error sending WebSocket update: {e}")
