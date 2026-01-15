
"""
Unified Event Schema for ZTBF

"""

from datetime import datetime
from typing import Optional, Dict, List, Literal
from pydantic import BaseModel, Field, validator
from enum import Enum


class EntityType(str, Enum):
    """Type of entity performing the action"""
    USER = "user"
    SERVICE = "service"
    DEVICE = "device"
    UNKNOWN = "unknown"


class EventType(str, Enum):
    """High-level event category"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    API_CALL = "api_call"
    CLOUD_API = "cloud_api"
    DATA_ACCESS = "data_access"
    NETWORK_CONNECTION = "network_connection"
    ADMIN_ACTION = "admin_action"

class RiskLevel(str, Enum):
    """Risk level indicator"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class LocationContext(BaseModel):
    """Geographic location information"""
    city: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    
    class Config:
        extra = "forbid"

class DeviceFingerprint(BaseModel):
    """Device identification information"""
    device_id: Optional[str] = None
    device_type: Optional[str] = None  # "desktop", "mobile", "tablet", "server"
    os: Optional[str] = None
    os_version: Optional[str] = None
    browser: Optional[str] = None
    browser_version: Optional[str] = None
    is_mobile: bool = False
    is_bot: bool = False
    
    class Config:
        extra = "forbid"

class ResourceContext(BaseModel):
    """Information about the resource being accessed"""
    type: str  # "api_endpoint", "cloud_resource", "application", "database", "file"
    id: Optional[str] = None
    name: Optional[str] = None
    sensitivity_level: int = Field(default=1, ge=1, le=5)  # 1=low, 5=critical
    
    # Resource-specific fields (populated based on type)
    service: Optional[str] = None  # For cloud resources (e.g., "s3", "ec2")
    endpoint: Optional[str] = None  # For API resources (e.g., "/api/users")
    method: Optional[str] = None  # For API resources (e.g., "GET", "POST")
    arn: Optional[str] = None  # For AWS resources
    
    class Config:
        extra = "allow"  # Allow source-specific fields

class EntityMetadata(BaseModel):
    """Metadata about the entity (user/service)"""
    department: Optional[str] = None
    role: Optional[str] = None
    job_title: Optional[str] = None
    manager: Optional[str] = None
    is_admin: bool = False
    is_privileged: bool = False
    account_creation_date: Optional[datetime] = None
    last_password_change: Optional[datetime] = None
    
    class Config:
        extra = "allow"

class TemporalContext(BaseModel):
    """Temporal features extracted from timestamp"""
    hour_of_day: int = Field(..., ge=0, le=23)
    day_of_week: int = Field(..., ge=0, le=6)  # 0=Monday, 6=Sunday
    is_weekend: bool
    is_business_hours: bool  # 9 AM - 5 PM local time
    week_of_year: int = Field(..., ge=1, le=53)
    month: int = Field(..., ge=1, le=12)
    
    class Config:
        extra = "forbid"


class PerformanceMetrics(BaseModel):
    """Performance and resource usage metrics"""
    latency_ms: Optional[int] = None
    request_size_bytes: Optional[int] = None
    response_size_bytes: Optional[int] = None
    cpu_usage_percent: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    
    class Config:
        extra = "forbid"