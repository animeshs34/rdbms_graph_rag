"""PostgreSQL CDC listener using logical replication"""

import json
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional

import psycopg2
from psycopg2.extras import LogicalReplicationConnection, ReplicationCursor
from loguru import logger

from .base import (
    CDCListener,
    ChangeEvent,
    ChangeOperation,
    CDCSetupError,
    CDCStreamError,
    CDCPositionError
)


class PostgreSQLCDCListener(CDCListener):
    """
    PostgreSQL CDC listener using logical replication
    
    Uses PostgreSQL's logical replication feature with wal2json plugin
    to capture changes in real-time.
    """
    
    def __init__(
        self,
        connection_config: Dict[str, Any],
        slot_name: str = "graph_sync_slot",
        publication_name: str = "graph_sync_pub",
        tables: Optional[list[str]] = None
    ):
        """
        Initialize PostgreSQL CDC listener
        
        Args:
            connection_config: PostgreSQL connection configuration
            slot_name: Name of the replication slot
            publication_name: Name of the publication
            tables: List of tables to monitor (None = all tables)
        """
        super().__init__(connection_config)
        self.slot_name = slot_name
        self.publication_name = publication_name
        self.tables = tables
        self.replication_conn = None
        self.replication_cursor: Optional[ReplicationCursor] = None
        self.stream_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
    def setup(self) -> None:
        """Set up PostgreSQL logical replication"""
        try:
            conn = psycopg2.connect(**self._get_connection_params())
            conn.autocommit = True
            cursor = conn.cursor()

            cursor.execute("SHOW wal_level")
            wal_level = cursor.fetchone()[0]
            if wal_level != 'logical':
                raise CDCSetupError(
                    f"PostgreSQL wal_level must be 'logical', currently: {wal_level}. "
                    "Set wal_level=logical in postgresql.conf and restart PostgreSQL."
                )
            
            cursor.execute(
                "SELECT 1 FROM pg_publication WHERE pubname = %s",
                (self.publication_name,)
            )

            if not cursor.fetchone():
                if self.tables:
                    tables_str = ", ".join(self.tables)
                    cursor.execute(
                        f"CREATE PUBLICATION {self.publication_name} "
                        f"FOR TABLE {tables_str}"
                    )
                else:
                    cursor.execute(
                        f"CREATE PUBLICATION {self.publication_name} "
                        f"FOR ALL TABLES"
                    )
                logger.info(f"Created publication: {self.publication_name}")
            else:
                logger.info(f"Publication already exists: {self.publication_name}")
            
            cursor.execute(
                "SELECT 1 FROM pg_replication_slots WHERE slot_name = %s",
                (self.slot_name,)
            )
            
            if not cursor.fetchone():
                repl_conn = psycopg2.connect(
                    **self._get_connection_params(),
                    connection_factory=LogicalReplicationConnection
                )
                repl_cursor = repl_conn.cursor()
                repl_cursor.create_replication_slot(
                    self.slot_name,
                    output_plugin='wal2json'
                )
                logger.info(f"Created replication slot: {self.slot_name} with wal2json")
                repl_cursor.close()
                repl_conn.close()
            else:
                logger.info(f"Replication slot already exists: {self.slot_name}")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            raise CDCSetupError(f"Failed to set up PostgreSQL CDC: {e}")
    
    def start_streaming(self, callback: Callable[[ChangeEvent], None]) -> None:
        """Start streaming changes from PostgreSQL"""
        if self.is_running:
            logger.warning("CDC streaming already running")
            return
        
        self.is_running = True
        self.stop_event.clear()
        
        self.stream_thread = threading.Thread(
            target=self._stream_changes,
            args=(callback,),
            daemon=True
        )
        self.stream_thread.start()
        logger.info("Started PostgreSQL CDC streaming")
    
    def _stream_changes(self, callback: Callable[[ChangeEvent], None]) -> None:
        """Internal method to stream changes (runs in separate thread)"""
        try:
            self.replication_conn = psycopg2.connect(
                **self._get_connection_params(),
                connection_factory=LogicalReplicationConnection
            )
            self.replication_cursor = self.replication_conn.cursor()
            
            options = {
                'format-version': 2,
                'include-timestamp': True,
                'include-transaction': True,
                'include-lsn': True
            }
            self.replication_cursor.start_replication(
                slot_name=self.slot_name,
                decode=True,
                options=options
            )
            
            logger.info(f"Streaming from replication slot: {self.slot_name}")

            message_count = 0
            while not self.stop_event.is_set():
                msg = self.replication_cursor.read_message()

                if msg:
                    message_count += 1
                    logger.debug(f"Received message #{message_count}: data_start={msg.data_start}, payload_size={len(msg.payload) if msg.payload else 0}")
                    self._process_message(msg, callback)
                else:
                    time.sleep(0.1)
                    
        except Exception as e:
            logger.error(f"Error in CDC streaming: {e}")
            raise CDCStreamError(f"CDC streaming failed: {e}")
        finally:
            if self.replication_cursor:
                self.replication_cursor.close()
            if self.replication_conn:
                self.replication_conn.close()
    
    def _process_message(
        self,
        msg,
        callback: Callable[[ChangeEvent], None]
    ) -> None:
        """Process a replication message"""
        try:
            payload = msg.payload

            logger.debug(f"Processing message payload: {payload[:200] if payload else 'EMPTY'}")

            self.current_position = str(msg.data_start)

            event = self._parse_wal2json(payload)
            if event:
                logger.info(f"Parsed event: {event.operation.value} on {event.schema}.{event.table}")
                callback(event)
            else:
                logger.debug("No event parsed from payload")

            msg.cursor.send_feedback(flush_lsn=msg.data_start)

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
    
    def _parse_wal2json(self, payload: str) -> Optional[ChangeEvent]:
        """
        Parse wal2json output format (JSON)

        Example wal2json format version 2:
        {
            "action": "I",  # I=INSERT, U=UPDATE, D=DELETE, T=TRUNCATE
            "schema": "public",
            "table": "patients",
            "columns": [
                {"name": "patient_id", "type": "integer", "value": 1},
                {"name": "first_name", "type": "text", "value": "John"}
            ],
            "identity": [  # For UPDATE/DELETE - old values
                {"name": "patient_id", "type": "integer", "value": 1}
            ],
            "timestamp": "2024-01-15 10:30:00.123456+00",
            "lsn": "0/12345678"
        }
        """
        try:
            data = json.loads(payload)

            if 'change' in data:
                if not data['change']:
                    return None
                change = data['change'][0]
            else:
                change = data

            action_map = {
                'I': ChangeOperation.INSERT,
                'U': ChangeOperation.UPDATE,
                'D': ChangeOperation.DELETE,
                'T': ChangeOperation.TRUNCATE
            }

            action = change.get('action') or change.get('kind')

            # Ignore transaction control messages (BEGIN, COMMIT)
            if action in ('B', 'C'):
                logger.debug(f"Ignoring transaction control message: {action}")
                return None

            operation = action_map.get(action)
            if not operation:
                logger.warning(f"Unknown action: {action}")
                return None

            schema = change.get('schema', 'public')
            table = change.get('table')

            if not table:
                logger.warning("No table name in wal2json output")
                return None

            new_data = None
            if 'columns' in change:
                new_data = {
                    col['name']: col.get('value')
                    for col in change['columns']
                }

            old_data = None
            if 'identity' in change:
                old_data = {
                    col['name']: col.get('value')
                    for col in change['identity']
                }

            primary_key = None
            if old_data:
                primary_key = old_data.copy()
            elif new_data:
                primary_key = self._extract_pk_from_data(new_data)

            timestamp = datetime.now()
            if 'timestamp' in change:
                try:
                    from dateutil import parser as date_parser
                    timestamp = date_parser.parse(change['timestamp'])
                except:
                    pass

            return ChangeEvent(
                operation=operation,
                table=table,
                schema=schema,
                timestamp=timestamp,
                database_type='postgres',
                old_data=old_data,
                new_data=new_data,
                primary_key=primary_key,
                lsn=change.get('lsn') or self.current_position,
                transaction_id=data.get('xid'),
                metadata={
                    'publication': self.publication_name,
                    'slot': self.slot_name,
                    'plugin': 'wal2json',
                    'nextlsn': data.get('nextlsn')
                }
            )

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing wal2json JSON: {e}")
            logger.debug(f"Payload: {payload}")
            return None
        except Exception as e:
            logger.error(f"Error parsing wal2json output: {e}")
            logger.debug(f"Payload: {payload}")
            return None

        return result

    def _extract_pk_from_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract primary key from data (assume 'id' column)"""
        if 'id' in data:
            return {'id': data['id']}
        return None

    def stop_streaming(self) -> None:
        """Stop streaming changes"""
        if not self.is_running:
            return

        logger.info("Stopping PostgreSQL CDC streaming")
        self.stop_event.set()
        self.is_running = False

        if self.stream_thread:
            self.stream_thread.join(timeout=5)

    def get_current_position(self) -> Optional[str]:
        """Get current LSN position"""
        return self.current_position

    def resume_from_position(self, position: str) -> None:
        """Resume streaming from a specific LSN"""
        self.current_position = position
        logger.info(f"Will resume from position: {position}")

    def cleanup(self) -> None:
        """Clean up replication slot and publication"""
        try:
            conn = psycopg2.connect(**self._get_connection_params())
            conn.autocommit = True
            cursor = conn.cursor()

            cursor.execute(
                f"SELECT pg_drop_replication_slot('{self.slot_name}') "
                f"WHERE EXISTS (SELECT 1 FROM pg_replication_slots WHERE slot_name = '{self.slot_name}')"
            )

            cursor.execute(f"DROP PUBLICATION IF EXISTS {self.publication_name}")

            cursor.close()
            conn.close()

            logger.info("Cleaned up PostgreSQL CDC resources")

        except Exception as e:
            logger.error(f"Error cleaning up CDC: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get current CDC status"""
        try:
            conn = psycopg2.connect(**self._get_connection_params())
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    slot_name,
                    plugin,
                    slot_type,
                    active,
                    restart_lsn,
                    confirmed_flush_lsn
                FROM pg_replication_slots
                WHERE slot_name = %s
                """,
                (self.slot_name,)
            )

            slot_info = cursor.fetchone()

            cursor.close()
            conn.close()

            if slot_info:
                return {
                    'slot_name': slot_info[0],
                    'plugin': slot_info[1],
                    'slot_type': slot_info[2],
                    'active': slot_info[3],
                    'restart_lsn': str(slot_info[4]) if slot_info[4] else None,
                    'confirmed_flush_lsn': str(slot_info[5]) if slot_info[5] else None,
                    'current_position': self.current_position,
                    'is_running': self.is_running
                }
            else:
                return {
                    'error': 'Replication slot not found',
                    'is_running': self.is_running
                }

        except Exception as e:
            return {
                'error': str(e),
                'is_running': self.is_running
            }

    def _get_connection_params(self) -> Dict[str, Any]:
        """Get connection parameters from config"""
        if isinstance(self.connection_config, str):
            return {'dsn': self.connection_config}
        else:
            return {
                'host': self.connection_config.get('host', 'localhost'),
                'port': self.connection_config.get('port', 5432),
                'database': self.connection_config.get('database'),
                'user': self.connection_config.get('user'),
                'password': self.connection_config.get('password')
            }


