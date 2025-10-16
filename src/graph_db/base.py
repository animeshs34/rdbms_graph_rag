"""Base graph database connector interface"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class GraphDatabaseConnector(ABC):
    """Abstract base class for graph database connectors"""
    
    def __init__(self, connection_config: Dict[str, Any]):
        self.connection_config = connection_config
        self.connection = None
    
    @abstractmethod
    def connect(self) -> None:
        """Establish connection to graph database"""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to graph database"""
        pass
    
    @abstractmethod
    def create_node(self, label: str, properties: Dict[str, Any]) -> Any:
        """Create a node in the graph"""
        pass
    
    @abstractmethod
    def create_relationship(
        self, 
        from_node_id: Any, 
        to_node_id: Any, 
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Create a relationship between two nodes"""
        pass
    
    @abstractmethod
    def batch_create_nodes(self, label: str, nodes: List[Dict[str, Any]]) -> List[Any]:
        """Create multiple nodes in batch"""
        pass
    
    @abstractmethod
    def batch_create_relationships(
        self,
        relationships: List[Dict[str, Any]]
    ) -> List[Any]:
        """Create multiple relationships in batch"""
        pass
    
    @abstractmethod
    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a query and return results"""
        pass
    
    @abstractmethod
    def create_index(self, label: str, property_name: str) -> None:
        """Create an index on a node property"""
        pass
    
    @abstractmethod
    def create_constraint(self, label: str, property_name: str, constraint_type: str = "unique") -> None:
        """Create a constraint on a node property"""
        pass
    
    @abstractmethod
    def clear_database(self) -> None:
        """Clear all data from the database (use with caution!)"""
        pass
    
    @abstractmethod
    def get_node_count(self, label: Optional[str] = None) -> int:
        """Get count of nodes, optionally filtered by label"""
        pass
    
    @abstractmethod
    def get_relationship_count(self, relationship_type: Optional[str] = None) -> int:
        """Get count of relationships, optionally filtered by type"""
        pass
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()

