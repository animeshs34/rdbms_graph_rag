"""Neo4j graph database connector"""

from typing import Any, Dict, List, Optional
from neo4j import GraphDatabase, Driver
from loguru import logger

from .base import GraphDatabaseConnector


class Neo4jConnector(GraphDatabaseConnector):
    """Neo4j database connector implementation"""
    
    def __init__(self, connection_config: Dict[str, Any]):
        super().__init__(connection_config)
        self.driver: Optional[Driver] = None
    
    def connect(self) -> None:
        """Establish connection to Neo4j"""
        try:
            uri = self.connection_config.get("uri", "bolt://localhost:7687")
            user = self.connection_config.get("user", "neo4j")
            password = self.connection_config.get("password", "neo4j")
            
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            logger.info(f"Successfully connected to Neo4j at {uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def disconnect(self) -> None:
        """Close connection to Neo4j"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")
    
    def create_node(self, label: str, properties: Dict[str, Any]) -> Any:
        """Create a node in Neo4j"""
        with self.driver.session() as session:
            query = f"CREATE (n:{label} $props) RETURN id(n) as node_id"
            result = session.run(query, props=properties)
            record = result.single()
            return record["node_id"] if record else None
    
    def create_relationship(
        self,
        from_node_id: Any,
        to_node_id: Any,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Create a relationship between two nodes"""
        with self.driver.session() as session:
            props_clause = "$props" if properties else "{}"
            query = f"""
                MATCH (a), (b)
                WHERE id(a) = $from_id AND id(b) = $to_id
                CREATE (a)-[r:{relationship_type} {props_clause}]->(b)
                RETURN id(r) as rel_id
            """
            params = {
                "from_id": from_node_id,
                "to_id": to_node_id
            }
            if properties:
                params["props"] = properties
            
            result = session.run(query, **params)
            record = result.single()
            return record["rel_id"] if record else None
    
    def batch_create_nodes(self, label: str, nodes: List[Dict[str, Any]]) -> List[Any]:
        """Create multiple nodes in batch"""
        with self.driver.session() as session:
            query = f"""
                UNWIND $nodes as node
                CREATE (n:{label})
                SET n = node
                RETURN id(n) as node_id
            """
            result = session.run(query, nodes=nodes)
            return [record["node_id"] for record in result]
    
    def batch_create_relationships(self, relationships: List[Dict[str, Any]]) -> List[Any]:
        """
        Create multiple relationships in batch
        
        Each relationship dict should have:
        - from_id: source node id
        - to_id: target node id
        - type: relationship type
        - properties: optional properties dict
        """
        with self.driver.session() as session:
            query = """
                UNWIND $rels as rel
                MATCH (a), (b)
                WHERE id(a) = rel.from_id AND id(b) = rel.to_id
                CALL apoc.create.relationship(a, rel.type, rel.properties, b) YIELD rel as r
                RETURN id(r) as rel_id
            """
            try:
                result = session.run(query, rels=relationships)
                return [record["rel_id"] for record in result]
            except Exception:
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
        """Execute a Cypher query and return results"""
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]
    
    def create_index(self, label: str, property_name: str) -> None:
        """Create an index on a node property"""
        with self.driver.session() as session:
            query = f"CREATE INDEX IF NOT EXISTS FOR (n:{label}) ON (n.{property_name})"
            session.run(query)
            logger.info(f"Created index on {label}.{property_name}")
    
    def create_constraint(self, label: str, property_name: str, constraint_type: str = "unique") -> None:
        """Create a constraint on a node property"""
        with self.driver.session() as session:
            if constraint_type == "unique":
                query = f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{property_name} IS UNIQUE"
            else:
                query = f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{property_name} IS NOT NULL"
            
            session.run(query)
            logger.info(f"Created {constraint_type} constraint on {label}.{property_name}")
    
    def clear_database(self) -> None:
        """Clear all data from the database"""
        with self.driver.session() as session:
            session.run("MATCH ()-[r]->() DELETE r")
            session.run("MATCH (n) DELETE n")
            logger.warning("Cleared all data from Neo4j database")
    
    def get_node_count(self, label: Optional[str] = None) -> int:
        """Get count of nodes"""
        with self.driver.session() as session:
            if label:
                query = f"MATCH (n:{label}) RETURN count(n) as count"
            else:
                query = "MATCH (n) RETURN count(n) as count"
            
            result = session.run(query)
            record = result.single()
            return record["count"] if record else 0
    
    def get_relationship_count(self, relationship_type: Optional[str] = None) -> int:
        """Get count of relationships"""
        with self.driver.session() as session:
            if relationship_type:
                query = f"MATCH ()-[r:{relationship_type}]->() RETURN count(r) as count"
            else:
                query = "MATCH ()-[r]->() RETURN count(r) as count"
            
            result = session.run(query)
            record = result.single()
            return record["count"] if record else 0
    
    def find_nodes_by_property(self, label: str, property_name: str, value: Any) -> List[Dict[str, Any]]:
        """Find nodes by property value"""
        with self.driver.session() as session:
            query = f"MATCH (n:{label} {{{property_name}: $value}}) RETURN n"
            result = session.run(query, value=value)
            return [dict(record["n"]) for record in result]
    
    def get_node_with_relationships(self, node_id: Any, depth: int = 1) -> Dict[str, Any]:
        """Get a node with its relationships up to a certain depth"""
        with self.driver.session() as session:
            query = f"""
                MATCH path = (n)-[*1..{depth}]-(related)
                WHERE id(n) = $node_id
                RETURN n, relationships(path) as rels, nodes(path) as nodes
            """
            result = session.run(query, node_id=node_id)
            records = [dict(record) for record in result]
            return records[0] if records else {}

