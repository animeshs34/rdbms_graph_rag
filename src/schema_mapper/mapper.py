"""Schema mapper for converting RDBMS schemas to graph schemas"""

import re
from typing import Dict, List, Optional, Set
from loguru import logger

from ..connectors.base import TableSchema, DatabaseConnector
from .graph_schema import GraphSchema, NodeType, RelationshipType, Property, PropertyType
from .llm_enhancer import LLMSchemaEnhancer
from .data_profiler import DataProfiler


class SchemaMapper:
    """Maps relational database schemas to graph schemas"""
    
    TYPE_MAPPING = {
        "integer": PropertyType.INTEGER,
        "bigint": PropertyType.INTEGER,
        "smallint": PropertyType.INTEGER,
        "serial": PropertyType.INTEGER,
        "bigserial": PropertyType.INTEGER,
        "numeric": PropertyType.FLOAT,
        "decimal": PropertyType.FLOAT,
        "real": PropertyType.FLOAT,
        "double precision": PropertyType.FLOAT,
        "varchar": PropertyType.STRING,
        "char": PropertyType.STRING,
        "text": PropertyType.STRING,
        "boolean": PropertyType.BOOLEAN,
        "date": PropertyType.DATE,
        "timestamp": PropertyType.DATETIME,
        "timestamptz": PropertyType.DATETIME,
        "json": PropertyType.JSON,
        "jsonb": PropertyType.JSON,
        "int": PropertyType.INTEGER,
        "tinyint": PropertyType.INTEGER,
        "mediumint": PropertyType.INTEGER,
        "float": PropertyType.FLOAT,
        "double": PropertyType.FLOAT,
        "datetime": PropertyType.DATETIME,
        "INTEGER": PropertyType.INTEGER,
        "REAL": PropertyType.FLOAT,
        "TEXT": PropertyType.STRING,
        "BLOB": PropertyType.STRING,
    }
    
    def __init__(
        self,
        use_naming_conventions: bool = True,
        similarity_threshold: float = 0.7,
        llm_enhancer: Optional[LLMSchemaEnhancer] = None
    ):
        """
        Initialize schema mapper

        Args:
            use_naming_conventions: Whether to use naming conventions for relationship inference
            similarity_threshold: Threshold for column name similarity matching
            llm_enhancer: Optional LLM enhancer for intelligent schema mapping
        """
        self.use_naming_conventions = use_naming_conventions
        self.similarity_threshold = similarity_threshold
        self.llm_enhancer = llm_enhancer
    
    def map_schema(
        self,
        table_schemas: Dict[str, TableSchema],
        label_prefix: Optional[str] = None,
        source_connector: Optional[DatabaseConnector] = None
    ) -> GraphSchema:
        """
        Map relational schemas to graph schema

        Args:
            table_schemas: Dictionary of table name to TableSchema
            label_prefix: Optional prefix for all node labels (e.g., "Ecommerce_", "Healthcare_")
            source_connector: Optional database connector for statistical profiling

        Returns:
            GraphSchema object
        """
        logger.info(f"Mapping {len(table_schemas)} tables to graph schema")
        if label_prefix:
            logger.info(f"Using label prefix: {label_prefix}")

        graph_schema = GraphSchema()
        graph_schema.metadata = {
            "source_tables": list(table_schemas.keys()),
            "total_tables": len(table_schemas),
            "label_prefix": label_prefix
        }

        for table_name, table_schema in table_schemas.items():
            node_type = self._create_node_type(table_name, table_schema, label_prefix)
            graph_schema.add_node_type(node_type)

        for table_name, table_schema in table_schemas.items():
            relationships = self._create_relationships_from_foreign_keys(
                table_name, table_schema, table_schemas, label_prefix
            )
            for relationship in relationships:
                graph_schema.add_relationship_type(relationship)

        if self.use_naming_conventions:
            inferred_relationships = self._infer_relationships_from_naming(
                table_schemas, graph_schema, label_prefix
            )
            for relationship in inferred_relationships:
                graph_schema.add_relationship_type(relationship)

        if self.llm_enhancer and source_connector:
            logger.info("Enhancing schema with LLM (metadata only, no raw data)")
            llm_relationships = self._enhance_with_llm(
                table_schemas, graph_schema, label_prefix, source_connector
            )
            for relationship in llm_relationships:
                graph_schema.add_relationship_type(relationship)

        logger.info(
            f"Created graph schema with {len(graph_schema.node_types)} node types "
            f"and {len(graph_schema.relationship_types)} relationship types"
        )

        return graph_schema
    
    def _create_node_type(
        self,
        table_name: str,
        table_schema: TableSchema,
        label_prefix: Optional[str] = None
    ) -> NodeType:
        """Create a node type from a table schema"""
        label = self._table_name_to_label(table_name, label_prefix)

        properties = []
        for column in table_schema.columns:
            prop = self._column_to_property(column)
            if prop:
                properties.append(prop)

        primary_key = table_schema.primary_keys[0] if table_schema.primary_keys else None

        return NodeType(
            label=label,
            properties=properties,
            source_table=table_name,
            primary_key=primary_key,
            description=f"Node type derived from table '{table_name}'"
        )

    def _table_name_to_label(self, table_name: str, label_prefix: Optional[str] = None) -> str:
        """Convert table name to graph node label"""
        words = table_name.split('_')
        label = ''.join(word.capitalize() for word in words)

        if label.endswith('ies'):
            label = label[:-3] + 'y'
        elif label.endswith('ses'):
            label = label[:-2]
        elif label.endswith('s') and not label.endswith('ss'):
            label = label[:-1]

        if label_prefix:
            if not label_prefix.endswith('_'):
                label_prefix = label_prefix + '_'
            label = label_prefix + label

        return label
    
    def _column_to_property(self, column: Dict) -> Optional[Property]:
        """Convert a database column to a graph property"""
        column_name = column.get("column_name")
        data_type = column.get("data_type", "").lower()
        
        if column_name in ["created_at", "updated_at", "deleted_at"]:
            return None
        
        prop_type = self._map_sql_type(data_type)
        
        is_primary = column.get("is_primary_key", False)
        is_nullable = column.get("is_nullable", True)
        
        return Property(
            name=column_name,
            type=prop_type,
            required=not is_nullable,
            indexed=is_primary,
            unique=is_primary,
            description=f"Property from column '{column_name}'"
        )
    
    def _map_sql_type(self, sql_type: str) -> PropertyType:
        """Map SQL data type to graph property type"""
        base_type = re.sub(r'\(.*?\)', '', sql_type).strip()
        
        if base_type in self.TYPE_MAPPING:
            return self.TYPE_MAPPING[base_type]
        
        for sql_pattern, prop_type in self.TYPE_MAPPING.items():
            if sql_pattern in base_type:
                return prop_type
        
        return PropertyType.STRING
    
    def _create_relationships_from_foreign_keys(
        self,
        table_name: str,
        table_schema: TableSchema,
        all_schemas: Dict[str, TableSchema],
        label_prefix: Optional[str] = None
    ) -> List[RelationshipType]:
        """Create relationships from foreign key constraints"""
        relationships = []

        for fk in table_schema.foreign_keys:
            from_label = self._table_name_to_label(table_name, label_prefix)
            to_label = self._table_name_to_label(fk["foreign_table_name"], label_prefix)
            
            rel_type = self._generate_relationship_type(
                table_name, 
                fk["foreign_table_name"],
                fk["column_name"]
            )
            
            relationship = RelationshipType(
                type=rel_type,
                from_node=from_label,
                to_node=to_label,
                source_foreign_key={
                    "table": table_name,
                    "column": fk["column_name"],
                    "referenced_table": fk["foreign_table_name"],
                    "referenced_column": fk["foreign_column_name"]
                },
                cardinality="many-to-one",
                description=f"Relationship from {from_label} to {to_label} via foreign key"
            )
            
            relationships.append(relationship)
        
        return relationships
    
    def _generate_relationship_type(
        self, 
        from_table: str, 
        to_table: str, 
        fk_column: str
    ) -> str:
        """Generate a meaningful relationship type name"""
        
        column_base = fk_column.replace("_id", "").replace("_fk", "")
        
        to_table_singular = to_table.rstrip('s')
        if to_table_singular.lower() in column_base.lower():
            return f"HAS_{to_table_singular.upper()}"
        else:
            parts = column_base.split('_')
            if len(parts) > 1:
                verb = '_'.join(parts[:-1])
                return verb.upper()
            else:
                return f"RELATES_TO_{to_table_singular.upper()}"
    
    def _infer_relationships_from_naming(
        self,
        table_schemas: Dict[str, TableSchema],
        graph_schema: GraphSchema,
        label_prefix: Optional[str] = None
    ) -> List[RelationshipType]:
        """Infer additional relationships from naming conventions"""
        inferred = []
        existing_rels = set()

        for rel in graph_schema.relationship_types:
            key = (rel.from_node, rel.to_node, rel.type)
            existing_rels.add(key)

        for table_name, table_schema in table_schemas.items():
            from_label = self._table_name_to_label(table_name, label_prefix)

            for column in table_schema.columns:
                column_name = column["column_name"]

                if column_name.endswith("_id"):
                    potential_table = column_name[:-3]

                    for other_table in table_schemas.keys():
                        if self._is_similar(potential_table, other_table):
                            to_label = self._table_name_to_label(other_table, label_prefix)
                            rel_type = f"HAS_{to_label.upper()}"
                            
                            key = (from_label, to_label, rel_type)
                            if key not in existing_rels:
                                relationship = RelationshipType(
                                    type=rel_type,
                                    from_node=from_label,
                                    to_node=to_label,
                                    cardinality="many-to-one",
                                    description=f"Inferred relationship from naming convention"
                                )
                                inferred.append(relationship)
                                existing_rels.add(key)
        
        logger.info(f"Inferred {len(inferred)} additional relationships from naming conventions")
        return inferred
    
    def _is_similar(self, name1: str, name2: str) -> bool:
        """Check if two names are similar (for relationship inference)"""
        name1 = name1.lower().rstrip('s')
        name2 = name2.lower().rstrip('s')
        return name1 == name2 or name1 in name2 or name2 in name1

    def _enhance_with_llm(
        self,
        table_schemas: Dict[str, TableSchema],
        graph_schema: GraphSchema,
        label_prefix: Optional[str],
        source_connector: DatabaseConnector
    ) -> List[RelationshipType]:
        """
        Enhance schema mapping with LLM using privacy-preserving statistical analysis

        Args:
            table_schemas: Table schemas
            graph_schema: Current graph schema
            label_prefix: Domain prefix
            source_connector: Database connector for profiling

        Returns:
            List of LLM-inferred relationships
        """
        try:
            profiler = DataProfiler(source_connector)
            data_profile = profiler.profile_schema(table_schemas, sample_size=1000)

            llm_suggestions = self.llm_enhancer.infer_relationships(
                table_schemas,
                graph_schema.relationship_types,
                data_profile,
                label_prefix
            )

            llm_relationships = []
            existing_keys = set()

            for rel in graph_schema.relationship_types:
                key = (rel.from_node, rel.to_node, rel.type)
                existing_keys.add(key)

            for suggestion in llm_suggestions:
                from_label = self._table_name_to_label(suggestion["from_table"], label_prefix)
                to_label = self._table_name_to_label(suggestion["to_table"], label_prefix)
                rel_type = suggestion["relationship_type"]

                key = (from_label, to_label, rel_type)

                if key not in existing_keys and suggestion.get("confidence", 0) >= 0.6:
                    relationship = RelationshipType(
                        type=rel_type,
                        from_node=from_label,
                        to_node=to_label,
                        cardinality=suggestion.get("cardinality", "many-to-one"),
                        description=f"LLM-inferred: {suggestion.get('reasoning', 'No reason provided')}"
                    )
                    llm_relationships.append(relationship)
                    existing_keys.add(key)

                    logger.info(
                        f"LLM added relationship: {from_label} --[{rel_type}]--> {to_label} "
                        f"(confidence: {suggestion.get('confidence', 0):.2f})"
                    )

            return llm_relationships

        except Exception as e:
            logger.error(f"Error in LLM enhancement: {e}")
            return []

