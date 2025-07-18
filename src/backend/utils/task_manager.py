"""
Task manager for background job handling.

Manages long-running background tasks such as fuzzing experiments,
providing status tracking and lifecycle management.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Optional, Callable, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task:
    """Represents a background task."""
    
    def __init__(self, task_id: str, name: str, func: Callable, *args, **kwargs):
        self.id = task_id
        self.name = name
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.status = TaskStatus.PENDING
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.result: Any = None
        self.error: Optional[str] = None
        self.progress: Optional[Dict[str, Any]] = None
        self._asyncio_task: Optional[asyncio.Task] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "progress": self.progress
        }


class TaskManager:
    """Manages background tasks and their lifecycle."""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.max_completed_tasks = 100  # Keep last 100 completed tasks
    
    def create_task(
        self, 
        name: str, 
        func: Callable, 
        *args, 
        task_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Create a new background task.
        
        Args:
            name: Task name/description
            func: Function to execute
            *args: Function arguments
            task_id: Optional custom task ID
            **kwargs: Function keyword arguments
            
        Returns:
            Task ID
        """
        if task_id is None:
            task_id = str(uuid.uuid4())
        
        task = Task(task_id, name, func, *args, **kwargs)
        self.tasks[task_id] = task
        
        logger.info(f"Created task {task_id}: {name}")
        return task_id
    
    async def start_task(self, task_id: str) -> bool:
        """
        Start a pending task.
        
        Args:
            task_id: Task ID
            
        Returns:
            True if started successfully, False otherwise
        """
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        if task.status != TaskStatus.PENDING:
            return False
        
        # Create and start asyncio task
        task._asyncio_task = asyncio.create_task(self._run_task(task))
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        
        logger.info(f"Started task {task_id}: {task.name}")
        return True
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.
        
        Args:
            task_id: Task ID
            
        Returns:
            True if cancelled successfully, False otherwise
        """
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        if task.status != TaskStatus.RUNNING or not task._asyncio_task:
            return False
        
        # Cancel the asyncio task
        task._asyncio_task.cancel()
        
        try:
            await task._asyncio_task
        except asyncio.CancelledError:
            pass
        
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.utcnow()
        task._asyncio_task = None
        
        logger.info(f"Cancelled task {task_id}: {task.name}")
        return True
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get task by ID.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task if found, None otherwise
        """
        return self.tasks.get(task_id)
    
    def list_tasks(self, status_filter: Optional[TaskStatus] = None) -> list[Task]:
        """
        List tasks with optional status filter.
        
        Args:
            status_filter: Optional status filter
            
        Returns:
            List of tasks
        """
        tasks = list(self.tasks.values())
        
        if status_filter:
            tasks = [t for t in tasks if t.status == status_filter]
        
        # Sort by created_at descending
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task status as dictionary.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task status dictionary if found, None otherwise
        """
        task = self.get_task(task_id)
        return task.to_dict() if task else None
    
    def update_task_progress(self, task_id: str, progress: Dict[str, Any]) -> bool:
        """
        Update task progress information.
        
        Args:
            task_id: Task ID
            progress: Progress data
            
        Returns:
            True if updated successfully, False otherwise
        """
        if task_id not in self.tasks:
            return False
        
        self.tasks[task_id].progress = progress
        return True
    
    def cleanup_completed_tasks(self):
        """Clean up old completed tasks to prevent memory leaks."""
        completed_tasks = [
            t for t in self.tasks.values() 
            if t.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
        ]
        
        if len(completed_tasks) > self.max_completed_tasks:
            # Sort by completion time and remove oldest
            completed_tasks.sort(key=lambda t: t.completed_at or datetime.min)
            tasks_to_remove = completed_tasks[:-self.max_completed_tasks]
            
            for task in tasks_to_remove:
                del self.tasks[task.id]
                logger.debug(f"Cleaned up old task {task.id}: {task.name}")
    
    async def _run_task(self, task: Task):
        """
        Run a task and handle its lifecycle.
        
        Args:
            task: Task to run
        """
        try:
            # Execute the task function
            if asyncio.iscoroutinefunction(task.func):
                result = await task.func(*task.args, **task.kwargs)
            else:
                # Run synchronous function in thread pool
                result = await asyncio.get_event_loop().run_in_executor(
                    None, task.func, *task.args, **task.kwargs
                )
            
            # Task completed successfully
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            task._asyncio_task = None
            
            logger.info(f"Completed task {task.id}: {task.name}")
            
        except asyncio.CancelledError:
            # Task was cancelled
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.utcnow()
            task._asyncio_task = None
            logger.info(f"Task cancelled {task.id}: {task.name}")
            raise
            
        except Exception as e:
            # Task failed
            task.error = str(e)
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.utcnow()
            task._asyncio_task = None
            
            logger.error(f"Task failed {task.id}: {task.name} - {e}")
        
        finally:
            # Clean up old tasks periodically
            self.cleanup_completed_tasks()


# Global task manager instance
_task_manager = None

def get_task_manager() -> TaskManager:
    """Get global task manager instance."""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager 