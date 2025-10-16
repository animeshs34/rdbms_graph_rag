"""AWS Neptune graph database connector"""

from typing import Any, Dict, List, Optional
import boto3
from gremlin_python.driver import client, serializer
from loguru import logger

from .base import GraphDatabaseConnector


class NeptuneConnector(GraphDatabaseConnector):
    """AWS Neptune database connector implementation using Gremlin"""
    
    def __init__(self, connection_config: Dict[str, Any]):
        super().__init__(connection_config)
        self.client = None
    
    def connect(self) -> None:
        """Establish connection to Neptune"""
        try:
            endpoint = self.connection_config.get("endpoint")
            port = self.connection_config.get("port", 8182)
            
            if not endpoint:
                logger.warning("Neptune endpoint not configured, skipping connection")
                return
            
            connection_url = f"wss://{endpoint}:{port}/gremlin"
            
            self.client = client.Client(
                connection_url,
                'g',
                message_serializer=serializer.GraphSONSerializersV2d0()
            )
            
            logger.info(f"Successfully connected to Neptune at {endpoint}")
        except Exception as e:
            logger.error(f"Failed to connect to Neptune: {e}")
            raise
    
    def disconnect(self) -> None:
        """Close connection to Neptune"""
        if self.client:
            self.client.close()
            logger.info("Neptune connection closed")
    
    def create_node(self, label: str, properties: Dict[str, Any]) -> Any:
        """Create a vertex in Neptune"""
        if not self.client:
            raise RuntimeError("Not connected to Neptune")
        
        query = f"g.addV('{label}')"
        for key, value in properties.items():
            query += f".property('{key}', '{value}')"
        query += ".id()"
        
        result = self.client.submit(query).all().result()
        return result[0] if result else None
    
    def create_relationship(
        self,
        from_node_id: Any,
        to_node_id: Any,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Create an edge between two vertices"""
        if not self.client:
            raise RuntimeError("Not connected to Neptune")
        
        query = f"g.V('{from_node_id}').addE('{relationship_type}').to(g.V('{to_node_id}'))"
        
        if properties:
            for key, value in properties.items():
                query += f".property('{key}', '{value}')"
        
        query += ".id()"
        
        result = self.client.submit(query).all().result()
        return result[0] if result else None
    
    def batch_create_nodes(self, label: str, nodes: List[Dict[str, Any]]) -> List[Any]:
        """Create multiple vertices in batch"""
        if not self.client:
            raise RuntimeError("Not connected to Neptune")
        
        node_ids = []
        for node in nodes:
            node_id = self.create_node(label, node)
            node_ids.append(node_id)
        
        return node_ids
    
    def batch_create_relationships(self, relationships: List[Dict[str, Any]]) -> List[Any]:
        """Create multiple edges in batch"""
        if not self.client:
            raise RuntimeError("Not connected to Neptune")
        
        rel_ids = []
        for rel in relationships:
            rel_id = self.create_relationship(
                rel["from_id"],
                rel["to_id"],
                rel["type"],
                rel.get("properties")
            )
            rel_ids.append(rel_id)
        
        return rel_ids
    
    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a Gremlin query and return results"""
        if not self.client:
            raise RuntimeError("Not connected to Neptune")
        
        result = self.client.submit(query, parameters or {}).all().result()
        return [{"result": r} for r in result]
    
    def create_index(self, label: str, property_name: str) -> None:
        """Create an index (Neptune handles this automatically)"""
        logger.info(f"Neptune automatically indexes properties: {label}.{property_name}")
    
    def create_constraint(self, label: str, property_name: str, constraint_type: str = "unique") -> None:
        """Create a constraint (limited support in Neptune)"""
        logger.warning(f"Neptune has limited constraint support: {label}.{property_name}")
    
    def clear_database(self) -> None:
        """Clear all data from the database"""
        if not self.client:
            raise RuntimeError("Not connected to Neptune")
        
        query = "g.V().drop()"
        self.client.submit(query).all().result()
        logger.warning("Cleared all data from Neptune database")
    
    def get_node_count(self, label: Optional[str] = None) -> int:
        """Get count of vertices"""
        if not self.client:
            raise RuntimeError("Not connected to Neptune")
        
        if label:
            query = f"g.V().hasLabel('{label}').count()"
        else:
            query = "g.V().count()"
        
        result = self.client.submit(query).all().result()
        return result[0] if result else 0
    
    def get_relationship_count(self, relationship_type: Optional[str] = None) -> int:
        """Get count of edges"""
        if not self.client:
            raise RuntimeError("Not connected to Neptune")
        
        if relationship_type:
            query = f"g.E().hasLabel('{relationship_type}').count()"
        else:
            query = "g.E().count()"
        
        result = self.client.submit(query).all().result()
        return result[0] if result else 0

