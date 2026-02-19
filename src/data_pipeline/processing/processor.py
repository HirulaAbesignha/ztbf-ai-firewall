
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
   
    async def _flush_batch(self):
        """Flush accumulated batch to storage"""
        if not self.batch:
            return
        
        try:
            batch_size = len(self.batch)
            logger.info(f"💾 Flushing batch of {batch_size} events to storage...")
            
            # Write to storage
            self.storage.write_events(self.batch, tier="hot")
            
            self.stats["stored"] += batch_size
            
            # Clear batch
            self.batch = []
            self.last_flush = datetime.utcnow()
            
            logger.info(f"✅ Batch flushed successfully")
        
        except Exception as e:
            logger.error(f"Error flushing batch: {e}", exc_info=True)
            self.stats["errors"] += 1
            
            # On flush error, don't clear batch - will retry on next flush
    
    async def _report_stats(self):
        """Periodically report processing statistics"""
        while self.running:
            try:
                await asyncio.sleep(60)  # Report every minute
                
                if self.stats["started_at"]:
                    uptime = (datetime.utcnow() - self.stats["started_at"]).seconds
                    rate = self.stats["processed"] / uptime if uptime > 0 else 0
                    
                    logger.info("📊 Processing Statistics:")
                    logger.info(f"   - Processed: {self.stats['processed']:,} ({rate:.1f} events/sec)")
                    logger.info(f"   - Normalized: {self.stats['normalized']:,}")
                    logger.info(f"   - Enriched: {self.stats['enriched']:,}")
                    logger.info(f"   - Stored: {self.stats['stored']:,}")
                    logger.info(f"   - Errors: {self.stats['errors']}")
                    logger.info(f"   - Retries: {self.stats['retries']}")
                    logger.info(f"   - Queue size: {self.event_queue.qsize()}")
                    logger.info(f"   - Uptime: {uptime}s")
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Stats reporting error: {e}")
    
    def _log_final_stats(self):
        """Log final statistics on shutdown"""
        if self.stats["started_at"]:
            uptime = (datetime.utcnow() - self.stats["started_at"]).seconds
            rate = self.stats["processed"] / uptime if uptime > 0 else 0
            
            logger.info("=" * 60)
            logger.info("📊 FINAL PROCESSING STATISTICS")
            logger.info("=" * 60)
            logger.info(f"Total Processed:  {self.stats['processed']:,}")
            logger.info(f"Total Stored:     {self.stats['stored']:,}")
            logger.info(f"Total Errors:     {self.stats['errors']}")
            logger.info(f"Total Retries:    {self.stats['retries']}")
            logger.info(f"Average Rate:     {rate:.1f} events/sec")
            logger.info(f"Total Uptime:     {uptime}s")
            logger.info("=" * 60)


# ===== MAIN =====

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="ZTBF Event Processor")
    parser.add_argument("--workers", type=int, default=8, help="Number of worker threads")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for storage")
    parser.add_argument("--storage", type=str, default="data/events", help="Storage path")
    
    args = parser.parse_args()
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    # Initialize queue (shared with ingestion API)
    queue_config = QueueConfig(
        max_memory_size=100_000,
        disk_buffer_path="data/queue_overflow.db",
        overflow_strategy="disk"
    )
    event_queue = HybridQueue(queue_config)
    
    # Initialize processor
    processor_config = ProcessorConfig(
        num_workers=args.workers,
        batch_size=args.batch_size,
        storage_path=args.storage
    )
    processor = EventProcessor(event_queue, processor_config)
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        processor.signal_shutdown()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start processor
    try:
        await processor.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        processor.signal_shutdown()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        event_queue.close()


if __name__ == "__main__":
    asyncio.run(main())
