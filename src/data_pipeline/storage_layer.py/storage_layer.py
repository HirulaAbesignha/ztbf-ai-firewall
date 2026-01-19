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

    def read_events(
        self,
        start_time: datetime,
        end_time: datetime,
        source_system: Optional[str] = None,
        tier: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Read events from storage
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            source_system: Filter by source (e.g., "azure_ad")
            tier: Read from specific tier, or None for all tiers
        
        Returns:
            DataFrame of events
        """
        # Determine which tiers to read from
        if tier:
            tiers = [tier]
        else:
            tiers = self._determine_tiers(start_time, end_time)
        
        # Build list of S3 prefixes to scan
        prefixes = []
        current_date = start_time.date()
        end_date = end_time.date()
        
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            
            for tier_name in tiers:
                if source_system:
                    prefix = f"{tier_name}/date={date_str}/hour=*/source={source_system}/"
                else:
                    prefix = f"{tier_name}/date={date_str}/"
                
                prefixes.append(prefix)
            
            current_date += timedelta(days=1)
        
        # Read all matching partitions
        dfs = []
        for prefix in prefixes:
            partition_dfs = self._read_prefix(prefix)
            dfs.extend(partition_dfs)
        
        if not dfs:
            return pd.DataFrame()
        
        # Concatenate and filter by exact time range
        df = pd.concat(dfs, ignore_index=True)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df[(df['timestamp'] >= start_time) & (df['timestamp'] <= end_time)]
        
        return df

    def _determine_tiers(self, start_time: datetime, end_time: datetime) -> List[str]:
        """Determine which storage tiers to read from based on time range"""
        now = datetime.utcnow()
        tiers = []
        
        # Check if we need hot tier (last 7 days)
        hot_cutoff = now - timedelta(days=self.config.hot_retention_days)
        if end_time >= hot_cutoff:
            tiers.append("hot")
        
        # Check if we need warm tier (7-30 days)
        warm_cutoff = now - timedelta(days=self.config.warm_retention_days)
        if start_time < hot_cutoff and end_time >= warm_cutoff:
            tiers.append("warm")
        
        # Check if we need cold tier (30-90 days)
        cold_cutoff = now - timedelta(days=self.config.cold_retention_days)
        if start_time < warm_cutoff and end_time >= cold_cutoff:
            tiers.append("cold")
        
        return tiers if tiers else ["hot"]  # Default to hot if no tiers match

    def _read_prefix(self, prefix: str) -> List[pd.DataFrame]:
        """Read all Parquet files under a given prefix"""
        dfs = []
        
        try:
            # List objects with prefix
            response = self.s3_client.list_objects_v2(
                Bucket=self.config.bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                return dfs
            
            # Read each Parquet file
            for obj in response['Contents']:
                key = obj['Key']
                if not key.endswith('.parquet'):
                    continue
                
                # Download file
                response = self.s3_client.get_object(
                    Bucket=self.config.bucket_name,
                    Key=key
                )
                
                # Read Parquet
                import io
                buffer = io.BytesIO(response['Body'].read())
                df = pd.read_parquet(buffer)
                dfs.append(df)
        
        except Exception as e:
            print(f"Error reading from {prefix}: {e}")
        
        return dfs
    
    def lifecycle_management(self):
        """
        Move events between storage tiers based on age
        Hot → Warm → Cold → Delete
        """
        now = datetime.utcnow()
        
        # Move hot → warm
        hot_cutoff = now - timedelta(days=self.config.hot_retention_days)
        self._move_tier("hot", "warm", hot_cutoff)
        
        # Move warm → cold
        warm_cutoff = now - timedelta(days=self.config.warm_retention_days)
        self._move_tier("warm", "cold", warm_cutoff)
        
        # Delete cold data past retention
        cold_cutoff = now - timedelta(days=self.config.cold_retention_days)
        self._delete_old_data("cold", cold_cutoff)
    
    def _move_tier(self, from_tier: str, to_tier: str, cutoff_date: datetime):
        """Move data from one tier to another"""
        # List all objects in from_tier
        prefix = f"{from_tier}/"
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.config.bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                return
            
            for obj in response['Contents']:
                key = obj['Key']
                last_modified = obj['LastModified']
                
                # Check if old enough to move
                if last_modified.replace(tzinfo=None) < cutoff_date:
                    # Construct new key in destination tier
                    new_key = key.replace(from_tier + "/", to_tier + "/", 1)
                    
                    # Copy to new tier
                    self.s3_client.copy_object(
                        Bucket=self.config.bucket_name,
                        CopySource={'Bucket': self.config.bucket_name, 'Key': key},
                        Key=new_key
                    )
                    
                    # Delete from old tier
                    self.s3_client.delete_object(
                        Bucket=self.config.bucket_name,
                        Key=key
                    )
                    
                    print(f"Moved {key} → {new_key}")
        
        except Exception as e:
            print(f"Error moving data from {from_tier} to {to_tier}: {e}")
    
    def _delete_old_data(self, tier: str, cutoff_date: datetime):
        """Delete data older than cutoff date"""
        prefix = f"{tier}/"
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.config.bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                return
            
            for obj in response['Contents']:
                key = obj['Key']
                last_modified = obj['LastModified']
                
                if last_modified.replace(tzinfo=None) < cutoff_date:
                    self.s3_client.delete_object(
                        Bucket=self.config.bucket_name,
                        Key=key
                    )
                    print(f"Deleted {key} (expired)")
        
        except Exception as e:
            print(f"Error deleting old data from {tier}: {e}")
    
    def get_statistics(self) -> Dict:
        """Get storage statistics"""
        stats = {
            "hot": {"count": 0, "size_bytes": 0},
            "warm": {"count": 0, "size_bytes": 0},
            "cold": {"count": 0, "size_bytes": 0}
        }
        
        for tier in ["hot", "warm", "cold"]:
            prefix = f"{tier}/"
            
            try:
                response = self.s3_client.list_objects_v2(
                    Bucket=self.config.bucket_name,
                    Prefix=prefix
                )
                
                if 'Contents' in response:
                    stats[tier]["count"] = len(response['Contents'])
                    stats[tier]["size_bytes"] = sum(obj['Size'] for obj in response['Contents'])
            
            except Exception as e:
                print(f"Error getting stats for {tier}: {e}")
        
        return stats


# ===== LOCAL FILESYSTEM STORAGE (FOR LIGHTWEIGHT TESTING) =====

class LocalStorageLayer:
    """
    Simplified storage layer using local filesystem
    Useful for development without MinIO/S3
    """
    
    def __init__(self, base_path: str = "data/events"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def write_events(self, events: List[Dict], tier: str = "hot"):
        """Write events to local Parquet files"""
        if not events:
            return
        
        df = pd.DataFrame(events)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date.astype(str)
        df['hour'] = df['timestamp'].dt.hour
        
        # Write partitioned
        for (date, hour, source), group_df in df.groupby(['date', 'hour', 'source_system']):
            partition_dir = self.base_path / tier / f"date={date}" / f"hour={hour:02d}" / f"source={source}"
            partition_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = partition_dir / "events.parquet"
            
            # Append if file exists
            if file_path.exists():
                existing_df = pd.read_parquet(file_path)
                combined_df = pd.concat([existing_df, group_df], ignore_index=True)
                combined_df.to_parquet(file_path, compression='snappy', index=False)
            else:
                group_df.to_parquet(file_path, compression='snappy', index=False)
            
            print(f"Wrote {len(group_df)} events to {file_path}")
    
    def read_events(
        self,
        start_time: datetime,
        end_time: datetime,
        source_system: Optional[str] = None,
        tier: Optional[str] = None
    ) -> pd.DataFrame:
        """Read events from local storage"""
        tiers = [tier] if tier else ["hot", "warm", "cold"]
        dfs = []
        
        for tier_name in tiers:
            tier_path = self.base_path / tier_name
            if not tier_path.exists():
                continue
            
            # Recursively find all Parquet files
            for parquet_file in tier_path.rglob("*.parquet"):
                df = pd.read_parquet(parquet_file)
                dfs.append(df)
        
        if not dfs:
            return pd.DataFrame()
        
        # Filter by time range
        df = pd.concat(dfs, ignore_index=True)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df[(df['timestamp'] >= start_time) & (df['timestamp'] <= end_time)]
        
        if source_system:
            df = df[df['source_system'] == source_system]
        
        return df