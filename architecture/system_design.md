
# System Architecture: AI-Driven Zero-Trust Behavior Firewall (ZTBF)

**Version**: 1.0  
**Date**: 2026-01-01  
**Status**: Phase 0 - Foundation  
**Target Environment**: Cloud-Native (AWS/Azure), Free Development MVP

---

## Architecture Principles

### Design Philosophy
1. **Zero Trust**: Never trust, always verify, assume breach
2. **Cloud-Native**: Containerized, horizontally scalable, infrastructure-as-code
3. **AI-First**: Machine learning at the core, not bolted-on
4. **Privacy-Aware**: Metadata-only analysis, no payload inspection
5. **Explainable**: Every decision traceable and auditable
6. **Free-First MVP**: Local development, no cloud costs during Phases 0-2

### Non-Functional Requirements
- **Latency**: Risk decision < 500ms (real-time blocking)
- **Throughput**: 10,000 events/second (design capacity)
- **Availability**: 99.9% uptime (3-nines)
- **Scalability**: Horizontal scaling for all components
- **Durability**: Event data retained 90 days (configurable)

---

## High-Level System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL DATA SOURCES                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Azure AD │  │CloudTrail│  │ K8s Audit│  │VPC Flow  │  │  APIs    │  │
│  │  Logs    │  │  (AWS)   │  │   Logs   │  │   Logs   │  │ Gateway  │  │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘  │
└────────┼─────────────┼─────────────┼─────────────┼─────────────┼───────┘
         │             │             │             │             │
         └─────────────┴─────────────┴─────────────┴─────────────┘
                                     │
                    ┌─────────────────────────────────┐
                    │   DATA INGESTION LAYER          │
                    │  (Kafka / RabbitMQ / Pulsar)    │
                    │  - Log collectors / agents      │
                    │  - Schema validation            │
                    │  - Buffering & backpressure     │
                    └────────────────┬────────────────┘
                                     │
         ┌───────────────────────────┴───────────────────────────┐
         │                                                       │
         ▼                                                       ▼
┌────────────────────┐                              ┌────────────────────┐
│ RAW EVENT STORAGE  │                              │  STREAM PROCESSOR  │
│   (Time-series)    │                              │    (Spark/Flink)   │
│  - S3 / MinIO      │◄─────────────────────────────│  - Normalization   │
│  - Parquet format  │       Persisted events       │  - Enrichment      │
│  - Partitioned     │                              │  - Deduplication   │
└────────────────────┘                              └─────────┬──────────┘
                                                              │
                    ┌─────────────────────────────────────────┘
                    │
                    ▼
        ┌───────────────────────────┐
        │  FEATURE ENGINEERING      │
        │  - Velocity metrics       │
        │  - Sequence extraction    │
        │  - Graph features         │
        │  - Temporal aggregations  │
        │  - Contextual enrichment  │
        └───────────┬───────────────┘
                    │
         ┌──────────┴──────────┐
         │                     │
         ▼                     ▼
┌─────────────────┐   ┌─────────────────┐
│ FEATURE STORE   │   │  REAL-TIME      │
│  (Redis/Feast)  │   │  FEATURE CACHE  │
│ - Historical    │   │  (Redis)        │
│ - Training data │   │  - Live values  │
└─────────────────┘   └────────┬────────┘
                               │
         ┌─────────────────────┴─────────────────────┐
         │                                           │
         ▼                                           ▼
┌─────────────────────────┐              ┌──────────────────────────┐
│   AI MODEL ENSEMBLE     │              │  BASELINE / PROFILE DB   │
│                         │              │   (PostgreSQL / Mongo)   │
│  ┌──────────────────┐   │              │  - User behavior profile │
│  │ Isolation Forest │   │              │  - Service dependencies  │
│  │   (Anomaly)      │   │              │  - Normal patterns       │
│  └──────────────────┘   │              │  - Risk history          │
│                         │              └──────────────────────────┘
│  ┌──────────────────┐   │
│  │ LSTM Autoencoder │   │
│  │   (Sequence)     │   │
│  └──────────────────┘   │
│                         │
│  ┌──────────────────┐   │
│  │ Graph Neural Net │   │
│  │ (Lateral Movmt)  │   │
│  └──────────────────┘   │
│                         │
│  ┌──────────────────┐   │
│  │ Transformer      │   │
│  │ (Context/Attn)   │   │
│  └──────────────────┘   │
└────────────┬────────────┘
             │
             │ Model predictions
             │ (anomaly scores)
             ▼
┌────────────────────────────────────┐
│   RISK SCORING & DECISION ENGINE   │
│                                    │
│  - Weighted ensemble combiner      │
│  - Business context layer          │
│  - Policy rule engine              │
│  - Risk threshold evaluation       │
│  - Confidence scoring              │
└────────────┬───────────────────────┘
             │
             │ Risk score + decision
             │
         ┌───┴────┐
         │        │
         ▼        ▼
