"""
Hybrid Queue Implementation for ZTBF

"""

import asyncio
import sqlite3
import json
import time
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class QueueConfig:
    """Configuration for HybridQueue"""
    max_memory_size: int = 100_000  # Maximum events in memory
    disk_buffer_path: str = "data/queue_overflow.db"
    overflow_strategy: str = "disk"  # "disk" or "drop"
    enable_stats: bool = True


class DiskBuffer:
    """
    SQLite-based disk buffer for overflow events
    Provides persistent storage when memory queue is full
    """
    
    def __init__(self, db_path: str):
        """
        Initialize disk buffer
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()
        
        logger.info(f"Disk buffer initialized: {db_path}")
    
    def _init_db(self):
        """Create tables and indexes"""
        cursor = self.conn.cursor()
        
        # Events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_buffer (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                event_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Index for timestamp-based retrieval
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON event_buffer(timestamp)
        """)
        
        # Index for ID-based retrieval
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_id 
            ON event_buffer(id)
        """)
        
        self.conn.commit()
        logger.info("Disk buffer tables created")
    
    async def write(self, event: Dict[str, Any]) -> bool:
        """
        Write event to disk buffer
        
        Args:
            event: Event dictionary to write
        
        Returns:
            True if successful, False otherwise
        """
        try:
            event_json = json.dumps(event)
            timestamp = time.time()
            
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO event_buffer (timestamp, event_json) VALUES (?, ?)",
                (timestamp, event_json)
            )
            self.conn.commit()
            
            return True
        
        except Exception as e:
            logger.error(f"Error writing to disk buffer: {e}")
            return False
    
    async def read(self) -> Optional[Dict[str, Any]]:
        """
        Read oldest event from disk buffer (FIFO)
        
        Returns:
            Event dictionary or None if buffer is empty
        """
        try:
            cursor = self.conn.cursor()
            
            # Get oldest event
            cursor.execute("""
                SELECT id, event_json 
                FROM event_buffer 
                ORDER BY id 
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            
            if row:
                event_id, event_json = row
                event = json.loads(event_json)
                
                # Delete retrieved event
                cursor.execute(
                    "DELETE FROM event_buffer WHERE id = ?",
                    (event_id,)
                )
                self.conn.commit()
                
                return event
            
            return None
        
        except Exception as e:
            logger.error(f"Error reading from disk buffer: {e}")
            return None
    
    def get_size(self) -> int:
        """
        Get number of events in disk buffer
        
        Returns:
            Count of buffered events
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM event_buffer")
            count = cursor.fetchone()[0]
            return count
        except Exception as e:
            logger.error(f"Error getting disk buffer size: {e}")
            return 0
    
    def clear(self):
        """Clear all events from disk buffer"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM event_buffer")
            self.conn.commit()
            logger.info("Disk buffer cleared")
        except Exception as e:
            logger.error(f"Error clearing disk buffer: {e}")
    
    def close(self):
        """Close database connection"""
        self.conn.close()
        logger.info("Disk buffer closed")

