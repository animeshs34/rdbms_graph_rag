"""SQLite database connector"""

import sqlite3
from typing import Any, Dict, List, Optional
from loguru import logger

from .base import DatabaseConnector, TableSchema


class SQLiteConnector(DatabaseConnector):
    """SQLite database connector implementation"""
    
    def connect(self) -> None:
        """Establish SQLite connection"""
        try:
            self.connection = sqlite3.connect(self.connection_string)
            self.connection.row_factory = sqlite3.Row
            logger.info(f"Successfully connected to SQLite database: {self.connection_string}")
        except Exception as e:
            logger.error(f"Failed to connect to SQLite: {e}")
            raise
    
    def disconnect(self) -> None:
        """Close SQLite connection"""
        if self.connection:
            self.connection.close()
            logger.info("SQLite connection closed")
    
    def get_tables(self) -> List[str]:
        """Get list of all tables in the database"""
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        cursor = self.connection.cursor()
        cursor.execute(query)
        return [row[0] for row in cursor.fetchall()]
    
    def get_table_schema(self, table_name: str) -> TableSchema:
        """Get schema information for a specific table"""
        columns = self._get_columns(table_name)
        primary_keys = self._get_primary_keys(table_name)
        foreign_keys = self._get_foreign_keys(table_name)
        indexes = self._get_indexes(table_name)
        row_count = self.get_row_count(table_name)
        
        return TableSchema(
            name=table_name,
            columns=columns,
            primary_keys=primary_keys,
            foreign_keys=foreign_keys,
            indexes=indexes,
            row_count=row_count
        )
    
    def _get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """Get column information for a table"""
        query = f"PRAGMA table_info({table_name})"
        cursor = self.connection.cursor()
        cursor.execute(query)
        return [
            {
                "column_name": row[1],
                "data_type": row[2],
                "is_nullable": row[3] == 0,
                "column_default": row[4],
                "is_primary_key": row[5] == 1
            }
            for row in cursor.fetchall()
        ]
    
    def _get_primary_keys(self, table_name: str) -> List[str]:
        """Get primary key columns for a table"""
        columns = self._get_columns(table_name)
        return [col["column_name"] for col in columns if col["is_primary_key"]]
    
    def _get_foreign_keys(self, table_name: str) -> List[Dict[str, Any]]:
        """Get foreign key constraints for a table"""
        query = f"PRAGMA foreign_key_list({table_name})"
        cursor = self.connection.cursor()
        cursor.execute(query)
        return [
            {
                "column_name": row[3],
                "foreign_table_name": row[2],
                "foreign_column_name": row[4],
                "constraint_name": f"fk_{table_name}_{row[0]}"
            }
            for row in cursor.fetchall()
        ]
    
    def _get_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """Get indexes for a table"""
        query = f"PRAGMA index_list({table_name})"
        cursor = self.connection.cursor()
        cursor.execute(query)
        indexes = []
        for row in cursor.fetchall():
            index_name = row[1]
            is_unique = row[2] == 1
            col_query = f"PRAGMA index_info({index_name})"
            col_cursor = self.connection.cursor()
            col_cursor.execute(col_query)
            for col_row in col_cursor.fetchall():
                indexes.append({
                    "index_name": index_name,
                    "column_name": col_row[2],
                    "is_unique": is_unique
                })
        return indexes
    
    def get_all_schemas(self) -> Dict[str, TableSchema]:
        """Get schema information for all tables"""
        tables = self.get_tables()
        return {table: self.get_table_schema(table) for table in tables}
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results"""
        cursor = self.connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_sample_data(self, table_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get sample data from a table"""
        query = f"SELECT * FROM {table_name} LIMIT ?"
        cursor = self.connection.cursor()
        cursor.execute(query, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_row_count(self, table_name: str) -> int:
        """Get total row count for a table"""
        query = f"SELECT COUNT(*) FROM {table_name}"
        cursor = self.connection.cursor()
        cursor.execute(query)
        return cursor.fetchone()[0]

