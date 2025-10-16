"""MySQL database connector"""

from typing import Any, Dict, List, Optional
import pymysql
from loguru import logger

from .base import DatabaseConnector, TableSchema


class MySQLConnector(DatabaseConnector):
    """MySQL database connector implementation"""
    
    def connect(self) -> None:
        """Establish MySQL connection"""
        try:
            parts = self.connection_string.replace("mysql+pymysql://", "").split("@")
            user_pass = parts[0].split(":")
            host_db = parts[1].split("/")
            host_port = host_db[0].split(":")
            
            self.connection = pymysql.connect(
                host=host_port[0],
                port=int(host_port[1]) if len(host_port) > 1 else 3306,
                user=user_pass[0],
                password=user_pass[1] if len(user_pass) > 1 else "",
                database=host_db[1] if len(host_db) > 1 else "",
                cursorclass=pymysql.cursors.DictCursor
            )
            logger.info("Successfully connected to MySQL database")
        except Exception as e:
            logger.error(f"Failed to connect to MySQL: {e}")
            raise
    
    def disconnect(self) -> None:
        """Close MySQL connection"""
        if self.connection:
            self.connection.close()
            logger.info("MySQL connection closed")
    
    def get_tables(self) -> List[str]:
        """Get list of all tables in the database"""
        query = "SHOW TABLES"
        with self.connection.cursor() as cursor:
            cursor.execute(query)
            return [list(row.values())[0] for row in cursor.fetchall()]
    
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
        query = f"DESCRIBE {table_name}"
        with self.connection.cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
            return [
                {
                    "column_name": row["Field"],
                    "data_type": row["Type"],
                    "is_nullable": row["Null"] == "YES",
                    "column_default": row["Default"],
                    "is_primary_key": row["Key"] == "PRI"
                }
                for row in results
            ]
    
    def _get_primary_keys(self, table_name: str) -> List[str]:
        """Get primary key columns for a table"""
        query = f"""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = %s
            AND CONSTRAINT_NAME = 'PRIMARY'
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (table_name,))
            return [row["COLUMN_NAME"] for row in cursor.fetchall()]
    
    def _get_foreign_keys(self, table_name: str) -> List[Dict[str, Any]]:
        """Get foreign key constraints for a table"""
        query = f"""
            SELECT
                COLUMN_NAME as column_name,
                REFERENCED_TABLE_NAME as foreign_table_name,
                REFERENCED_COLUMN_NAME as foreign_column_name,
                CONSTRAINT_NAME as constraint_name
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = %s
            AND REFERENCED_TABLE_NAME IS NOT NULL
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (table_name,))
            return cursor.fetchall()
    
    def _get_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """Get indexes for a table"""
        query = f"SHOW INDEX FROM {table_name}"
        with self.connection.cursor() as cursor:
            cursor.execute(query)
            return [
                {
                    "index_name": row["Key_name"],
                    "column_name": row["Column_name"],
                    "is_unique": row["Non_unique"] == 0
                }
                for row in cursor.fetchall()
            ]
    
    def get_all_schemas(self) -> Dict[str, TableSchema]:
        """Get schema information for all tables"""
        tables = self.get_tables()
        return {table: self.get_table_schema(table) for table in tables}
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results"""
        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def get_sample_data(self, table_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get sample data from a table"""
        query = f"SELECT * FROM {table_name} LIMIT %s"
        with self.connection.cursor() as cursor:
            cursor.execute(query, (limit,))
            return cursor.fetchall()
    
    def get_row_count(self, table_name: str) -> int:
        """Get total row count for a table"""
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        with self.connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchone()["count"]

