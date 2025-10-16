"""LLM-based schema enhancement using ONLY metadata (privacy-preserving)"""

import json
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger

from ..connectors.base import TableSchema
from .graph_schema import RelationshipType, PropertyType
from ..llm.provider import create_llm_provider, LLMProvider


class LLMSchemaEnhancer:
    """
    LLM-based schema enhancement that NEVER sends actual data.
    Only uses metadata and statistical summaries for privacy protection.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        provider: str = "openai"
    ):
        """
        Initialize LLM schema enhancer

        Args:
            api_key: LLM provider API key
            model: LLM model to use (default: gpt-4o-mini for cost efficiency)
            provider: LLM provider ('openai' or 'gemini')
        """
        self.provider = create_llm_provider(provider, api_key, model)
        self.model = model
        self.provider_name = provider
        logger.info(f"Initialized LLM Schema Enhancer with {provider} model: {model}")
    
    def infer_relationships(
        self,
        table_schemas: Dict[str, TableSchema],
        existing_relationships: List[RelationshipType],
        data_profile: Optional[Dict[str, Any]] = None,
        label_prefix: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Infer additional relationships using LLM with ONLY metadata
        
        Args:
            table_schemas: Schema information (metadata only)
            existing_relationships: Already detected relationships
            data_profile: Statistical profile (NO raw data)
            label_prefix: Domain prefix for labels
            
        Returns:
            List of inferred relationship suggestions
        """
        logger.info("Using LLM to infer relationships from metadata")
        
        context = self._build_metadata_context(
            table_schemas,
            existing_relationships,
            data_profile
        )
        
        prompt = f"""You are a database schema expert. Analyze the following database schema METADATA to infer relationships.

IMPORTANT: You are analyzing ONLY schema metadata and statistics. NO actual data is provided.

{context}

Your tasks:
1. Identify implicit relationships not captured by foreign keys
2. Infer relationship cardinality based on:
   - Column naming patterns
   - Data type compatibility
   - Statistical patterns (distinct counts, null percentages)
   - Domain knowledge
3. Suggest semantic relationship names based on domain context
4. Consider temporal relationships (created_at, updated_at patterns)
5. Identify many-to-many relationships (junction tables)

For each inferred relationship, provide:
- from_table: Source table name
- to_table: Target table name  
- relationship_type: Semantic name in UPPER_SNAKE_CASE (e.g., "TREATED_BY", "PURCHASED", "BELONGS_TO")
- cardinality: "one-to-one", "one-to-many", "many-to-one", or "many-to-many"
- confidence: 0.0-1.0 (how confident you are)
- reasoning: Brief explanation of why you inferred this relationship
- linking_columns: Object with "from_column" and "to_column" keys

Only suggest relationships with confidence >= 0.6.

Return as JSON with a "relationships" array. Example:
{{
  "relationships": [
    {{
      "from_table": "orders",
      "to_table": "customers",
      "relationship_type": "PLACED_BY",
      "cardinality": "many-to-one",
      "confidence": 0.9,
      "reasoning": "orders.customer_id references customers table, naming convention suggests customer relationship",
      "linking_columns": {{"from_column": "customer_id", "to_column": "id"}}
    }}
  ]
}}"""

        try:
            response = self.provider.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a database schema expert. You analyze ONLY metadata, never actual data."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result = json.loads(response)
            relationships = result.get("relationships", [])
            
            logger.info(f"LLM suggested {len(relationships)} relationships")
            
            for rel in relationships:
                logger.debug(
                    f"LLM suggestion: {rel['from_table']} --[{rel['relationship_type']}]--> "
                    f"{rel['to_table']} (confidence: {rel['confidence']}, reason: {rel['reasoning']})"
                )
            
            return relationships
            
        except Exception as e:
            logger.error(f"Error in LLM relationship inference: {e}")
            return []
    
    def suggest_relationship_names(
        self,
        from_table: str,
        to_table: str,
        column_name: str,
        domain_hints: Optional[List[str]] = None
    ) -> str:
        """
        Suggest a semantic relationship name using LLM
        
        Args:
            from_table: Source table
            to_table: Target table
            column_name: Foreign key column name
            domain_hints: Domain context hints
            
        Returns:
            Suggested relationship name
        """
        
        domain_context = f"\nDomain context: {', '.join(domain_hints)}" if domain_hints else ""
        
        prompt = f"""Given a database relationship, suggest a semantic relationship name.

From table: {from_table}
To table: {to_table}
Foreign key column: {column_name}{domain_context}

Suggest a meaningful relationship name in UPPER_SNAKE_CASE that describes the relationship.
Examples:
- customer_id in orders → "PLACED_BY" or "BELONGS_TO"
- doctor_id in appointments → "SCHEDULED_WITH" or "ASSIGNED_TO"
- product_id in order_items → "CONTAINS"

Return ONLY the relationship name, nothing else."""

        try:
            response = self.provider.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=20
            )

            name = response.strip().upper()
            logger.debug(f"LLM suggested relationship name: {name}")
            return name
            
        except Exception as e:
            logger.error(f"Error suggesting relationship name: {e}")
            return f"HAS_{to_table.upper()}"

    def suggest_relationship_names_batch(
        self,
        relationships: List[Dict[str, str]],
        max_workers: int = 5
    ) -> List[str]:
        """
        Suggest relationship names for multiple relationships in parallel

        Args:
            relationships: List of dicts with 'from_table', 'to_table', 'column_name', 'domain_hints'
            max_workers: Maximum number of parallel workers

        Returns:
            List of suggested relationship names in same order as input
        """
        logger.info(f"Suggesting {len(relationships)} relationship names in parallel with {max_workers} workers")

        results = [None] * len(relationships)

        def process_single(idx: int, rel: Dict[str, str]) -> tuple:
            """Process a single relationship and return (index, result)"""
            try:
                name = self.suggest_relationship_names(
                    from_table=rel['from_table'],
                    to_table=rel['to_table'],
                    column_name=rel['column_name'],
                    domain_hints=rel.get('domain_hints')
                )
                return (idx, name)
            except Exception as e:
                logger.error(f"Error processing relationship {idx}: {e}")
                return (idx, f"HAS_{rel['to_table'].upper()}")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(process_single, idx, rel): idx
                for idx, rel in enumerate(relationships)
            }

            for future in as_completed(futures):
                idx, name = future.result()
                results[idx] = name

        logger.info(f"Completed {len(results)} relationship name suggestions")
        return results

    def _build_metadata_context(
        self,
        table_schemas: Dict[str, TableSchema],
        existing_relationships: List[RelationshipType],
        data_profile: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build context for LLM using ONLY metadata (privacy-safe)
        """
        context_parts = []
        
        if data_profile and data_profile.get("domain_hints"):
            context_parts.append("=== DETECTED DOMAIN ===")
            context_parts.append(f"Likely domains: {', '.join(data_profile['domain_hints'])}\n")
        
        context_parts.append("=== DATABASE SCHEMA (Metadata Only) ===\n")
        
        for table_name, schema in table_schemas.items():
            context_parts.append(f"\nTable: {table_name}")
            
            if data_profile and table_name in data_profile.get("tables", {}):
                row_count = data_profile["tables"][table_name].get("row_count", 0)
                context_parts.append(f"  Row count: {row_count}")
            
            context_parts.append(f"  Primary Key: {schema.primary_keys}")
            
            context_parts.append("  Columns:")
            for col in schema.columns[:15]:
                col_info = f"    - {col['column_name']} ({col['data_type']})"
                
                if data_profile and table_name in data_profile.get("tables", {}):
                    col_profile = data_profile["tables"][table_name]["columns"].get(col['column_name'], {})
                    if col_profile:
                        stats = []
                        if col_profile.get("cardinality"):
                            stats.append(f"cardinality: {col_profile['cardinality']}")
                        if col_profile.get("null_percentage") is not None:
                            stats.append(f"null: {col_profile['null_percentage']:.1f}%")
                        if col_profile.get("pattern"):
                            stats.append(f"pattern: {col_profile['pattern']}")
                        
                        if stats:
                            col_info += f" [{', '.join(stats)}]"
                
                context_parts.append(col_info)
            
            if schema.foreign_keys:
                context_parts.append("  Foreign Keys:")
                for fk in schema.foreign_keys:
                    context_parts.append(
                        f"    - {fk['column_name']} -> "
                        f"{fk['foreign_table_name']}.{fk['foreign_column_name']}"
                    )
        
        context_parts.append("\n=== EXISTING RELATIONSHIPS (Already Detected) ===")
        if existing_relationships:
            for rel in existing_relationships:
                context_parts.append(
                    f"  {rel.from_node} --[{rel.type}]--> {rel.to_node} "
                    f"({rel.cardinality})"
                )
        else:
            context_parts.append("  None detected yet")
        
        if data_profile and data_profile.get("potential_relationships"):
            context_parts.append("\n=== POTENTIAL RELATIONSHIPS (Statistical Analysis) ===")
            for pot_rel in data_profile["potential_relationships"][:10]:  # Limit
                context_parts.append(
                    f"  {pot_rel['table1']} <-> {pot_rel['table2']} "
                    f"via {pot_rel['linking_column']} "
                    f"(reason: {pot_rel['reason']})"
                )
        
        return "\n".join(context_parts)

