"""Data profiler for privacy-preserving statistical analysis"""

from typing import Dict, List, Any, Optional, Set
from collections import Counter
from loguru import logger

from ..connectors.base import DatabaseConnector, TableSchema


class DataProfiler:
    """
    Analyzes database schema and data patterns WITHOUT exposing sensitive data.
    Only generates statistical summaries safe to send to LLM.
    """
    
    def __init__(self, connector: DatabaseConnector):
        """
        Initialize data profiler
        
        Args:
            connector: Database connector for analysis
        """
        self.connector = connector
    
    def profile_schema(
        self, 
        table_schemas: Dict[str, TableSchema],
        sample_size: int = 1000
    ) -> Dict[str, Any]:
        """
        Generate privacy-safe statistical profile of database schema
        
        Args:
            table_schemas: Schema information
            sample_size: Number of rows to analyze (not sent to LLM)
            
        Returns:
            Statistical profile safe for LLM consumption
        """
        logger.info("Generating privacy-safe schema profile")
        
        profile = {
            "tables": {},
            "potential_relationships": [],
            "domain_hints": []
        }
        
        for table_name, schema in table_schemas.items():
            profile["tables"][table_name] = self._profile_table(
                table_name, 
                schema, 
                sample_size
            )
        
        profile["potential_relationships"] = self._analyze_cross_table_patterns(
            table_schemas, 
            profile["tables"]
        )
        
        profile["domain_hints"] = self._detect_domain_hints(table_schemas)
        
        logger.info(f"Generated profile for {len(profile['tables'])} tables")
        return profile
    
    def _profile_table(
        self, 
        table_name: str, 
        schema: TableSchema,
        sample_size: int
    ) -> Dict[str, Any]:
        """Profile a single table (privacy-safe)"""
        
        table_profile = {
            "row_count": 0,
            "columns": {},
            "has_timestamps": False,
            "has_status_fields": False
        }
        
        try:
            table_profile["row_count"] = self.connector.get_row_count(table_name)
            
            sample_data = self.connector.get_sample_data(table_name, limit=sample_size)
            
            for column in schema.columns:
                col_name = column["column_name"]
                table_profile["columns"][col_name] = self._profile_column(
                    col_name,
                    column,
                    sample_data
                )
            
            table_profile["has_timestamps"] = any(
                'date' in col.lower() or 'time' in col.lower() 
                for col in table_profile["columns"].keys()
            )
            
            table_profile["has_status_fields"] = any(
                'status' in col.lower() or 'state' in col.lower()
                for col in table_profile["columns"].keys()
            )
            
        except Exception as e:
            logger.warning(f"Error profiling table {table_name}: {e}")
        
        return table_profile
    
    def _profile_column(
        self, 
        col_name: str, 
        column_info: Dict[str, Any],
        sample_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Profile a single column - PRIVACY SAFE
        Returns only statistical metadata, never actual values
        """
        
        profile = {
            "data_type": column_info.get("data_type"),
            "is_nullable": column_info.get("is_nullable", True),
            "is_primary_key": column_info.get("is_primary_key", False),
            "is_foreign_key": column_info.get("is_foreign_key", False),
        }
        
        values = [row.get(col_name) for row in sample_data if row.get(col_name) is not None]
        
        if not values:
            profile["null_percentage"] = 100.0
            return profile
        
        total_rows = len(sample_data)
        non_null_count = len(values)
        
        profile["null_percentage"] = ((total_rows - non_null_count) / total_rows * 100) if total_rows > 0 else 0
        profile["distinct_count"] = len(set(str(v) for v in values))
        profile["distinct_ratio"] = profile["distinct_count"] / non_null_count if non_null_count > 0 else 0
        
        if profile["distinct_ratio"] > 0.95:
            profile["cardinality"] = "unique"  # Likely ID or unique field
        elif profile["distinct_ratio"] < 0.1:
            profile["cardinality"] = "low"  # Likely enum/category
        else:
            profile["cardinality"] = "medium"
        
        if values:
            sample_value = str(values[0])
            
            if '@' in sample_value:
                profile["pattern"] = "email_like"
            elif len(sample_value) == 10 and sample_value.replace('-', '').isdigit():
                profile["pattern"] = "phone_like"
            elif col_name.lower().endswith('_id'):
                profile["pattern"] = "identifier"
            elif col_name.lower() in ['status', 'state', 'type', 'category']:
                profile["pattern"] = "categorical"
            
            if isinstance(sample_value, str):
                lengths = [len(str(v)) for v in values]
                profile["avg_length"] = sum(lengths) / len(lengths)
                profile["max_length"] = max(lengths)
                profile["min_length"] = min(lengths)
        
        return profile
    
    def _analyze_cross_table_patterns(
        self,
        table_schemas: Dict[str, TableSchema],
        table_profiles: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect potential relationships by analyzing patterns across tables
        WITHOUT exposing actual data
        """
        
        potential_relationships = []
        
        table_names = list(table_schemas.keys())
        
        for i, table1 in enumerate(table_names):
            for table2 in table_names[i+1:]:
                cols1 = set(table_profiles[table1]["columns"].keys())
                cols2 = set(table_profiles[table2]["columns"].keys())
                
                common_cols = cols1 & cols2
                
                for col in common_cols:
                    col1_profile = table_profiles[table1]["columns"][col]
                    col2_profile = table_profiles[table2]["columns"][col]
                    
                    if (col1_profile.get("cardinality") == col2_profile.get("cardinality") and
                        col1_profile.get("data_type") == col2_profile.get("data_type")):
                        
                        potential_relationships.append({
                            "table1": table1,
                            "table2": table2,
                            "linking_column": col,
                            "confidence": "medium",
                            "reason": "matching_column_name_and_type"
                        })
                
                for col in cols1:
                    if col.endswith('_id'):
                        potential_table = col[:-3]
                        if self._is_similar_name(potential_table, table2):
                            potential_relationships.append({
                                "table1": table1,
                                "table2": table2,
                                "linking_column": col,
                                "confidence": "high",
                                "reason": "naming_convention_fk_pattern"
                            })
        
        return potential_relationships
    
    def _detect_domain_hints(
        self, 
        table_schemas: Dict[str, TableSchema]
    ) -> List[str]:
        """
        Detect domain/industry from table and column names
        Safe to share with LLM
        """
        
        hints = []
        
        domain_keywords = {
            "healthcare": ["patient", "doctor", "appointment", "prescription", "diagnosis", "medical"],
            "ecommerce": ["product", "order", "customer", "cart", "payment", "shipping"],
            "finance": ["account", "transaction", "balance", "payment", "invoice"],
            "education": ["student", "course", "enrollment", "grade", "teacher"],
            "hr": ["employee", "department", "salary", "attendance", "leave"]
        }
        
        all_names = []
        for table_name, schema in table_schemas.items():
            all_names.append(table_name.lower())
            all_names.extend([col["column_name"].lower() for col in schema.columns])
        
        for domain, keywords in domain_keywords.items():
            matches = sum(1 for keyword in keywords if any(keyword in name for name in all_names))
            if matches >= 2:
                hints.append(f"{domain} (confidence: {matches} matches)")
        
        return hints
    
    def _is_similar_name(self, name1: str, name2: str) -> bool:
        """Check if two names are similar"""
        name1 = name1.lower().rstrip('s')
        name2 = name2.lower().rstrip('s')
        return name1 == name2 or name1 in name2 or name2 in name1

