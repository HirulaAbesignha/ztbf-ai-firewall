# Data Pipeline Architecture: ZTBF Phase 1

**Version**: 1.0  
**Date**: 2025-01-08  
**Status**: Phase 1 - Implementation Ready

---

## Executive Summary

This document defines the **Behavior Data Collection and Streaming Pipeline** for ZTBF. The pipeline is designed to be:
- **Free-first**: Runs locally without cloud costs
- **Production-ready**: Scales to 50,000 events/second
- **Privacy-conscious**: Metadata-only, no payload inspection
- **ML-optimized**: Schema designed for feature engineering

---

## Architecture Overview

### Design Principles

1. **Streaming-First with Micro-Batching**
   - Primary: Async streaming (Python asyncio)
   - Fallback: Micro-batch processing (5-second windows)
   - No mandatory Kafka for MVP

2. **Backpressure Support**
   - In-memory queues with overflow to disk
   - Graceful degradation under load
   - Circuit breaker patterns

3. **Plug-and-Play Sources**
   - Standardized ingestion API
   - Source-specific adapters
   - Easy to add new sources later

4. **Lambda Architecture (Simplified)**
   - Speed Layer: Real-time streaming (asyncio)
   - Batch Layer: Historical processing (Pandas/Polars)
   - Serving Layer: Unified query interface

---