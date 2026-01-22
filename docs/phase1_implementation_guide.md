# Phase 1 Implementation Guide
## AI-Driven Zero-Trust Behavior Firewall - Data Pipeline

**Version**: 1.0  
**Date**: 2025-01-08  
**Status**: Ready for Implementation

---

## Overview

Phase 1 delivers a production-ready **Behavior Data Collection and Streaming Pipeline** that:
- ✅ Ingests events from 3 data sources (Azure AD, CloudTrail, API Gateway)
- ✅ Processes 10,000+ events/second
- ✅ Normalizes to unified schema
- ✅ Stores in tiered architecture (hot/warm/cold)
- ✅ Runs 100% free locally (no cloud costs)
- ✅ Scales to production (cloud-compatible)

---

## Repository Structure (Phase 1 Files)

```
ai-zero-trust-behavior-firewall/
├── research/
│   └── threat_model.md                    ✅ Created (Phase 0)
│
├── architecture/
│   ├── system_design.md                   ✅ Created (Phase 0)
│   └── data_pipeline_design.md            ✅ Created (Phase 1)
│
├── src/
│   └── data_pipeline/
│       ├── __init__.py
│       ├── schemas/
│       │   ├── __init__.py
│       │   └── unified_schema.py          ✅ Created (Phase 1)
│       │
│       ├── ingestion/
│       │   ├── __init__.py
│       │   ├── api.py                     🔲 TO CREATE
│       │   ├── file_watcher.py            🔲 TO CREATE
│       │   └── queue.py                   🔲 TO CREATE
│       │
│       ├── processing/
│       │   ├── __init__.py
│       │   ├── normalizer.py              🔲 TO CREATE
│       │   ├── enricher.py                🔲 TO CREATE
│       │   └── processor.py               🔲 TO CREATE
│       │
│       ├── storage/
│       │   ├── __init__.py
│       │   └── storage_layer.py           ✅ Created (Phase 1)
│       │
│       └── generators/
│           ├── __init__.py
│           └── synthetic_logs.py          ✅ Created (Phase 1)
│
├── configs/
│   ├── pipeline_config.yaml               🔲 TO CREATE
│   └── storage_config.yaml                🔲 TO CREATE
│
├── deployment/
│   ├── docker/
│   │   ├── Dockerfile.pipeline            🔲 TO CREATE
│   │   └── docker-compose.yml             🔲 TO CREATE
│   │
│   └── local/
│       └── setup_minio.sh                 🔲 TO CREATE
│
├── tests/
│   └── unit/
│       └── test_pipeline.py               🔲 TO CREATE
│
├── docs/
│   └── phase1_implementation_guide.md     ✅ Created (Phase 1)
│
├── requirements.txt                       🔲 TO CREATE
└── README.md                              🔲 TO UPDATE
```

---

## Technology Stack

### Core Dependencies

```
# requirements.txt

# Data Processing
pandas==2.1.4
pyarrow==14.0.1
polars==0.20.3                 # Optional: faster alternative to pandas

# Web Framework
fastapi==0.108.0
uvicorn[standard]==0.25.0
pydantic==2.5.3

# Storage
boto3==1.34.20                 # S3/MinIO client
minio==7.2.3                   # MinIO-specific client (optional)

# Message Queue (Optional)
aiofiles==23.2.1               # Async file I/O

# HTTP Client
aiohttp==3.9.1
requests==2.31.0

# Utilities
python-dotenv==1.0.0
pyyaml==6.0.1
python-dateutil==2.8.2

# Testing
pytest==7.4.3
pytest-asyncio==0.23.2
pytest-cov==4.1.0

# Development
black==23.12.1
flake8==7.0.0
mypy==1.8.0
```

### External Services (Local MVP)

```yaml
# docker-compose.yml services

services:
  minio:
    image: minio/minio:latest
    container_name: ztbf-minio
    ports:
      - "9000:9000"      # API
      - "9001:9001"      # Console
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
  
  # Optional: Redis for caching
  redis:
    image: redis:7-alpine
    container_name: ztbf-redis
    ports:
      - "6379:6379"
```

---

## Implementation Steps

### Step 1: Environment Setup

```bash
# Clone repository
git clone https://github.com/your-org/ai-zero-trust-behavior-firewall.git
cd ai-zero-trust-behavior-firewall

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start local services
docker-compose up -d minio

# Verify MinIO is running
curl http://localhost:9000/minio/health/live
```

### Step 2: Generate Synthetic Data

```bash
# Generate 10,000 normal events
python src/data_pipeline/generators/synthetic_logs.py \
    --count 10000 \
    --output data/synthetic_events_normal.json \
    --scenario normal

# Generate attack scenarios
python src/data_pipeline/generators/synthetic_logs.py \
    --scenario credential_theft \
    --output data/attack_credential_theft.json

python src/data_pipeline/generators/synthetic_logs.py \
    --scenario privilege_escalation \
    --output data/attack_privilege_esc.json
```

