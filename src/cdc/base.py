"""Base classes and interfaces for Change Data Capture"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional


class ChangeOperation(Enum):
    """Types of database operations"""
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    TRUNCATE = "TRUNCATE"
    DDL = "DDL"  # Schema changes


@dataclass
class ChangeEvent:
    """
    Unified change event format across all databases
    
    This standardized format allows different database CDC implementations
    to produce events that can be processed uniformly.
    """
    operation: ChangeOperation
    table: str
    schema: str
    timestamp: datetime
    database_type: str
    
    old_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None
    
    primary_key: Optional[Dict[str, Any]] = None
    
    ddl_statement: Optional[str] = None
    
    transaction_id: Optional[str] = None
    lsn: Optional[str] = None
    position: Optional[str] = None
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        return (
            f"ChangeEvent({self.operation.value} on {self.schema}.{self.table} "
            f"at {self.timestamp})"
        )
    
    def get_identifier(self) -> str:
        """Get unique identifier for this change"""
        pk_str = str(self.primary_key) if self.primary_key else "unknown"
        return f"{self.schema}.{self.table}:{pk_str}:{self.timestamp.isoformat()}"


class CDCListener(ABC):
    """
    Abstract base class for database-specific CDC listeners
    
    Each database type (PostgreSQL, MySQL, etc.) implements this interface
    to provide CDC functionality in a database-specific way.
    """
    
    def __init__(self, connection_config: Dict[str, Any]):
        """
        Initialize CDC listener
        
        Args:
            connection_config: Database connection configuration
        """
        self.connection_config = connection_config
        self.is_running = False
        self.current_position: Optional[str] = None
    
    @abstractmethod
    def setup(self) -> None:
        """
        Set up CDC infrastructure (replication slots, triggers, etc.)
        
        This method should be idempotent - safe to call multiple times.
        """
        pass
    
    @abstractmethod
    def start_streaming(self, callback: Callable[[ChangeEvent], None]) -> None:
        """
        Start streaming changes from the database
        
        Args:
            callback: Function to call for each change event
        """
        pass
    
    @abstractmethod
    def stop_streaming(self) -> None:
        """Stop streaming changes"""
        pass
    
    @abstractmethod
    def get_current_position(self) -> Optional[str]:
        """
        Get current position in change stream
        
        Returns:
            Position marker (LSN, binlog position, etc.) or None
        """
        pass
    
    @abstractmethod
    def resume_from_position(self, position: str) -> None:
        """
        Resume streaming from a specific position
        
        Args:
            position: Position marker to resume from
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """
        Clean up CDC infrastructure (remove replication slots, etc.)
        
        Should be called when CDC is no longer needed.
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of CDC listener
        
        Returns:
            Status information including position, lag, etc.
        """
        pass


class CDCHandler(ABC):
    """
    Abstract base class for handling change events
    
    Implementations process change events and sync to target systems
    (Neo4j, vector store, etc.)
    """
    
    @abstractmethod
    def handle_change(self, event: ChangeEvent) -> None:
        """
        Process a change event
        
        Args:
            event: Change event to process
        """
        pass
    
    @abstractmethod
    def handle_batch(self, events: list[ChangeEvent]) -> None:
        """
        Process a batch of change events
        
        Args:
            events: List of change events to process
        """
        pass
    
    def can_handle(self, event: ChangeEvent) -> bool:
        """
        Check if this handler can process the given event
        
        Args:
            event: Change event to check
            
        Returns:
            True if this handler can process the event
        """
        return True


class CDCError(Exception):
    """Base exception for CDC-related errors"""
    pass


class CDCSetupError(CDCError):
    """Error during CDC setup"""
    pass


class CDCStreamError(CDCError):
    """Error during CDC streaming"""
    pass


class CDCPositionError(CDCError):
    """Error related to CDC position/resume"""
    pass

