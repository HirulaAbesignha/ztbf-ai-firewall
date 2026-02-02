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