### Step 3: Start Ingestion API

```bash
# Run ingestion API
uvicorn src.data_pipeline.ingestion.api:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload

# Verify API is running
curl http://localhost:8000/health
```

### Step 4: Start Stream Processor

```bash
# In a separate terminal
python src/data_pipeline/processing/processor.py \
    --workers 8 \
    --config configs/pipeline_config.yaml
```

### Step 5: Ingest Test Data

```bash
# Send events to API
python scripts/ingest_file.py \
    --file data/synthetic_events_normal.json \
    --api-url http://localhost:8000 \
    --rate 100  # 100 events/second
```

### Step 6: Verify Storage

```bash
# Query stored events
python scripts/query_events.py \
    --start-time "2025-01-08T00:00:00" \
    --end-time "2025-01-08T23:59:59" \
    --source azure_ad \
    --output results.csv
```

---

## Configuration

### Pipeline Configuration

**File: `configs/pipeline_config.yaml`**

```yaml
# Data Pipeline Configuration

ingestion:
  api:
    host: "0.0.0.0"
    port: 8000
    api_keys:
      - "test_key_1"
      - "test_key_2"
  
  queue:
    max_memory_size: 100000  # events
    disk_buffer_path: "data/queue_overflow.db"
    overflow_strategy: "disk"  # "disk" or "drop"

processing:
  workers: 8  # Number of async workers
  batch_size: 1000  # Events per batch
  batch_timeout_seconds: 5
  
  enrichment:
    geoip_enabled: true
    geoip_database: "data/GeoLite2-City.mmdb"  # Download from MaxMind
    entity_metadata_cache_ttl: 3600  # seconds

storage:
  backend: "minio"  # "minio" or "s3"
  endpoint_url: "http://localhost:9000"
  access_key: "minioadmin"
  secret_key: "minioadmin"
  bucket_name: "ztbf-events"
  region: "us-east-1"
  
  tiers:
    hot:
      retention_days: 7
      compression: "snappy"
    warm:
      retention_days: 30
      compression: "snappy"
    cold:
      retention_days: 90
      compression: "gzip"
  
  partitioning:
    - "date"
    - "hour"
    - "source_system"

logging:
  level: "INFO"
  format: "json"
  file: "logs/pipeline.log"
```

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/test_normalizer.py

import pytest
from datetime import datetime
from src.data_pipeline.processing.normalizer import EventNormalizer

def test_normalize_azure_ad_event():
    """Test Azure AD event normalization"""
    normalizer = EventNormalizer()
    
    raw_event = {
        "source_type": "azure_ad",
        "id": "test-id",
        "createdDateTime": "2025-01-08T10:00:00Z",
        "userPrincipalName": "alice@company.com",
        "userId": "user_001",
        "appId": "app-123",
        "ipAddress": "192.168.1.100",
        "status": {"errorCode": 0},
        # ... more fields
    }
    
    normalized = normalizer.normalize(raw_event)
    
    assert normalized["entity_id"] == "alice@company.com"
    assert normalized["entity_type"] == "user"
    assert normalized["event_type"] == "authentication"
    assert normalized["success"] == True
    assert normalized["source_ip"] == "192.168.1.100"

def test_normalize_cloudtrail_event():
    """Test CloudTrail event normalization"""
    # Similar test for CloudTrail
    pass

def test_invalid_source_type():
    """Test handling of invalid source type"""
    normalizer = EventNormalizer()
    
    raw_event = {"source_type": "unknown"}
    
    with pytest.raises(ValueError):
        normalizer.normalize(raw_event)
```

### Integration Tests

```python
# tests/integration/test_pipeline_e2e.py

import pytest
import asyncio
from src.data_pipeline.ingestion.api import app
from src.data_pipeline.processing.processor import AsyncEventProcessor
from src.data_pipeline.storage.storage_layer import LocalStorageLayer

@pytest.mark.asyncio
async def test_end_to_end_pipeline():
    """Test complete pipeline flow"""
    # 1. Generate test event
    test_event = {
        "source_type": "azure_ad",
        "userPrincipalName": "test@company.com",
        # ... complete event
    }
    
    # 2. Send to ingestion API
    response = await client.post("/ingest/azure_ad", json=test_event)
    assert response.status_code == 200
    
    # 3. Wait for processing
    await asyncio.sleep(1)
    
    # 4. Verify storage
    storage = LocalStorageLayer("data/test_events")
    events = storage.read_events(
        start_time=datetime.utcnow() - timedelta(minutes=5),
        end_time=datetime.utcnow()
    )
    
    assert len(events) > 0
    assert events.iloc[0]["entity_id"] == "test@company.com"
