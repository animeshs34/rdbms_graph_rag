"""CDC handlers for syncing changes to target systems"""

from typing import Dict, Any, List, Optional
from loguru import logger

from .base import CDCHandler, ChangeEvent, ChangeOperation
from ..graph_db.base import GraphDatabaseConnector
from ..embeddings.embedder import EmbeddingService
from ..embeddings.vector_store import VectorStore
from ..schema_mapper.graph_schema import GraphSchema


class GraphSyncHandler(CDCHandler):
    """
    Handler to sync changes to graph database (Neo4j)
    
    Processes change events and updates the graph database accordingly:
    - INSERT: Create new node
    - UPDATE: Update node properties
    - DELETE: Delete node
    """
    
    def __init__(
        self,
        graph_db: GraphDatabaseConnector,
        graph_schema: GraphSchema,
        domain_prefix: str = ""
    ):
        """
        Initialize graph sync handler
        
        Args:
            graph_db: Graph database connector
            graph_schema: Graph schema mapping
            domain_prefix: Prefix for node labels (e.g., "Healthcare")
        """
        self.graph_db = graph_db
        self.graph_schema = graph_schema
        self.domain_prefix = domain_prefix
        
        self.table_to_node_type = {}
        for node_type in graph_schema.node_types:
            if node_type.source_table:
                self.table_to_node_type[node_type.source_table] = node_type
    
    def handle_change(self, event: ChangeEvent) -> None:
        """Handle a single change event"""
        try:
            if event.operation == ChangeOperation.INSERT:
                self._handle_insert(event)
            elif event.operation == ChangeOperation.UPDATE:
                self._handle_update(event)
            elif event.operation == ChangeOperation.DELETE:
                self._handle_delete(event)
            elif event.operation == ChangeOperation.TRUNCATE:
                self._handle_truncate(event)
            else:
                logger.warning(f"Unsupported operation: {event.operation}")
                
        except Exception as e:
            logger.error(f"Error handling change event: {e}")
            raise
    
    def handle_batch(self, events: List[ChangeEvent]) -> None:
        """Handle a batch of change events"""
        inserts = []
        updates = []
        deletes = []
        
        for event in events:
            if event.operation == ChangeOperation.INSERT:
                inserts.append(event)
            elif event.operation == ChangeOperation.UPDATE:
                updates.append(event)
            elif event.operation == ChangeOperation.DELETE:
                deletes.append(event)
        
        if inserts:
            self._batch_insert(inserts)
        if updates:
            self._batch_update(updates)
        if deletes:
            self._batch_delete(deletes)
    
    def _handle_insert(self, event: ChangeEvent) -> None:
        """Handle INSERT operation"""
        node_type = self.table_to_node_type.get(event.table)
        if not node_type:
            logger.debug(f"No node type mapping for table: {event.table}")
            return
        
        label = node_type.label
        properties = self._prepare_properties(event.new_data, node_type)
        
        self.graph_db.create_node(label, properties)
        logger.debug(f"Created node: {label} with {len(properties)} properties")
    
    def _handle_update(self, event: ChangeEvent) -> None:
        """Handle UPDATE operation"""
        node_type = self.table_to_node_type.get(event.table)
        if not node_type:
            return
        
        label = node_type.label
        properties = self._prepare_properties(event.new_data, node_type)
        
        if event.primary_key and node_type.primary_key:
            pk_value = event.primary_key.get(node_type.primary_key)
            if pk_value:
                query = f"""
                MATCH (n:{label} {{{node_type.primary_key}: $pk_value}})
                SET n += $properties
                RETURN n
                """
                self.graph_db.execute_query(
                    query,
                    {'pk_value': pk_value, 'properties': properties}
                )
                logger.debug(f"Updated node: {label}[{pk_value}]")
    
    def _handle_delete(self, event: ChangeEvent) -> None:
        """Handle DELETE operation"""
        node_type = self.table_to_node_type.get(event.table)
        if not node_type:
            return
        
        label = node_type.label
        
        if event.primary_key and node_type.primary_key:
            pk_value = event.primary_key.get(node_type.primary_key)
            if pk_value:
                query = f"""
                MATCH (n:{label} {{{node_type.primary_key}: $pk_value}})
                DETACH DELETE n
                """
                self.graph_db.execute_query(query, {'pk_value': pk_value})
                logger.debug(f"Deleted node: {label}[{pk_value}]")
    
    def _handle_truncate(self, event: ChangeEvent) -> None:
        """Handle TRUNCATE operation"""
        node_type = self.table_to_node_type.get(event.table)
        if not node_type:
            return
        
        label = node_type.label
        query = f"MATCH (n:{label}) DETACH DELETE n"
        self.graph_db.execute_query(query)
        logger.info(f"Truncated all nodes with label: {label}")
    
    def _batch_insert(self, events: List[ChangeEvent]) -> None:
        """Batch insert multiple nodes"""
        by_table = {}
        for event in events:
            if event.table not in by_table:
                by_table[event.table] = []
            by_table[event.table].append(event)
        
        for table, table_events in by_table.items():
            node_type = self.table_to_node_type.get(table)
            if not node_type:
                continue
            
            nodes = []
            for event in table_events:
                properties = self._prepare_properties(event.new_data, node_type)
                nodes.append(properties)
            
            if nodes:
                self.graph_db.batch_create_nodes(node_type.label, nodes)
                logger.info(f"Batch created {len(nodes)} nodes of type {node_type.label}")
    
    def _batch_update(self, events: List[ChangeEvent]) -> None:
        """Batch update multiple nodes"""
        for event in events:
            self._handle_update(event)
    
    def _batch_delete(self, events: List[ChangeEvent]) -> None:
        """Batch delete multiple nodes"""
        for event in events:
            self._handle_delete(event)
    
    def _prepare_properties(
        self,
        data: Dict[str, Any],
        node_type
    ) -> Dict[str, Any]:
        """Prepare node properties from raw data"""
        if not data:
            return {}

        properties = {}
        for prop in node_type.properties:
            if prop.name in data:
                value = data[prop.name]
                if value is not None:
                    properties[prop.name] = value

        return properties
    
    def can_handle(self, event: ChangeEvent) -> bool:
        """Check if this handler can process the event"""
        return event.table in self.table_to_node_type