┌────────────┐  ┌──────────────────┐
│ EXPLAINER  │  │  ENFORCEMENT     │
│  (SHAP)    │  │  ORCHESTRATOR    │
│            │  │                  │
│ - Feature  │  │ - Alert (low)    │
│   contrib  │  │ - MFA (medium)   │
│ - Reason   │  │ - Block (high)   │
│   codes    │  │                  │
└─────┬──────┘  └─────────┬────────┘
      │                   │
      │                   │ Enforcement actions
      │                   │
      └────────┬──────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│      DASHBOARDS & ANALYST INTERFACE      │
│                                          │
│  ┌────────────┐  ┌────────────────────┐  │
│  │  Real-time │  │  Investigation UI  │  │
│  │  Alerts    │  │  - Event timeline  │  │
│  └────────────┘  │  - User context    │  │
│                  │  - Risk details    │  │
│  ┌────────────┐  └────────────────────┘  │
│  │  Risk      │                          │
│  │  Trends    │  ┌────────────────────┐  │
│  └────────────┘  │  Feedback Loop     │  │
│                  │  - False positive  │  │
│  ┌────────────┐  │  - Model tuning    │  │
│  │  Entity    │  └────────────────────┘  │
│  │  Profiles  │                          │
│  └────────────┘                          │
└──────────────────────────────────────────┘
```

---

## Component Details

### 1. DATA INGESTION LAYER

**Purpose**: Reliably collect events from multiple sources

**Technologies (MVP)**:
- **Message Queue**: Apache Kafka (Redpanda for lightweight local dev)
- **Log Shippers**: Filebeat, Fluentd, custom collectors
- **API Gateway**: FastAPI endpoints for push-based ingestion

**Key Features**:
- Schema validation (Avro/JSON Schema)
- Buffering for burst traffic
- Backpressure handling
- Dead letter queue for malformed events

**Data Sources**:
```yaml
# Source 1: Azure AD Sign-in Logs
Format: JSON
Schema: Microsoft Graph API format
Fields: userId, timestamp, ipAddress, location, deviceId, riskLevel

# Source 2: AWS CloudTrail
Format: JSON (Gzipped)
Schema: AWS CloudTrail Event format
Fields: userIdentity, eventTime, sourceIPAddress, userAgent, eventName

# Source 3: Kubernetes Audit Logs
Format: JSON
Schema: K8s Audit Event format
Fields: user, verb, objectRef, sourceIPs, userAgent, timestamp

# Source 4: VPC Flow Logs
Format: Space-delimited text → parsed to JSON
Schema: AWS VPC Flow format
Fields: srcaddr, dstaddr, srcport, dstport, protocol, bytes, packets

# Source 5: API Gateway Logs
Format: JSON
Schema: Custom application format
Fields: userId, endpoint, method, statusCode, latency, timestamp
```

**MVP Implementation**:
- File-based ingestion (replay log files into Kafka)
- Synthetic log generator for testing
- Local Kafka instance (Redpanda in Docker)

---

### 2. STREAM PROCESSING

**Purpose**: Normalize, enrich, and prepare events for analysis

**Technologies**:
- **Primary**: Apache Spark Structured Streaming
- **Alternative**: Apache Flink (for lower latency)
- **MVP**: Python-based streaming (can upgrade later)

**Processing Steps**:

```python
# Pseudocode: Stream Processing Pipeline

def process_event_stream(raw_event):
    # Step 1: Normalize schema
    normalized = normalize_schema(raw_event)
    
    # Step 2: Enrich with context
    enriched = enrich_event(normalized)
    #   - GeoIP lookup (IP → Country/City)
    #   - Device fingerprint lookup
    #   - User/service metadata
    
    # Step 3: Deduplicate
    if is_duplicate(enriched):
        return None
    
    # Step 4: Extract entity identifiers
    entity_id = extract_entity_id(enriched)
    
    # Step 5: Persist to storage
    write_to_storage(enriched)
    
    # Step 6: Forward to feature engineering
    emit_to_feature_pipeline(enriched)
    
    return enriched
```

**Enrichment Sources**:
- GeoIP database (MaxMind GeoLite2 - free)
- Device fingerprint database (custom)
- User metadata (from identity provider)
- Threat intelligence feeds (optional)

---

### 3. FEATURE ENGINEERING

**Purpose**: Transform raw events into ML-ready features

**Feature Categories**:

#### A. Velocity Features
```python
# Example velocity features
- login_count_last_1h
- login_count_last_24h
- api_call_rate_per_minute
- failed_auth_count_last_10m
- unique_ips_last_24h
- unique_devices_last_7d
```

#### B. Sequence Features
```python
# Example sequence features
- last_10_actions = ["login", "read_db", "write_s3", ...]
- action_pair_frequency = {("login", "read_db"): 0.95, ...}
- rare_action_sequences = detect_rare_ngrams(action_sequence)
```

#### C. Graph Features
```python
# Example graph features
- service_dependency_violation = bool  # service A calling service D (never before)
- user_to_resource_distance = int      # graph hops from user's normal resources
- network_community_id = int           # which cluster user belongs to
- centrality_score = float             # how central user is in access graph
```