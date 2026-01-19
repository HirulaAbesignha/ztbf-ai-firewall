
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

class UnifiedEvent(BaseModel):
    """
    Unified event schema - canonical representation of all security events
    
    This schema is the result of normalizing and enriching events from
    all data sources (Azure AD, CloudTrail, API Gateway, etc.)
    """
    
    # ===== CORE IDENTITY =====
    entity_id: str = Field(..., description="Unique identifier for the entity (user/service)")
    entity_type: EntityType = Field(..., description="Type of entity")
    session_id: Optional[str] = Field(None, description="Session or correlation ID")
    
    # ===== EVENT METADATA =====
    event_type: EventType = Field(..., description="High-level event category")
    event_subtype: str = Field(..., description="Specific event action (e.g., 'sign_in', 'AssumeRole')")
    timestamp: datetime = Field(..., description="Event occurrence time (UTC)")
    success: bool = Field(..., description="Whether the action succeeded")
    error_code: Optional[str] = Field(None, description="Error code if action failed")
    error_message: Optional[str] = Field(None, description="Error description if action failed")
    
    # ===== NETWORK CONTEXT =====
    source_ip: str = Field(..., description="Source IP address")
    source_ip_anonymized: Optional[str] = Field(None, description="Anonymized IP (last octet masked)")
    user_agent: Optional[str] = Field(None, description="User agent string")
    
    # ===== ENRICHED CONTEXT =====
    location: Optional[LocationContext] = Field(None, description="Geographic location")
    device: Optional[DeviceFingerprint] = Field(None, description="Device information")
    resource: ResourceContext = Field(..., description="Resource being accessed")
    entity_metadata: Optional[EntityMetadata] = Field(None, description="Entity metadata")
    temporal: Optional[TemporalContext] = Field(None, description="Temporal features")
    performance: Optional[PerformanceMetrics] = Field(None, description="Performance metrics")
    
    # ===== RISK INDICATORS =====
    risk_level: Optional[RiskLevel] = Field(None, description="Pre-computed risk level (if available)")
    risk_score: Optional[float] = Field(None, ge=0, le=100, description="Risk score 0-100")
    risk_factors: Optional[List[str]] = Field(None, description="List of risk factors identified")
    
    # ===== METADATA =====
    source_system: str = Field(..., description="Source system (azure_ad, cloudtrail, api_gateway)")
    ingestion_timestamp: datetime = Field(..., description="When event was ingested by ZTBF")
    processing_timestamp: Optional[datetime] = Field(None, description="When event was processed")
    raw_event_id: Optional[str] = Field(None, description="Original event ID from source")
    pipeline_version: str = Field(default="1.0.0", description="Pipeline version")
    
    # ===== SOURCE-SPECIFIC FIELDS =====
    # These are preserved for debugging and compliance
    source_specific: Optional[Dict] = Field(None, description="Source-specific fields")

    class Config:
        extra = "forbid"
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @validator("source_ip_anonymized", always=True)
    def anonymize_ip(cls, v, values):
        """Automatically anonymize IP address"""
        if v is None and "source_ip" in values:
            ip = values["source_ip"]
            parts = ip.split(".")
            if len(parts) == 4:
                # Mask last octet
                return f"{parts[0]}.{parts[1]}.{parts[2]}.XXX"
        return v
    
    def to_feature_dict(self) -> Dict:
        """
        Convert to flat dictionary suitable for ML feature engineering
        Extracts nested fields into top-level features
        """
        features = {
            # Identity
            "entity_id_hash": hash(self.entity_id),  # Anonymized
            "entity_type": self.entity_type.value,
            "is_user": self.entity_type == EntityType.USER,
            "is_service": self.entity_type == EntityType.SERVICE,
            
            # Event
            "event_type": self.event_type.value,
            "event_subtype": self.event_subtype,
            "success": self.success,
            
            # Network
            "source_ip_hash": hash(self.source_ip),  # Anonymized
            
            # Location
            "location_country": self.location.country if self.location else None,
            "location_latitude": self.location.latitude if self.location else None,
            "location_longitude": self.location.longitude if self.location else None,
            
            # Device
            "device_id_hash": hash(self.device.device_id) if self.device and self.device.device_id else None,
            "device_type": self.device.device_type if self.device else None,
            "device_os": self.device.os if self.device else None,
            "is_mobile": self.device.is_mobile if self.device else False,
            "is_bot": self.device.is_bot if self.device else False,
            
            # Resource
            "resource_type": self.resource.type,
            "resource_sensitivity": self.resource.sensitivity_level,
            "resource_method": self.resource.method,
            
            # Entity metadata
            "is_admin": self.entity_metadata.is_admin if self.entity_metadata else False,
            "is_privileged": self.entity_metadata.is_privileged if self.entity_metadata else False,
            
            # Temporal
            "hour_of_day": self.temporal.hour_of_day if self.temporal else None,
            "day_of_week": self.temporal.day_of_week if self.temporal else None,
            "is_weekend": self.temporal.is_weekend if self.temporal else None,
            "is_business_hours": self.temporal.is_business_hours if self.temporal else None,
            
            # Performance
            "latency_ms": self.performance.latency_ms if self.performance else None,
            "request_size_bytes": self.performance.request_size_bytes if self.performance else None,
            "response_size_bytes": self.performance.response_size_bytes if self.performance else None,
            
            # Metadata
            "timestamp": self.timestamp.isoformat(),
            "source_system": self.source_system
        }
        
        return {k: v for k, v in features.items() if v is not None}

