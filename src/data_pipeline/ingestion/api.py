
"""
Ingestion API for ZTBF Data Pipeline

"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
import uvicorn

# Import schemas
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from data_pipeline.schemas.unified_schema import (
    AzureADSignInEvent,
    CloudTrailEvent,
    APIGatewayLog,
    validate_event
)
from data_pipeline.ingestion.queue import HybridQueue, QueueConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ===== CONFIGURATION =====

class APIConfig:
    """API Configuration"""
    HOST = "0.0.0.0"
    PORT = 8000
    API_KEYS = {"test_key", "dev_key"}  # In production: load from env/secrets
    RATE_LIMIT_PER_MINUTE = 10000
    MAX_BATCH_SIZE = 1000


# ===== GLOBAL STATE =====

# Event queue (initialized in lifespan)
event_queue: Optional[HybridQueue] = None

# Metrics
metrics = {
    "events_ingested_total": 0,
    "events_dropped_total": 0,
    "events_by_source": {
        "azure_ad": 0,
        "cloudtrail": 0,
        "api_gateway": 0
    },
    "errors_total": 0,
    "api_started_at": None
}


# ===== LIFESPAN MANAGEMENT =====

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown
    Initializes queue and starts background tasks
    """
    global event_queue
    
    logger.info("Starting ZTBF Ingestion API...")
    
    # Initialize queue
    queue_config = QueueConfig(
        max_memory_size=100_000,
        disk_buffer_path="data/queue_overflow.db",
        overflow_strategy="disk"
    )
    event_queue = HybridQueue(queue_config)
    
    # Record startup time
    metrics["api_started_at"] = datetime.utcnow()
    
    logger.info("Ingestion API started successfully")
    logger.info(f"   - Queue size: {queue_config.max_memory_size:,} events")
    logger.info(f"   - Overflow: {queue_config.overflow_strategy}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Ingestion API...")
    
    # Log final statistics
    logger.info(f"Final Statistics:")
    logger.info(f"   - Total ingested: {metrics['events_ingested_total']:,}")
    logger.info(f"   - Total dropped: {metrics['events_dropped_total']:,}")
    logger.info(f"   - By source: {metrics['events_by_source']}")