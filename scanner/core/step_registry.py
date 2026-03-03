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
        
        # Initialize steps.log (only if it doesn't exist - preserve Git Clone step if already written)
        if not self.steps_log.exists():
            with open(self.steps_log, "w", encoding="utf-8") as f:
                f.write(f"----- SimpleSecCheck Steps Log Initialized: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -----\n")
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
        """Load existing steps from steps.log (e.g., Git Clone step)"""
        import re
        try:
            with open(self.steps_log, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("-----"):
                        continue
                    
                    # Parse step line: "⏳ Step 1: Cloning Git repository..."
                    step_match = re.match(r'([⏳✓❌⊘]?)\s*Step\s+(\d+):\s*(.+)', line, re.IGNORECASE)
                    if step_match:
                        status_icon, step_num_str, message = step_match.groups()
                        step_number = int(step_num_str)
                        
                        # Extract step name from message
                        # Examples: "Cloning Git repository..." -> "Git Clone"
                        #           "Running Semgrep scan..." -> "Semgrep"
                        if "git" in message.lower() and "clone" in message.lower():
                            step_name = "Git Clone"
                        elif "initializ" in message.lower():
                            step_name = "Initialization"
                        elif "metadata" in message.lower():
                            step_name = "Metadata Collection"
                        elif "complet" in message.lower() and "scan" in message.lower():
                            step_name = "Completion"
                        else:
                            # Try to extract scanner name
                            name_match = re.match(r'^Running\s+(.+?)\s+scan', message, re.IGNORECASE)
                            if name_match:
                                step_name = name_match.group(1).strip()
                            else:
                                # Fallback: use first few words
                                words = message.split()[:2]
                                step_name = " ".join(words)
                        
                        # Determine status from icon
                        status = StepStatus.PENDING
                        if status_icon == '✓':
                            status = StepStatus.COMPLETED
                        elif status_icon == '⏳':
                            status = StepStatus.RUNNING
                        elif status_icon == '❌':
                            status = StepStatus.FAILED
                        elif status_icon == '⊘':
                            status = StepStatus.SKIPPED
                        
                        # Register step if not already registered
                        if step_name not in self.steps:
                            self.steps[step_name] = Step(
                                number=step_number,
                                name=step_name,
                                status=status,
                                message=message.strip(),
                                started_at=datetime.now() if status != StepStatus.PENDING else None,
                                completed_at=datetime.now() if status in [StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED] else None
                            )
                            # Update step_counter to highest step number
                            if step_number > self.step_counter:
                                self.step_counter = step_number
        except Exception as e:
            print(f"[Step Registry] Error loading existing steps: {e}")
    
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
                    "total_steps": self.get_total_steps(),
                    "progress_percentage": self.get_progress_percentage()
                }
            )
        except Exception as e:
            print(f"[Step Registry] Error sending WebSocket update: {e}")