```

### Load Testing

```bash
# Use Apache Bench or Locust for load testing

# Apache Bench: 10,000 requests, 100 concurrent
ab -n 10000 -c 100 -p test_event.json \
   -T application/json \
   http://localhost:8000/ingest/azure_ad

# Expected result: >1000 requests/second
```

---

## Monitoring & Observability

### Key Metrics to Track

```python
# metrics.py

from prometheus_client import Counter, Histogram, Gauge

# Ingestion metrics
events_ingested_total = Counter(
    'ztbf_events_ingested_total',
    'Total events ingested',
    ['source_type']
)

events_dropped_total = Counter(
    'ztbf_events_dropped_total',
    'Total events dropped',
    ['reason']
)

# Processing metrics
processing_duration_seconds = Histogram(
    'ztbf_processing_duration_seconds',
    'Event processing duration',
    ['stage']
)

queue_size = Gauge(
    'ztbf_queue_size',
    'Current queue size'
)

# Storage metrics
storage_writes_total = Counter(
    'ztbf_storage_writes_total',
    'Total storage writes',
    ['tier']
)

storage_size_bytes = Gauge(
    'ztbf_storage_size_bytes',
    'Storage size by tier',
    ['tier']
)
```

### Health Check Endpoint

```python
# src/data_pipeline/ingestion/api.py

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "queue_size": event_queue.qsize(),
        "storage": {
            "minio_accessible": check_minio_connection(),
            "disk_space_available": get_disk_space()
        }
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return {
        "events_ingested_total": events_ingested_total._value.get(),
        "queue_size": queue_size._value.get(),
        # ... more metrics
    }
```

---

## Performance Benchmarks

### Target Performance (MVP)

| Metric | Target | Measured |
|--------|--------|----------|
| Ingestion rate | 1,000-10,000 events/sec | TBD |
| Processing latency | < 500ms (p95) | TBD |
| Storage write latency | < 100ms (p95) | TBD |
| Query latency (1 hour) | < 2 seconds | TBD |
| Memory usage | < 2 GB | TBD |
| CPU usage | < 50% (8 cores) | TBD |

### Stress Test Scenarios

1. **Sustained Load**: 5,000 events/sec for 1 hour
2. **Burst Load**: 50,000 events/sec for 1 minute
3. **Large Event Size**: 10KB per event
4. **Long-Running**: 24 hours continuous operation

---

## Troubleshooting

### Common Issues

#### 1. MinIO Connection Failed
```bash
# Check MinIO is running
docker ps | grep minio

# Check MinIO logs
docker logs ztbf-minio

# Test connection
curl http://localhost:9000/minio/health/live
```

#### 2. Queue Overflow
```bash
# Check disk buffer size
du -sh data/queue_overflow.db

# Increase queue size in config
# Edit configs/pipeline_config.yaml
#   queue.max_memory_size: 200000
```

#### 3. Slow Processing
```bash
# Increase worker count
python src/data_pipeline/processing/processor.py --workers 16

# Check CPU usage
top -p $(pgrep -f processor.py)
```

#### 4. Storage Full
```bash
# Check storage usage
python scripts/storage_stats.py

# Run lifecycle management
python scripts/lifecycle_management.py
```

---

## Next Steps (Phase 2)

Once Phase 1 is complete and validated:

1. ✅ Feature Engineering Pipeline
   - Velocity features (login rate, API call rate)
   - Sequence features (action sequences)
   - Graph features (entity relationships)
   - Temporal features (time-of-day, day-of-week)

2. ✅ ML Model Training
   - Isolation Forest (anomaly detection)
   - LSTM Autoencoder (sequence anomaly)
   - Baseline establishment (30-day training)

3. ✅ Model Inference Pipeline
   - Real-time scoring
   - Batch scoring for historical data
   - Model versioning

---

## Success Criteria

Phase 1 is complete when:

- [  ] Ingestion API accepts all 3 event types
- [  ] Events are normalized to unified schema
- [  ] Events are stored in MinIO (hot tier)
- [  ] Can query events by time range
- [  ] Processing handles 1,000+ events/sec
- [  ] Synthetic log generator produces realistic data
- [  ] Unit tests pass (>80% coverage)
- [  ] Integration test passes (end-to-end)
- [  ] Load test passes (10,000 requests)
- [  ] Documentation is complete

---

## References

- [Phase 0: Threat Model](../research/threat_model.md)
- [Phase 0: System Architecture](../architecture/system_design.md)
- [Unified Event Schema](../src/data_pipeline/schemas/unified_schema.py)
- [Storage Layer](../src/data_pipeline/storage/storage_layer.py)
- [Synthetic Log Generator](../src/data_pipeline/generators/synthetic_logs.py)

---

**Status**: Phase 1 Design Complete ✅  
**Next**: Implement remaining components and begin Phase 2