
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
