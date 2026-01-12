"""
Storage Layer for ZTBF Data Pipeline

"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from dataclasses import dataclass
import boto3
from botocore.client import Config


@dataclass
class StorageConfig:
    """Configuration for storage layer"""
    # Storage backend
    backend: str = "minio"  # "minio" or "s3"
    endpoint_url: Optional[str] = "http://localhost:9000"  # MinIO endpoint
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    bucket_name: str = "ztbf-events"
    region: str = "us-east-1"
    
    # Storage tiers
    hot_retention_days: int = 7
    warm_retention_days: int = 30
    cold_retention_days: int = 90
    
    # Partitioning
    partition_by: List[str] = None
    
    # Compression
    hot_compression: str = "snappy"
    warm_compression: str = "snappy"
    cold_compression: str = "gzip"
    
    def __post_init__(self):
        if self.partition_by is None:
            self.partition_by = ["date", "hour", "source_system"]