# ===== SOURCE-SPECIFIC SCHEMAS =====
# These are used for ingestion validation before normalization

class AzureADSignInEvent(BaseModel):
    """Azure AD Sign-in Log Schema (Microsoft Graph API format)"""
    id: str
    createdDateTime: datetime
    userPrincipalName: str
    userId: str
    appId: str
    appDisplayName: str
    ipAddress: str
    clientAppUsed: Optional[str] = None
    correlationId: Optional[str] = None
    
    status: Dict = Field(..., description="Contains errorCode, failureReason, etc.")
    location: Optional[Dict] = None
    deviceDetail: Optional[Dict] = None
    riskLevelDuringSignIn: Optional[str] = None
    riskLevelAggregated: Optional[str] = None
    riskDetail: Optional[str] = None
    riskState: Optional[str] = None
    
    class Config:
        extra = "allow"  # Azure AD has many optional fields


class CloudTrailEvent(BaseModel):
    """AWS CloudTrail Event Schema"""
    eventVersion: str
    userIdentity: Dict = Field(..., description="IAM identity information")
    eventTime: datetime
    eventSource: str
    eventName: str
    awsRegion: str
    sourceIPAddress: str
    userAgent: str
    requestParameters: Optional[Dict] = None
    responseElements: Optional[Dict] = None
    requestID: str
    eventID: str
    eventType: str
    recipientAccountId: str
    
    errorCode: Optional[str] = None
    errorMessage: Optional[str] = None
    resources: Optional[List[Dict]] = None
    
    class Config:
        extra = "allow"


class APIGatewayLog(BaseModel):
    """API Gateway Log Schema (custom)"""
    timestamp: datetime
    request_id: str
    user_id: str
    method: str
    endpoint: str
    status_code: int
    latency_ms: int
    request_size_bytes: int
    response_size_bytes: int
    source_ip: str
    user_agent: Optional[str] = None
    api_key_id: Optional[str] = None
    
    class Config:
        extra = "allow"

# ===== SCHEMA VERSION REGISTRY =====
SCHEMA_VERSION = "1.0.0"

SCHEMA_REGISTRY = {
    "unified": UnifiedEvent,
    "azure_ad": AzureADSignInEvent,
    "cloudtrail": CloudTrailEvent,
    "api_gateway": APIGatewayLog
}


def get_schema(schema_name: str) -> BaseModel:
    """Get schema class by name"""
    if schema_name not in SCHEMA_REGISTRY:
        raise ValueError(f"Unknown schema: {schema_name}")
    return SCHEMA_REGISTRY[schema_name]


def validate_event(schema_name: str, event_data: Dict) -> BaseModel:
    """Validate event against schema"""
    schema_class = get_schema(schema_name)
    return schema_class(**event_data)