class HybridQueue:
    """
    Hybrid in-memory + disk queue
    
    Provides high-performance in-memory queuing with automatic
    overflow to disk when memory is full.
    
    Usage:
        config = QueueConfig(max_memory_size=100_000)
        queue = HybridQueue(config)
        
        # Put event
        success = await queue.put(event)
        
        # Get event
        event = await queue.get()
    """
    
    def __init__(self, config: QueueConfig):
        """
        Initialize hybrid queue
        
        Args:
            config: Queue configuration
        """
        self.config = config
        
        # In-memory queue
        self.memory_queue = asyncio.Queue(maxsize=config.max_memory_size)
        
        # Disk buffer
        self.disk_buffer = DiskBuffer(config.disk_buffer_path)
        
        # Statistics
        self.stats = {
            "enqueued": 0,
            "dequeued": 0,
            "overflowed": 0,
            "dropped": 0,
            "disk_reads": 0,
            "disk_writes": 0,
            "errors": 0
        }
        
        # Lock for thread safety
        self.lock = asyncio.Lock()
        
        logger.info("🔄 Hybrid queue initialized")
        logger.info(f"   - Memory capacity: {config.max_memory_size:,} events")
        logger.info(f"   - Overflow strategy: {config.overflow_strategy}")
    
    async def put(self, event: Dict[str, Any], timeout: float = 1.0) -> bool:
        """
        Put event in queue
        
        Args:
            event: Event dictionary to enqueue
            timeout: Timeout in seconds
        
        Returns:
            True if accepted, False if dropped
        """
        try:
            # Try to put in memory queue (non-blocking)
            self.memory_queue.put_nowait(event)
            self.stats["enqueued"] += 1
            return True
        
        except asyncio.QueueFull:
            # Memory queue is full - handle overflow
            return await self._handle_overflow(event)
        
        except Exception as e:
            logger.error(f"Error putting event in queue: {e}")
            self.stats["errors"] += 1
            return False
    
    async def _handle_overflow(self, event: Dict[str, Any]) -> bool:
        """
        Handle overflow when memory queue is full
        
        Args:
            event: Event that caused overflow
        
        Returns:
            True if handled, False if dropped
        """
        if self.config.overflow_strategy == "disk":
            # Write to disk buffer
            success = await self.disk_buffer.write(event)
            
            if success:
                self.stats["overflowed"] += 1
                self.stats["disk_writes"] += 1
                logger.debug("📦 Event overflowed to disk")
                return True
            else:
                self.stats["dropped"] += 1
                logger.warning("⚠️  Failed to overflow event to disk")
                return False
        
        elif self.config.overflow_strategy == "drop":
            # Drop event
            self.stats["dropped"] += 1
            logger.warning("⚠️  Event dropped (queue full)")
            return False
        
        else:
            logger.error(f"Unknown overflow strategy: {self.config.overflow_strategy}")
            self.stats["dropped"] += 1
            return False
    
    async def get(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """
        Get event from queue (FIFO)
        
        Prioritizes memory queue, falls back to disk buffer
        
        Args:
            timeout: Timeout in seconds
        
        Returns:
            Event dictionary or None if queue is empty
        """
        try:
            # Try to get from memory queue (with timeout)
            event = await asyncio.wait_for(
                self.memory_queue.get(),
                timeout=timeout
            )
            
            self.stats["dequeued"] += 1
            
            # After dequeuing from memory, check if we can refill from disk
            await self._refill_from_disk()
            
            return event
        
        except asyncio.TimeoutError:
            # Memory queue is empty, try disk buffer
            event = await self.disk_buffer.read()
            
            if event:
                self.stats["dequeued"] += 1
                self.stats["disk_reads"] += 1
                logger.debug("📦 Event retrieved from disk buffer")
            
            return event
        
        except Exception as e:
            logger.error(f"Error getting event from queue: {e}")
            self.stats["errors"] += 1
            return None
    
    async def _refill_from_disk(self):
        """
        Refill memory queue from disk buffer when space is available
        Non-blocking, runs in background
        """
        # Check if we have space in memory queue
        if self.memory_queue.qsize() < self.config.max_memory_size * 0.5:
            # We have space - try to refill from disk
            disk_size = self.disk_buffer.get_size()
            
            if disk_size > 0:
                # Refill up to 10% of capacity at a time
                refill_count = min(
                    disk_size,
                    int(self.config.max_memory_size * 0.1)
                )
                
                for _ in range(refill_count):
                    event = await self.disk_buffer.read()
                    if event:
                        try:
                            self.memory_queue.put_nowait(event)
                            self.stats["disk_reads"] += 1
                        except asyncio.QueueFull:
                            # Memory filled up again, stop refilling
                            # Put event back in disk
                            await self.disk_buffer.write(event)
                            break
                
                if refill_count > 0:
                    logger.info(f"📤 Refilled {refill_count} events from disk to memory")
    
    def qsize(self) -> int:
        """
        Get total queue size (memory + disk)
        
        Returns:
            Total number of events in queue
        """
        memory_size = self.memory_queue.qsize()
        disk_size = self.disk_buffer.get_size()
        return memory_size + disk_size
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics
        
        Returns:
            Dictionary of statistics
        """
        memory_size = self.memory_queue.qsize()
        disk_size = self.disk_buffer.get_size()
        
        return {
            **self.stats,
            "memory_queue_size": memory_size,
            "disk_buffer_size": disk_size,
            "total_queue_size": memory_size + disk_size,
            "memory_utilization": memory_size / self.config.max_memory_size,
            "is_memory_full": memory_size >= self.config.max_memory_size
        }
    
    def reset_stats(self):
        """Reset statistics counters"""
        self.stats = {
            "enqueued": 0,
            "dequeued": 0,
            "overflowed": 0,
            "dropped": 0,
            "disk_reads": 0,
            "disk_writes": 0,
            "errors": 0
        }
        logger.info("📊 Queue statistics reset")
    
    async def clear(self):
        """Clear all events from queue"""
        async with self.lock:
            # Clear memory queue
            while not self.memory_queue.empty():
                try:
                    self.memory_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            
            # Clear disk buffer
            self.disk_buffer.clear()
            
            logger.info("🗑️  Queue cleared")
    
    def close(self):
        """Close queue and cleanup resources"""
        self.disk_buffer.close()
        logger.info("🔄 Hybrid queue closed")