class EmbeddingSyncHandler(CDCHandler):
    """
    Handler to sync changes to vector embeddings
    
    Updates vector store when nodes are created, updated, or deleted
    """
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        graph_schema: GraphSchema
    ):
        """
        Initialize embedding sync handler
        
        Args:
            embedding_service: Service for generating embeddings
            vector_store: Vector store for storing embeddings
            graph_schema: Graph schema mapping
        """
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.graph_schema = graph_schema
        
        self.table_to_node_type = {}
        for node_type in graph_schema.node_types:
            if node_type.source_table:
                self.table_to_node_type[node_type.source_table] = node_type
    
    def handle_change(self, event: ChangeEvent) -> None:
        """Handle a single change event"""
        try:
            if event.operation == ChangeOperation.INSERT:
                self._handle_insert(event)
            elif event.operation == ChangeOperation.UPDATE:
                self._handle_update(event)
            elif event.operation == ChangeOperation.DELETE:
                self._handle_delete(event)
                
        except Exception as e:
            logger.error(f"Error updating embeddings: {e}")
            raise
    
    def handle_batch(self, events: List[ChangeEvent]) -> None:
        """Handle a batch of change events"""
        texts = []
        metadatas = []
        
        for event in events:
            if event.operation in [ChangeOperation.INSERT, ChangeOperation.UPDATE]:
                node_type = self.table_to_node_type.get(event.table)
                if node_type and event.new_data:
                    text = self._create_text_representation(event.new_data, node_type)
                    metadata = {
                        'table': event.table,
                        'label': node_type.label,
                        'operation': event.operation.value,
                        'timestamp': event.timestamp.isoformat()
                    }
                    texts.append(text)
                    metadatas.append(metadata)
        
        if texts:
            embeddings = self.embedding_service.embed_texts(texts)
            self.vector_store.add_vectors(embeddings, metadatas)
            logger.info(f"Added {len(embeddings)} embeddings to vector store")
    
    def _handle_insert(self, event: ChangeEvent) -> None:
        """Handle INSERT - create new embedding"""
        node_type = self.table_to_node_type.get(event.table)
        if not node_type or not event.new_data:
            return
        
        text = self._create_text_representation(event.new_data, node_type)
        embedding = self.embedding_service.embed_text(text)
        
        metadata = {
            'table': event.table,
            'label': node_type.label,
            'timestamp': event.timestamp.isoformat()
        }
        
        self.vector_store.add_vectors([embedding], [metadata])
    
    def _handle_update(self, event: ChangeEvent) -> None:
        """Handle UPDATE - update existing embedding"""
        self._handle_insert(event)
    
    def _handle_delete(self, event: ChangeEvent) -> None:
        """Handle DELETE - remove embedding"""
        logger.debug(f"Delete embedding for {event.table}")
    
    def _create_text_representation(
        self,
        data: Dict[str, Any],
        node_type
    ) -> str:
        """Create text representation of data for embedding"""
        parts = [f"Label: {node_type.label}"]
        
        for key, value in data.items():
            if value is not None:
                parts.append(f"{key}: {value}")
        
        return ", ".join(parts)
    
    def can_handle(self, event: ChangeEvent) -> bool:
        """Check if this handler can process the event"""
        return event.table in self.table_to_node_type

