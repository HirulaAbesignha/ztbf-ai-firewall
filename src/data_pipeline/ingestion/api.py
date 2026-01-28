
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
    logger.info("Shutting down Ingestion API...")
    
    # Log final statistics
    logger.info(f"Final Statistics:")
    logger.info(f"   - Total ingested: {metrics['events_ingested_total']:,}")
    logger.info(f"   - Total dropped: {metrics['events_dropped_total']:,}")
    logger.info(f"   - By source: {metrics['events_by_source']}")

# ===== FASTAPI APP =====

app = FastAPI(
    title="ZTBF Ingestion API",
    description="Event ingestion API for Zero-Trust Behavior Firewall",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware (for local development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== AUTHENTICATION =====

async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """
    Verify API key from header
    
    Args:
        x_api_key: API key from X-API-Key header
    
    Returns:
        API key if valid
    
    Raises:
        HTTPException: If API key is invalid
    """
    if x_api_key not in APIConfig.API_KEYS:
        logger.warning(f"Invalid API key attempt: {x_api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return x_api_key


# ===== RATE LIMITING =====

# Simple in-memory rate limiter (use Redis in production)
rate_limit_store: Dict[str, List[datetime]] = {}

async def check_rate_limit(api_key: str) -> bool:
    """
    Check if API key has exceeded rate limit
    
    Args:
        api_key: API key to check
    
    Returns:
        True if within limit, False if exceeded
    """
    now = datetime.utcnow()
    window_start = now.replace(second=0, microsecond=0)
    
    # Initialize if first request
    if api_key not in rate_limit_store:
        rate_limit_store[api_key] = []
    
    # Remove old timestamps (older than 1 minute)
    rate_limit_store[api_key] = [
        ts for ts in rate_limit_store[api_key]
        if (now - ts).total_seconds() < 60
    ]
    
    # Check limit
    if len(rate_limit_store[api_key]) >= APIConfig.RATE_LIMIT_PER_MINUTE:
        return False
    
    # Add current timestamp
    rate_limit_store[api_key].append(now)
    return True

# ===== HEALTH & STATUS ENDPOINTS =====

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    Returns service health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": (
            datetime.utcnow() - metrics["api_started_at"]
        ).total_seconds() if metrics["api_started_at"] else 0,
        "queue": {
            "size": event_queue.memory_queue.qsize() if event_queue else 0,
            "max_size": event_queue.config.max_memory_size if event_queue else 0
        }
    }


@app.get("/metrics")
async def get_metrics():
    """
    Prometheus-style metrics endpoint
    Returns operational metrics
    """
    queue_size = event_queue.memory_queue.qsize() if event_queue else 0
    
    return {
        "events_ingested_total": metrics["events_ingested_total"],
        "events_dropped_total": metrics["events_dropped_total"],
        "events_by_source": metrics["events_by_source"],
        "errors_total": metrics["errors_total"],
        "queue_size": queue_size,
        "queue_utilization": queue_size / event_queue.config.max_memory_size if event_queue else 0,
        "uptime_seconds": (
            datetime.utcnow() - metrics["api_started_at"]
        ).total_seconds() if metrics["api_started_at"] else 0
    }


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "ZTBF Ingestion API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "ingest_azure_ad": "/ingest/azure_ad",
            "ingest_cloudtrail": "/ingest/cloudtrail",
            "ingest_api_gateway": "/ingest/api_gateway",
            "ingest_batch": "/ingest/batch"
        },
        "documentation": "/docs"
    }

# ===== INGESTION ENDPOINTS =====

