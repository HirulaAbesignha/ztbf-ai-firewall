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

class StorageLayer:
    """
    Manages event storage across hot/warm/cold tiers
    Provides read/write interfaces for event data
    """
    
    def __init__(self, config: StorageConfig):
        self.config = config
        self.s3_client = self._init_s3_client()
        self._ensure_bucket_exists()
        
    def _init_s3_client(self):
        """Initialize S3/MinIO client"""
        if self.config.backend == "minio":
            return boto3.client(
                's3',
                endpoint_url=self.config.endpoint_url,
                aws_access_key_id=self.config.access_key,
                aws_secret_access_key=self.config.secret_key,
                config=Config(signature_version='s3v4'),
                region_name=self.config.region
            )
        else:  # AWS S3
            return boto3.client(
                's3',
                aws_access_key_id=self.config.access_key,
                aws_secret_access_key=self.config.secret_key,
                region_name=self.config.region
            )

    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            self.s3_client.head_bucket(Bucket=self.config.bucket_name)
        except:
            print(f"Creating bucket: {self.config.bucket_name}")
            if self.config.backend == "minio":
                self.s3_client.create_bucket(Bucket=self.config.bucket_name)
            else:
                # S3 requires location constraint for non-us-east-1
                if self.config.region == "us-east-1":
                    self.s3_client.create_bucket(Bucket=self.config.bucket_name)
                else:
                    self.s3_client.create_bucket(
                        Bucket=self.config.bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': self.config.region}
                    )

    def write_events(self, events: List[Dict], tier: str = "hot"):
        """
        Write events to storage
        
        Args:
            events: List of event dictionaries (unified schema)
            tier: Storage tier ("hot", "warm", or "cold")
        """
        if not events:
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(events)
        
        # Ensure timestamp is datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Add partition columns
        df['date'] = df['timestamp'].dt.date.astype(str)
        df['hour'] = df['timestamp'].dt.hour
        
        # Group by partition keys
        partition_cols = ['date', 'hour', 'source_system']
        for partition_values, group_df in df.groupby(partition_cols):
            self._write_partition(group_df, partition_values, tier)
    
    def _write_partition(self, df: pd.DataFrame, partition_values: tuple, tier: str):
        """Write a single partition to storage"""
        date, hour, source = partition_values
        
        # Construct S3 key (path)
        key = f"{tier}/date={date}/hour={hour:02d}/source={source}/events.parquet"
        
        # Select compression based on tier
        compression_map = {
            "hot": self.config.hot_compression,
            "warm": self.config.warm_compression,
            "cold": self.config.cold_compression
        }
        compression = compression_map.get(tier, "snappy")
        
        # Convert to Parquet bytes
        table = pa.Table.from_pandas(df)
        
        # Write to buffer
        import io
        buffer = io.BytesIO()
        pq.write_table(table, buffer, compression=compression)
        buffer.seek(0)
        
        # Upload to S3/MinIO
        try:
            self.s3_client.put_object(
                Bucket=self.config.bucket_name,
                Key=key,
                Body=buffer.getvalue()
            )
            print(f"Wrote {len(df)} events to {tier}/{key}")
        except Exception as e:
            print(f"Error writing to storage: {e}")
            raise