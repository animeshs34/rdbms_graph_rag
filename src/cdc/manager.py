"""CDC Manager for coordinating change data capture across databases"""

import threading
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from .base import CDCListener, ChangeEvent, CDCHandler, CDCError


class CDCManager:
    """
    Manages CDC across multiple databases and coordinates change handlers
    
    The CDC Manager:
    - Registers and manages multiple database CDC listeners
    - Routes change events to appropriate handlers
    - Provides batching and throttling capabilities
    - Tracks CDC status and metrics
    """
    
    def __init__(
        self,
        batch_size: int = 100,
        batch_timeout: float = 5.0,
        enable_batching: bool = True
    ):
        """
        Initialize CDC Manager
        
        Args:
            batch_size: Number of events to batch before processing
            batch_timeout: Max seconds to wait before processing partial batch
            enable_batching: Whether to batch events or process immediately
        """
        self.listeners: Dict[str, CDCListener] = {}
        self.handlers: List[CDCHandler] = []
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.enable_batching = enable_batching
        
        self.event_queue: List[ChangeEvent] = []
        self.queue_lock = threading.Lock()
        self.batch_thread: Optional[threading.Thread] = None
        self.stop_batching = threading.Event()
        
        self.metrics = {
            'events_received': 0,
            'events_processed': 0,
            'events_failed': 0,
            'batches_processed': 0,
            'last_event_time': None,
            'errors': []
        }
        self.metrics_lock = threading.Lock()
    
    def register_listener(
        self,
        name: str,
        listener: CDCListener,
        auto_setup: bool = True
    ) -> None:
        """
        Register a CDC listener for a database
        
        Args:
            name: Unique name for this listener
            listener: CDC listener instance
            auto_setup: Whether to automatically run setup()
        """
        if name in self.listeners:
            raise CDCError(f"Listener '{name}' already registered")
        
        self.listeners[name] = listener
        
        if auto_setup:
            try:
                listener.setup()
                logger.info(f"Set up CDC listener: {name}")
            except Exception as e:
                logger.error(f"Failed to set up listener '{name}': {e}")
                raise
    
    def add_handler(self, handler: CDCHandler) -> None:
        """
        Add a change event handler
        
        Args:
            handler: Handler to process change events
        """
        self.handlers.append(handler)
        logger.info(f"Added CDC handler: {handler.__class__.__name__}")
    
    def start_all(self) -> None:
        """Start CDC for all registered listeners"""
        if not self.listeners:
            logger.warning("No CDC listeners registered")
            return
        
        if self.enable_batching:
            self.stop_batching.clear()
            self.batch_thread = threading.Thread(
                target=self._batch_processor,
                daemon=True
            )
            self.batch_thread.start()
            logger.info("Started batch processing thread")
        
        for name, listener in self.listeners.items():
            try:
                listener.start_streaming(self._handle_change)
                logger.info(f"Started CDC listener: {name}")
            except Exception as e:
                logger.error(f"Failed to start listener '{name}': {e}")
    
    def stop_all(self) -> None:
        """Stop CDC for all registered listeners"""
        for name, listener in self.listeners.items():
            try:
                listener.stop_streaming()
                logger.info(f"Stopped CDC listener: {name}")
            except Exception as e:
                logger.error(f"Error stopping listener '{name}': {e}")
        
        if self.batch_thread:
            self.stop_batching.set()
            self.batch_thread.join(timeout=10)
            
            if self.event_queue:
                logger.info(f"Processing {len(self.event_queue)} remaining events")
                self._process_batch(self.event_queue)
                self.event_queue.clear()
    
    def _handle_change(self, event: ChangeEvent) -> None:
        """
        Handle a change event from a listener
        
        Args:
            event: Change event to process
        """
        with self.metrics_lock:
            self.metrics['events_received'] += 1
            self.metrics['last_event_time'] = datetime.now()
        
        if self.enable_batching:
            with self.queue_lock:
                self.event_queue.append(event)
                
                if len(self.event_queue) >= self.batch_size:
                    batch = self.event_queue.copy()
                    self.event_queue.clear()
                    self._process_batch(batch)
        else:
            self._process_event(event)
    
    def _batch_processor(self) -> None:
        """Background thread to process batches on timeout"""
        last_process_time = time.time()
        
        while not self.stop_batching.is_set():
            time.sleep(0.5)
            
            current_time = time.time()
            elapsed = current_time - last_process_time
            
            if elapsed >= self.batch_timeout:
                with self.queue_lock:
                    if self.event_queue:
                        batch = self.event_queue.copy()
                        self.event_queue.clear()
                        self._process_batch(batch)
                
                last_process_time = current_time
    
    def _process_batch(self, events: List[ChangeEvent]) -> None:
        """Process a batch of events"""
        if not events:
            return
        
        logger.debug(f"Processing batch of {len(events)} events")
        
        for handler in self.handlers:
            handler_events = [e for e in events if handler.can_handle(e)]
            
            if handler_events:
                try:
                    handler.handle_batch(handler_events)
                    
                    with self.metrics_lock:
                        self.metrics['events_processed'] += len(handler_events)
                        self.metrics['batches_processed'] += 1
                        
                except Exception as e:
                    logger.error(f"Error in handler {handler.__class__.__name__}: {e}")
                    
                    with self.metrics_lock:
                        self.metrics['events_failed'] += len(handler_events)
                        self.metrics['errors'].append({
                            'handler': handler.__class__.__name__,
                            'error': str(e),
                            'timestamp': datetime.now(),
                            'event_count': len(handler_events)
                        })
    
    def _process_event(self, event: ChangeEvent) -> None:
        """Process a single event immediately"""
        for handler in self.handlers:
            if handler.can_handle(event):
                try:
                    handler.handle_change(event)
                    
                    with self.metrics_lock:
                        self.metrics['events_processed'] += 1
                        
                except Exception as e:
                    logger.error(f"Error in handler {handler.__class__.__name__}: {e}")
                    
                    with self.metrics_lock:
                        self.metrics['events_failed'] += 1
                        self.metrics['errors'].append({
                            'handler': handler.__class__.__name__,
                            'error': str(e),
                            'timestamp': datetime.now(),
                            'event': str(event)
                        })
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all CDC listeners and overall metrics"""
        status = {
            'listeners': {},
            'handlers': [h.__class__.__name__ for h in self.handlers],
            'metrics': self.metrics.copy(),
            'batching': {
                'enabled': self.enable_batching,
                'batch_size': self.batch_size,
                'batch_timeout': self.batch_timeout,
                'queue_size': len(self.event_queue)
            }
        }
        
        for name, listener in self.listeners.items():
            try:
                status['listeners'][name] = listener.get_status()
            except Exception as e:
                status['listeners'][name] = {'error': str(e)}
        
        return status
    
    def cleanup_all(self) -> None:
        """Clean up all CDC resources"""
        for name, listener in self.listeners.items():
            try:
                listener.cleanup()
                logger.info(f"Cleaned up CDC listener: {name}")
            except Exception as e:
                logger.error(f"Error cleaning up listener '{name}': {e}")