@app.post("/ingest/azure_ad")
async def ingest_azure_ad(
    event: Dict[str, Any],
    api_key: str = Header(..., alias="X-API-Key")
):
    """
    Ingest Azure AD sign-in event
    
    Args:
        event: Azure AD sign-in log event (Microsoft Graph API format)
        api_key: API key for authentication
    
    Returns:
        Ingestion confirmation with event ID
    
    Raises:
        HTTPException: If validation fails or queue is full
    """
    # Verify API key
    await verify_api_key(api_key)
    
    # Check rate limit
    if not await check_rate_limit(api_key):
        logger.warning(f"Rate limit exceeded for key: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    try:
        # Validate schema
        validated_event = AzureADSignInEvent(**event)
        
        # Add metadata
        enriched_event = {
            **event,
            "source_type": "azure_ad",
            "ingestion_timestamp": datetime.utcnow().isoformat(),
            "ingestion_id": f"ingest_{datetime.utcnow().timestamp()}"
        }
        
        # Queue for processing
        success = await event_queue.put(enriched_event, timeout=1.0)
        
        if success:
            metrics["events_ingested_total"] += 1
            metrics["events_by_source"]["azure_ad"] += 1
            
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "status": "accepted",
                    "ingestion_id": enriched_event["ingestion_id"],
                    "source_type": "azure_ad"
                }
            )
        else:
            metrics["events_dropped_total"] += 1
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Queue full, event dropped"
            )
    
    except ValidationError as e:
        metrics["errors_total"] += 1
        logger.error(f"Validation error for Azure AD event: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        metrics["errors_total"] += 1
        logger.error(f"Error ingesting Azure AD event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.post("/ingest/cloudtrail")
async def ingest_cloudtrail(
    event: Dict[str, Any],
    api_key: str = Header(..., alias="X-API-Key")
):
    """
    Ingest AWS CloudTrail event
    
    Args:
        event: CloudTrail event record
        api_key: API key for authentication
    
    Returns:
        Ingestion confirmation with event ID
    """
    await verify_api_key(api_key)
    
    if not await check_rate_limit(api_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    try:
        # Validate schema
        validated_event = CloudTrailEvent(**event)
        
        # Add metadata
        enriched_event = {
            **event,
            "source_type": "cloudtrail",
            "ingestion_timestamp": datetime.utcnow().isoformat(),
            "ingestion_id": f"ingest_{datetime.utcnow().timestamp()}"
        }
        
        # Queue for processing
        success = await event_queue.put(enriched_event, timeout=1.0)
        
        if success:
            metrics["events_ingested_total"] += 1
            metrics["events_by_source"]["cloudtrail"] += 1
            
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "status": "accepted",
                    "ingestion_id": enriched_event["ingestion_id"],
                    "source_type": "cloudtrail"
                }
            )
        else:
            metrics["events_dropped_total"] += 1
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Queue full, event dropped"
            )
    
    except ValidationError as e:
        metrics["errors_total"] += 1
        logger.error(f"Validation error for CloudTrail event: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        metrics["errors_total"] += 1
        logger.error(f"Error ingesting CloudTrail event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.post("/ingest/api_gateway")
async def ingest_api_gateway(
    event: Dict[str, Any],
    api_key: str = Header(..., alias="X-API-Key")
):
    """
    Ingest API Gateway log event
    
    Args:
        event: API Gateway log entry
        api_key: API key for authentication
    
    Returns:
        Ingestion confirmation with event ID
    """
    await verify_api_key(api_key)
    
    if not await check_rate_limit(api_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    try:
        # Validate schema
        validated_event = APIGatewayLog(**event)
        
        # Add metadata
        enriched_event = {
            **event,
            "source_type": "api_gateway",
            "ingestion_timestamp": datetime.utcnow().isoformat(),
            "ingestion_id": f"ingest_{datetime.utcnow().timestamp()}"
        }
        
        # Queue for processing
        success = await event_queue.put(enriched_event, timeout=1.0)
        
        if success:
            metrics["events_ingested_total"] += 1
            metrics["events_by_source"]["api_gateway"] += 1
            
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "status": "accepted",
                    "ingestion_id": enriched_event["ingestion_id"],
                    "source_type": "api_gateway"
                }
            )
        else:
            metrics["events_dropped_total"] += 1
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Queue full, event dropped"
            )
    
    except ValidationError as e:
        metrics["errors_total"] += 1
        logger.error(f"Validation error for API Gateway event: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        metrics["errors_total"] += 1
        logger.error(f"Error ingesting API Gateway event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.post("/ingest/batch")
async def ingest_batch(
    events: List[Dict[str, Any]],
    source_type: str,
    api_key: str = Header(..., alias="X-API-Key")
):
    """
    Ingest multiple events in a single request (batch ingestion)
    
    Args:
        events: List of events to ingest
        source_type: Source type (azure_ad, cloudtrail, api_gateway)
        api_key: API key for authentication
    
    Returns:
        Batch ingestion summary
    """
    await verify_api_key(api_key)
    
    # Validate batch size
    if len(events) > APIConfig.MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Batch size exceeds maximum of {APIConfig.MAX_BATCH_SIZE}"
        )
    
    # Validate source type
    if source_type not in ["azure_ad", "cloudtrail", "api_gateway"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid source_type: {source_type}"
        )
    
    results = {
        "total": len(events),
        "accepted": 0,
        "rejected": 0,
        "errors": []
    }
    
    for idx, event in enumerate(events):
        try:
            # Add source type and metadata
            event["source_type"] = source_type
            event["ingestion_timestamp"] = datetime.utcnow().isoformat()
            event["ingestion_id"] = f"ingest_batch_{datetime.utcnow().timestamp()}_{idx}"
            
            # Queue for processing
            success = await event_queue.put(event, timeout=0.1)
            
            if success:
                results["accepted"] += 1
                metrics["events_ingested_total"] += 1
                metrics["events_by_source"][source_type] += 1
            else:
                results["rejected"] += 1
                results["errors"].append(f"Event {idx}: Queue full")
        
        except Exception as e:
            results["rejected"] += 1
            results["errors"].append(f"Event {idx}: {str(e)}")
            metrics["errors_total"] += 1
    
    return JSONResponse(
        status_code=status.HTTP_207_MULTI_STATUS,
        content={
            "status": "batch_processed",
            "results": results
        }
    )
