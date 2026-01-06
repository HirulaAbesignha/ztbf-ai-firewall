
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