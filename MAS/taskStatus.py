from enum import Enum

class TaskStatus(Enum):
    """Task status types"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"