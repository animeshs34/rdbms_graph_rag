"""Data migrator for transferring data from RDBMS to graph databases"""

from typing import Dict, List, Any, Optional
from loguru import logger
from tqdm import tqdm

from ..connectors.base import DatabaseConnector
from ..graph_db.base import GraphDatabaseConnector
from ..schema_mapper.graph_schema import GraphSchema


class DataMigrator:
    """Migrates data from relational databases to graph databases"""
    
    def __init__(
        self,
        source_connector: DatabaseConnector,
        target_connector: GraphDatabaseConnector,
        graph_schema: GraphSchema,
        batch_size: int = 1000
    ):
        """
        Initialize data migrator
        
        Args:
            source_connector: Source RDBMS connector
            target_connector: Target graph database connector
            graph_schema: Graph schema to use for migration
            batch_size: Number of records to process in each batch
        """
        self.source = source_connector
        self.target = target_connector
        self.graph_schema = graph_schema
        self.batch_size = batch_size
        self.node_id_mapping: Dict[str, Dict[Any, Any]] = {}
    
    def migrate(self, clear_target: bool = False) -> Dict[str, Any]:
        """
        Perform full migration from source to target
        
        Args:
            clear_target: Whether to clear target database before migration
            
        Returns:
            Migration statistics
        """
        logger.info("Starting data migration")
        
        if clear_target:
            logger.warning("Clearing target database")
            self.target.clear_database()
        
        stats = {
            "nodes_created": 0,
            "relationships_created": 0,
            "tables_migrated": 0,
            "errors": []
        }
        
        self._create_indexes_and_constraints()
        
        for node_type in self.graph_schema.node_types:
            try:
                count = self._migrate_table_to_nodes(node_type)
                stats["nodes_created"] += count
                stats["tables_migrated"] += 1
                logger.info(f"Migrated {count} nodes for {node_type.label}")
            except Exception as e:
                error_msg = f"Error migrating {node_type.label}: {str(e)}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)
        
        for rel_type in self.graph_schema.relationship_types:
            try:
                count = self._create_relationships(rel_type)
                stats["relationships_created"] += count
                logger.info(f"Created {count} relationships of type {rel_type.type}")
            except Exception as e:
                error_msg = f"Error creating relationships {rel_type.type}: {str(e)}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)
        
        logger.info(f"Migration complete: {stats}")
        return stats
    
    def _create_indexes_and_constraints(self) -> None:
        """Create indexes and constraints in target database"""
        logger.info("Creating indexes and constraints")
        
        for node_type in self.graph_schema.node_types:
            if node_type.primary_key:
                try:
                    self.target.create_index(node_type.label, node_type.primary_key)
                except Exception as e:
                    logger.warning(f"Could not create index: {e}")
            
            for prop in node_type.properties:
                if prop.indexed and prop.name != node_type.primary_key:
                    try:
                        self.target.create_index(node_type.label, prop.name)
                    except Exception as e:
                        logger.warning(f"Could not create index: {e}")
                
                if prop.unique:
                    try:
                        self.target.create_constraint(node_type.label, prop.name, "unique")
                    except Exception as e:
                        logger.warning(f"Could not create constraint: {e}")
    
    def _migrate_table_to_nodes(self, node_type) -> int:
        """Migrate a single table to graph nodes"""
        table_name = node_type.source_table
        if not table_name:
            logger.warning(f"No source table for node type {node_type.label}")
            return 0
        
        total_rows = self.source.get_row_count(table_name)
        logger.info(f"Migrating {total_rows} rows from {table_name} to {node_type.label}")
        
        self.node_id_mapping[table_name] = {}
        
        offset = 0
        total_created = 0
        
        with tqdm(total=total_rows, desc=f"Migrating {table_name}") as pbar:
            while offset < total_rows:
                query = f"SELECT * FROM {table_name} LIMIT {self.batch_size} OFFSET {offset}"
                rows = self.source.execute_query(query)
                
                if not rows:
                    break
                
                nodes = []
                pk_values = []
                
                for row in rows:
                    pk_value = row.get(node_type.primary_key) if node_type.primary_key else None
                    pk_values.append(pk_value)
                    
                    node_props = self._row_to_node_properties(row, node_type)
                    nodes.append(node_props)
                
                node_ids = self.target.batch_create_nodes(node_type.label, nodes)
                
                for pk_value, node_id in zip(pk_values, node_ids):
                    if pk_value is not None:
                        self.node_id_mapping[table_name][pk_value] = node_id
                
                total_created += len(nodes)
                offset += self.batch_size
                pbar.update(len(rows))
        
        return total_created
    
    def _row_to_node_properties(self, row: Dict[str, Any], node_type) -> Dict[str, Any]:
        """Convert a database row to graph node properties"""
        from decimal import Decimal
        from datetime import datetime, date

        properties = {}

        property_names = {prop.name for prop in node_type.properties}

        for key, value in row.items():
            if key in property_names:
                if value is not None:
                    if isinstance(value, Decimal):
                        properties[key] = float(value)
                    elif isinstance(value, (datetime, date)):
                        properties[key] = value.isoformat()
                    else:
                        properties[key] = value

        return properties
    
    def _create_relationships(self, rel_type) -> int:
        """Create relationships based on foreign keys"""
        if not rel_type.source_foreign_key:
            logger.warning(f"No source foreign key for relationship {rel_type.type}")
            return 0
        
        fk_info = rel_type.source_foreign_key
        source_table = fk_info["table"]
        fk_column = fk_info["column"]
        target_table = fk_info["referenced_table"]
        target_column = fk_info["referenced_column"]
        
        logger.info(f"Creating relationships: {source_table}.{fk_column} -> {target_table}.{target_column}")
        
        query = f"""
            SELECT {fk_column}, {self._get_primary_key(source_table)}
            FROM {source_table}
            WHERE {fk_column} IS NOT NULL
        """
        
        rows = self.source.execute_query(query)
        
        relationships = []
        for row in rows:
            source_pk = row[self._get_primary_key(source_table)]
            target_pk = row[fk_column]
            
            source_node_id = self.node_id_mapping.get(source_table, {}).get(source_pk)
            target_node_id = self.node_id_mapping.get(target_table, {}).get(target_pk)
            
            if source_node_id and target_node_id:
                relationships.append({
                    "from_id": source_node_id,
                    "to_id": target_node_id,
                    "type": rel_type.type,
                    "properties": {}
                })
        
        if relationships:
            self.target.batch_create_relationships(relationships)
        
        return len(relationships)
    
    def _get_primary_key(self, table_name: str) -> str:
        """Get primary key column name for a table"""
        for node_type in self.graph_schema.node_types:
            if node_type.source_table == table_name:
                return node_type.primary_key or "id"
        return "id"
    
    def get_migration_stats(self) -> Dict[str, Any]:
        """Get current migration statistics"""
        stats = {
            "total_nodes": self.target.get_node_count(),
            "total_relationships": self.target.get_relationship_count(),
            "node_types": {}
        }
        
        for node_type in self.graph_schema.node_types:
            count = self.target.get_node_count(node_type.label)
            stats["node_types"][node_type.label] = count
        
        return stats

