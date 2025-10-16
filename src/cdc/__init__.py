"""Change Data Capture (CDC) module for real-time database synchronization"""

from .base import CDCListener, ChangeEvent, ChangeOperation
from .manager import CDCManager
from .postgres_listener import PostgreSQLCDCListener

__all__ = [
    "CDCListener",
    "ChangeEvent", 
    "ChangeOperation",
    "CDCManager",
    "PostgreSQLCDCListener"
]

