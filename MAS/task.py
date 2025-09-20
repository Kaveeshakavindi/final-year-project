import time
from taskStatus import TaskStatus
from dataclasses import dataclass
from typing import Optional

@dataclass
class Task:
    id: str
    type: str
    prompt: str
    model: str = "llama2"
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: float = None
    completed_at: Optional[float] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()