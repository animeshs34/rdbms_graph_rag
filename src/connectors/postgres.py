"""PostgreSQL database connector"""

from typing import Any, Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from loguru import logger

from .base import DatabaseConnector, TableSchema, ColumnInfo


class PostgreSQLConnector(DatabaseConnector):
    """PostgreSQL database connector implementation"""
    
    def connect(self) -> None:
        """Establish PostgreSQL connection"""
        try:
            self.connection = psycopg2.connect(self.connection_string)
            logger.info("Successfully connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    def disconnect(self) -> None:
        """Close PostgreSQL connection"""
        if self.connection:
            self.connection.close()
            logger.info("PostgreSQL connection closed")
    
    def get_tables(self) -> List[str]:
        """Get list of all tables in the database"""
        query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        with self.connection.cursor() as cursor:
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
        query = """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length,
                numeric_precision,
                numeric_scale
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
        """
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (table_name,))
            return [dict(row) for row in cursor.fetchall()]
    
    def _get_primary_keys(self, table_name: str) -> List[str]:
        """Get primary key columns for a table"""
        query = """
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = %s::regclass AND i.indisprimary
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (table_name,))
            return [row[0] for row in cursor.fetchall()]
    
    def _get_foreign_keys(self, table_name: str) -> List[Dict[str, Any]]:
        """Get foreign key constraints for a table"""
        query = """
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name,
                tc.constraint_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY' 
            AND tc.table_name = %s
        """
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (table_name,))
            return [dict(row) for row in cursor.fetchall()]
    
    def _get_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """Get indexes for a table"""
        query = """
            SELECT
                i.relname as index_name,
                a.attname as column_name,
                ix.indisunique as is_unique
            FROM pg_class t
            JOIN pg_index ix ON t.oid = ix.indrelid
            JOIN pg_class i ON i.oid = ix.indexrelid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
            WHERE t.relname = %s
            AND t.relkind = 'r'
        """
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (table_name,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_schemas(self) -> Dict[str, TableSchema]:
        """Get schema information for all tables"""
        tables = self.get_tables()
        return {table: self.get_table_schema(table) for table in tables}
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results"""
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_sample_data(self, table_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get sample data from a table"""
        query = f"SELECT * FROM {table_name} LIMIT %s"
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_row_count(self, table_name: str) -> int:
        """Get total row count for a table"""
        query = f"SELECT COUNT(*) FROM {table_name}"
        with self.connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchone()[0]

