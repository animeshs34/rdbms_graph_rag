"""Base database connector interface"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class TableSchema:
    """Represents a database table schema"""
    name: str
    columns: List[Dict[str, Any]]
    primary_keys: List[str]
    foreign_keys: List[Dict[str, Any]]
    indexes: List[Dict[str, Any]]
    row_count: Optional[int] = None


@dataclass
class ColumnInfo:
    """Represents a database column"""
    name: str
    data_type: str
    nullable: bool
    default: Optional[Any] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_key_ref: Optional[Dict[str, str]] = None


class DatabaseConnector(ABC):
    """Abstract base class for database connectors"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.connection = None
    
    @abstractmethod
    def connect(self) -> None:
        """Establish database connection"""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close database connection"""
        pass
    
    @abstractmethod
    def get_tables(self) -> List[str]:
        """Get list of all tables in the database"""
        pass
    
    @abstractmethod
    def get_table_schema(self, table_name: str) -> TableSchema:
        """Get schema information for a specific table"""
        pass
    
    @abstractmethod
    def get_all_schemas(self) -> Dict[str, TableSchema]:
        """Get schema information for all tables"""
        pass
    
    @abstractmethod
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results"""
        pass
    
    @abstractmethod
    def get_sample_data(self, table_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get sample data from a table"""
        pass
    
    @abstractmethod
    def get_row_count(self, table_name: str) -> int:
        """Get total row count for a table"""
        pass
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()

