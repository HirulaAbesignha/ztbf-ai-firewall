
"""
Main Event Processor for ZTBF
"""

import asyncio
import logging
import signal
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from data_pipeline.ingestion.queue import HybridQueue, QueueConfig
from data_pipeline.processing.normalizer import EventNormalizer
from data_pipeline.processing.enricher import EventEnricher, EnricherConfig
from data_pipeline.storage.storage_layer import LocalStorageLayer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/processor.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ProcessorConfig:
    """Configuration for event processor"""
    num_workers: int = 8
    batch_size: int = 100
    batch_timeout_seconds: int = 5
    storage_path: str = "data/events"
    max_retries: int = 3
    enable_stats: bool = True


class EventProcessor:
    """
    Main event processor orchestrating the pipeline
    
    Manages:
    - Worker pool for parallel processing
    - Event normalization and enrichment
    - Storage persistence
    - Error handling and retries
    - Statistics tracking
    """
    
    def __init__(
        self,
        event_queue: HybridQueue,
        config: Optional[ProcessorConfig] = None
    ):
        """
        Initialize event processor
        
        Args:
            event_queue: Queue to read events from
            config: Processor configuration
        """
        self.config = config or ProcessorConfig()
        self.event_queue = event_queue
        
        # Initialize components
        self.normalizer = EventNormalizer()
        self.enricher = EventEnricher(EnricherConfig())
        self.storage = LocalStorageLayer(self.config.storage_path)
        
        # Worker management
        self.workers: List[asyncio.Task] = []
        self.running = False
        self.shutdown_event = asyncio.Event()
        
        # Statistics
        self.stats = {
            "processed": 0,
            "normalized": 0,
            "enriched": 0,
            "stored": 0,
            "errors": 0,
            "retries": 0,
            "started_at": None
        }
        
        # Event batches for micro-batching
        self.batch: List[Dict[str, Any]] = []
        self.last_flush = datetime.utcnow()
        
        logger.info("Event Processor initialized")
        logger.info(f"   - Workers: {self.config.num_workers}")
        logger.info(f"   - Batch size: {self.config.batch_size}")
        logger.info(f"   - Storage: {self.config.storage_path}")
    
    async def start(self):
        """Start the event processor with worker pool"""
        self.running = True
        self.stats["started_at"] = datetime.utcnow()
        
        logger.info("Starting Event Processor...")
        
        # Start worker pool
        for worker_id in range(self.config.num_workers):
            worker = asyncio.create_task(self._worker(worker_id))
            self.workers.append(worker)
        
        logger.info(f"Started {len(self.workers)} workers")
        
        # Start statistics reporter
        stats_task = asyncio.create_task(self._report_stats())
        
        # Wait for shutdown signal
        await self.shutdown_event.wait()
        
        # Cleanup
        stats_task.cancel()
        await self.stop()
    
    async def stop(self):
        """Stop the event processor gracefully"""
        logger.info("Stopping Event Processor...")
        
        self.running = False
        
        # Cancel all workers
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        
        # Flush remaining batch
        if self.batch:
            await self._flush_batch()
        
        # Log final statistics
        self._log_final_stats()
        
        logger.info("Event Processor stopped")
    
    def signal_shutdown(self):
        """Signal graceful shutdown"""
        logger.info("Shutdown signal received")
        self.shutdown_event.set()
    
    async def _worker(self, worker_id: int):
        """
        Worker coroutine that processes events
        
        Args:
            worker_id: Unique worker identifier
        """
        logger.info(f"Worker {worker_id} started")
        
        while self.running:
            try:
                # Get event from queue
                event = await self.event_queue.get(timeout=1.0)
                
                if event is None:
                    # No event available, continue
                    continue
                
                # Process event
                processed_event = await self._process_event(event, worker_id)
                
                if processed_event:
                    # Add to batch
                    self.batch.append(processed_event)
                    self.stats["processed"] += 1
                    
                    # Flush if batch is full or timeout reached
                    if len(self.batch) >= self.config.batch_size:
                        await self._flush_batch()
                    elif (datetime.utcnow() - self.last_flush).seconds >= self.config.batch_timeout_seconds:
                        await self._flush_batch()
            
            except asyncio.CancelledError:
                logger.info(f"👷 Worker {worker_id} cancelled")
                break
            
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}", exc_info=True)
                self.stats["errors"] += 1
                await asyncio.sleep(0.1)
        
        logger.info(f"👷 Worker {worker_id} stopped")
    
    async def _process_event(
        self,
        raw_event: Dict[str, Any],
        worker_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Process a single event through the pipeline
        
        Args:
            raw_event: Raw event from queue
            worker_id: Worker processing this event
        
        Returns:
            Processed event or None if processing failed
        """
        retry_count = 0
        
        while retry_count <= self.config.max_retries:
            try:
                # Step 1: Normalize
                normalized_event = await self.normalizer.normalize(raw_event)
                self.stats["normalized"] += 1
                
                logger.debug(f"Worker {worker_id}: Normalized event {normalized_event.get('raw_event_id')}")
                
                # Step 2: Enrich
                enriched_event = await self.enricher.enrich(normalized_event)
                self.stats["enriched"] += 1
                
                logger.debug(f"Worker {worker_id}: Enriched event {enriched_event.get('raw_event_id')}")
                
                return enriched_event
            
            except Exception as e:
                retry_count += 1
                self.stats["retries"] += 1
                
                if retry_count <= self.config.max_retries:
                    logger.warning(
                        f"Worker {worker_id}: Processing error (retry {retry_count}/{self.config.max_retries}): {e}"
                    )
                    await asyncio.sleep(0.1 * retry_count)  # Exponential backoff
                else:
                    logger.error(
                        f"Worker {worker_id}: Processing failed after {self.config.max_retries} retries: {e}"
                    )
                    self.stats["errors"] += 1
                    return None
