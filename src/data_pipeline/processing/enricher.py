"""
Event Enricher for ZTBF
File: src/data_pipeline/processing/enricher.py

Enriches normalized events with additional contextual information:
- GeoIP lookup (IP → location)
- Entity metadata (user/service details)
- Device fingerprinting
- Resource sensitivity classification
- Threat intelligence (future)

Enrichment Flow:
    Normalized Event
        → GeoIP Lookup
        → Entity Metadata
        → Device Analysis
        → Resource Classification
        → Enriched Event
"""