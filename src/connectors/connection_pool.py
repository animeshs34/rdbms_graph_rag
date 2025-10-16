"""Database connection pooling for improved performance and reliability"""

from typing import Dict, Any, Optional
from queue import Queue, Empty
from threading import Lock
import time
from loguru import logger
import psycopg2
from psycopg2 import pool as pg_pool
import mysql.connector
from mysql.connector import pooling as mysql_pooling


class ConnectionPool:
    """Generic connection pool manager"""
    
    def __init__(
        self,
        db_type: str,
        connection_params: Dict[str, Any],
        min_connections: int = 2,
        max_connections: int = 10,
        timeout: int = 30
    ):
        """
        Initialize connection pool
        
        Args:
            db_type: Database type ('postgres', 'mysql', 'sqlite')
            connection_params: Connection parameters
            min_connections: Minimum number of connections to maintain
            max_connections: Maximum number of connections allowed
            timeout: Connection timeout in seconds
        """
        self.db_type = db_type.lower()
        self.connection_params = connection_params
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.timeout = timeout
        self.pool = None
        self._lock = Lock()
        self._initialize_pool()
    
    def _initialize_pool(self) -> None:
        """Initialize the connection pool based on database type"""
        try:
            if self.db_type == 'postgres':
                self._initialize_postgres_pool()
            elif self.db_type == 'mysql':
                self._initialize_mysql_pool()
            elif self.db_type == 'sqlite':
                self._initialize_sqlite_pool()
            else:
                raise ValueError(f"Unsupported database type: {self.db_type}")
            
            logger.info(f"Initialized {self.db_type} connection pool (min={self.min_connections}, max={self.max_connections})")
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise
    
    def _initialize_postgres_pool(self) -> None:
        """Initialize PostgreSQL connection pool"""
        self.pool = pg_pool.ThreadedConnectionPool(
            self.min_connections,
            self.max_connections,
            **self.connection_params
        )
    
    def _initialize_mysql_pool(self) -> None:
        """Initialize MySQL connection pool"""
        pool_config = {
            **self.connection_params,
            'pool_name': f'mysql_pool_{id(self)}',
            'pool_size': self.max_connections,
            'pool_reset_session': True
        }
        self.pool = mysql_pooling.MySQLConnectionPool(**pool_config)
    
    def _initialize_sqlite_pool(self) -> None:
        """Initialize SQLite connection pool (simple queue-based)"""
        import sqlite3
        self.pool = Queue(maxsize=self.max_connections)
        
        for _ in range(self.min_connections):
            conn = sqlite3.connect(
                self.connection_params.get('database', ':memory:'),
                check_same_thread=False
            )
            self.pool.put(conn)
    
    def get_connection(self):
        """
        Get a connection from the pool
        
        Returns:
            Database connection
        """
        try:
            if self.db_type == 'postgres':
                return self.pool.getconn()
            elif self.db_type == 'mysql':
                return self.pool.get_connection()
            elif self.db_type == 'sqlite':
                try:
                    return self.pool.get(timeout=self.timeout)
                except Empty:
                    if self.pool.qsize() < self.max_connections:
                        import sqlite3
                        return sqlite3.connect(
                            self.connection_params.get('database', ':memory:'),
                            check_same_thread=False
                        )
                    raise TimeoutError("Connection pool exhausted")
        except Exception as e:
            logger.error(f"Failed to get connection from pool: {e}")
            raise
    
    def return_connection(self, connection) -> None:
        """
        Return a connection to the pool
        
        Args:
            connection: Database connection to return
        """
        try:
            if self.db_type == 'postgres':
                self.pool.putconn(connection)
            elif self.db_type == 'mysql':
                connection.close()
            elif self.db_type == 'sqlite':
                if self.pool.qsize() < self.max_connections:
                    self.pool.put(connection)
                else:
                    connection.close()
        except Exception as e:
            logger.error(f"Failed to return connection to pool: {e}")
    
    def close_all(self) -> None:
        """Close all connections in the pool"""
        try:
            if self.db_type == 'postgres':
                self.pool.closeall()
            elif self.db_type == 'mysql':
                pass
            elif self.db_type == 'sqlite':
                while not self.pool.empty():
                    try:
                        conn = self.pool.get_nowait()
                        conn.close()
                    except Empty:
                        break
            
            logger.info(f"Closed all connections in {self.db_type} pool")
        except Exception as e:
            logger.error(f"Error closing connection pool: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get pool status information"""
        status = {
            'db_type': self.db_type,
            'min_connections': self.min_connections,
            'max_connections': self.max_connections,
            'timeout': self.timeout
        }
        
        if self.db_type == 'sqlite':
            status['available_connections'] = self.pool.qsize()
        
        return status


class PooledConnection:
    """Context manager for pooled connections"""
    
    def __init__(self, pool: ConnectionPool):
        """
        Initialize pooled connection context manager
        
        Args:
            pool: Connection pool to use
        """
        self.pool = pool
        self.connection = None
    
    def __enter__(self):
        """Get connection from pool"""
        self.connection = self.pool.get_connection()
        return self.connection
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Return connection to pool"""
        if self.connection:
            if exc_type is not None:
                try:
                    self.connection.rollback()
                except:
                    pass
            self.pool.return_connection(self.connection)
        return False


_pool_registry: Dict[str, ConnectionPool] = {}
_registry_lock = Lock()


def get_or_create_pool(
    pool_id: str,
    db_type: str,
    connection_params: Dict[str, Any],
    **kwargs
) -> ConnectionPool:
    """
    Get existing pool or create new one
    
    Args:
        pool_id: Unique identifier for the pool
        db_type: Database type
        connection_params: Connection parameters
        **kwargs: Additional pool configuration
        
    Returns:
        Connection pool
    """
    with _registry_lock:
        if pool_id not in _pool_registry:
            _pool_registry[pool_id] = ConnectionPool(
                db_type,
                connection_params,
                **kwargs
            )
        return _pool_registry[pool_id]


def close_pool(pool_id: str) -> None:
    """
    Close and remove a pool from registry
    
    Args:
        pool_id: Pool identifier
    """
    with _registry_lock:
        if pool_id in _pool_registry:
            _pool_registry[pool_id].close_all()
            del _pool_registry[pool_id]
            logger.info(f"Closed and removed pool: {pool_id}")


def close_all_pools() -> None:
    """Close all pools in the registry"""
    with _registry_lock:
        for pool_id, pool in list(_pool_registry.items()):
            pool.close_all()
        _pool_registry.clear()
        logger.info("Closed all connection pools")

