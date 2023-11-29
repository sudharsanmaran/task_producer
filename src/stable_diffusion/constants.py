from enum import Enum


class Status(Enum):
    """Status of the image generation request"""

    PENDING = "pending"
    PROCESS = "process"
    COMPLETED = "completed"
    FAILED = "failed"
