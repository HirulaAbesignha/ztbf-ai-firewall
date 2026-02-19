"""
Event Normalizer for ZTBF

"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from data_pipeline.schemas.unified_schema import (
    UnifiedEvent,
    EntityType,
    EventType,
    LocationContext,
    DeviceFingerprint,
    ResourceContext,
    TemporalContext
)

logger = logging.getLogger(__name__)


class NormalizationError(Exception):
    """Custom exception for normalization errors"""
    pass


class EventNormalizer:
    """
    Normalizes events from various sources to unified schema
    
    Supports:
    - Azure AD sign-in logs
    - AWS CloudTrail events
    - API Gateway logs
    - (Extensible to new sources)
    """
    
    def __init__(self):
        """Initialize normalizer with source mappers"""
        self.source_mappers: Dict[str, Callable] = {
            "azure_ad": self.normalize_azure_ad,
            "cloudtrail": self.normalize_cloudtrail,
            "api_gateway": self.normalize_api_gateway
        }
        
        logger.info("Event Normalizer initialized")
        logger.info(f"   - Supported sources: {list(self.source_mappers.keys())}")
    
    async def normalize(self, raw_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize event to unified schema
        
        Args:
            raw_event: Raw event from data source
        
        Returns:
            Normalized event dictionary (unified schema)
        
        Raises:
            NormalizationError: If normalization fails
        """
        try:
            source_type = raw_event.get("source_type")
            
            if not source_type:
                raise NormalizationError("Missing source_type field")
            
            if source_type not in self.source_mappers:
                raise NormalizationError(f"Unknown source type: {source_type}")
            
            # Get source-specific mapper
            mapper = self.source_mappers[source_type]
            
            # Normalize
            normalized = await mapper(raw_event)
            
            # Add processing timestamp
            normalized["processing_timestamp"] = datetime.utcnow()
            
            return normalized
        
        except Exception as e:
            logger.error(f"Normalization error: {e}", exc_info=True)
            raise NormalizationError(f"Failed to normalize event: {str(e)}")
    
    # ===== AZURE AD NORMALIZATION =====
    
    async def normalize_azure_ad(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Azure AD sign-in event to unified schema
        
        Args:
            event: Azure AD sign-in log event
        
        Returns:
            Normalized event dictionary
        """
        try:
            # Extract location
            location_data = event.get("location", {})
            location = LocationContext(
                city=location_data.get("city"),
                country=location_data.get("countryOrRegion"),
                latitude=location_data.get("geoCoordinates", {}).get("latitude"),
                longitude=location_data.get("geoCoordinates", {}).get("longitude")
            ) if location_data else None
            
            # Extract device info
            device_data = event.get("deviceDetail", {})
            device = DeviceFingerprint(
                device_id=device_data.get("deviceId"),
                os=device_data.get("operatingSystem"),
                browser=device_data.get("browser"),
                is_mobile=device_data.get("operatingSystem", "").lower() in ["ios", "android"]
            ) if device_data else None
            
            # Extract resource
            resource = ResourceContext(
                type="application",
                id=event.get("appId"),
                name=event.get("appDisplayName")
            )
            
            # Determine success
            status = event.get("status", {})
            success = status.get("errorCode") == 0 or status.get("errorCode") is None
            
            # Extract temporal features
            timestamp = self._parse_timestamp(event.get("createdDateTime"))
            temporal = self._extract_temporal_features(timestamp) if timestamp else None
            
            # Build normalized event
            normalized = {
                # Core identity
                "entity_id": event.get("userPrincipalName") or event.get("userId"),
                "entity_type": EntityType.USER,
                "session_id": event.get("correlationId"),
                
                # Event metadata
                "event_type": EventType.AUTHENTICATION,
                "event_subtype": "sign_in",
                "timestamp": timestamp,
                "success": success,
                "error_code": str(status.get("errorCode")) if not success else None,
                "error_message": status.get("failureReason") if not success else None,
                
                # Network context
                "source_ip": event.get("ipAddress"),
                "user_agent": event.get("clientAppUsed"),
                
                # Enriched context
                "location": location.dict() if location else None,
                "device": device.dict() if device else None,
                "resource": resource.dict(),
                "temporal": temporal.dict() if temporal else None,
                
                # Risk indicators (from Azure AD)
                "risk_level": event.get("riskLevelDuringSignIn"),
                "risk_factors": [event.get("riskDetail")] if event.get("riskDetail") else None,
                
                # Metadata
                "source_system": "azure_ad",
                "ingestion_timestamp": self._parse_timestamp(event.get("ingestion_timestamp")),
                "raw_event_id": event.get("id"),
                "pipeline_version": "1.0.0",
                
                # Preserve source-specific fields
                "source_specific": {
                    "correlationId": event.get("correlationId"),
                    "riskState": event.get("riskState"),
                    "riskLevelAggregated": event.get("riskLevelAggregated")
                }
            }
            
            return normalized
        
        except Exception as e:
            logger.error(f"Error normalizing Azure AD event: {e}")
            raise NormalizationError(f"Azure AD normalization failed: {str(e)}")
    
    # ===== CLOUDTRAIL NORMALIZATION =====
    
    async def normalize_cloudtrail(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize AWS CloudTrail event to unified schema
        
        Args:
            event: CloudTrail event record
        
        Returns:
            Normalized event dictionary
        """
        try:
            # Extract user identity
            user_identity = event.get("userIdentity", {})
            entity_id = self._extract_cloudtrail_entity_id(user_identity)
            entity_type = self._determine_entity_type(user_identity)
            
            # Extract resource
            service = event.get("eventSource", "").replace(".amazonaws.com", "")
            resource = ResourceContext(
                type="cloud_resource",
                service=service,
                method=event.get("eventName"),
                name=event.get("eventName"),
                # Extract ARN if available
                id=event.get("resources", [{}])[0].get("ARN") if event.get("resources") else None
            )
            
            # Determine success
            success = event.get("errorCode") is None
            
            # Extract timestamp
            timestamp = self._parse_timestamp(event.get("eventTime"))
            temporal = self._extract_temporal_features(timestamp) if timestamp else None
            
            # Build normalized event
            normalized = {
                # Core identity
                "entity_id": entity_id,
                "entity_type": entity_type,
                "session_id": event.get("requestID"),
                
                # Event metadata
                "event_type": EventType.CLOUD_API,
                "event_subtype": event.get("eventName"),
                "timestamp": timestamp,
                "success": success,
                "error_code": event.get("errorCode"),
                "error_message": event.get("errorMessage"),
                
                # Network context
                "source_ip": event.get("sourceIPAddress"),
                "user_agent": event.get("userAgent"),
                
                # Enriched context
                "location": None,  # Will be enriched by enricher
                "device": None,
                "resource": resource.dict(),
                "temporal": temporal.dict() if temporal else None,
                
                # Risk indicators
                "risk_level": None,  # Will be computed by ML models
                "risk_factors": None,
                
                # Metadata
                "source_system": "cloudtrail",
                "ingestion_timestamp": self._parse_timestamp(event.get("ingestion_timestamp")),
                "raw_event_id": event.get("eventID"),
                "pipeline_version": "1.0.0",
                
                # Preserve source-specific fields
                "source_specific": {
                    "eventVersion": event.get("eventVersion"),
                    "awsRegion": event.get("awsRegion"),
                    "accountId": event.get("recipientAccountId"),
                    "eventType": event.get("eventType"),
                    "userIdentity": user_identity,
                    "requestParameters": event.get("requestParameters"),
                    "responseElements": event.get("responseElements")
                }
            }
            
            return normalized
        
        except Exception as e:
            logger.error(f"Error normalizing CloudTrail event: {e}")
            raise NormalizationError(f"CloudTrail normalization failed: {str(e)}")
    
    # ===== API GATEWAY NORMALIZATION =====
    
    async def normalize_api_gateway(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize API Gateway log to unified schema
        
        Args:
            event: API Gateway log entry
        
        Returns:
            Normalized event dictionary
        """
        try:
            # Determine entity type based on user_id format
            user_id = event.get("user_id", "")
            entity_type = EntityType.USER if "@" in user_id else EntityType.SERVICE
            
            # Extract resource
            resource = ResourceContext(
                type="api_endpoint",
                endpoint=event.get("endpoint"),
                method=event.get("method"),
                name=f"{event.get('method')} {event.get('endpoint')}"
            )
            
            # Determine success
            status_code = event.get("status_code", 0)
            success = 200 <= status_code < 300
            
            # Extract timestamp
            timestamp = self._parse_timestamp(event.get("timestamp"))
            temporal = self._extract_temporal_features(timestamp) if timestamp else None
            
            # Extract performance metrics
            performance = {
                "latency_ms": event.get("latency_ms"),
                "request_size_bytes": event.get("request_size_bytes"),
                "response_size_bytes": event.get("response_size_bytes")
            }
            
            # Build normalized event
            normalized = {
                # Core identity
                "entity_id": user_id,
                "entity_type": entity_type,
                "session_id": event.get("request_id"),
                
                # Event metadata
                "event_type": EventType.API_CALL,
                "event_subtype": event.get("method"),
                "timestamp": timestamp,
                "success": success,
                "error_code": str(status_code) if not success else None,
                "error_message": None,
                
                # Network context
                "source_ip": event.get("source_ip"),
                "user_agent": event.get("user_agent"),
                
                # Enriched context
                "location": None,  # Will be enriched
                "device": None,
                "resource": resource.dict(),
                "temporal": temporal.dict() if temporal else None,
                "performance": performance,
                
                # Risk indicators
                "risk_level": None,
                "risk_factors": None,
                
                # Metadata
                "source_system": "api_gateway",
                "ingestion_timestamp": self._parse_timestamp(event.get("ingestion_timestamp")),
                "raw_event_id": event.get("request_id"),
                "pipeline_version": "1.0.0",
                
                # Preserve source-specific fields
                "source_specific": {
                    "api_key_id": event.get("api_key_id"),
                    "status_code": status_code
                }
            }
            
            return normalized
        
        except Exception as e:
            logger.error(f"Error normalizing API Gateway event: {e}")
            raise NormalizationError(f"API Gateway normalization failed: {str(e)}")
    
    # ===== HELPER METHODS =====
    
    def _extract_cloudtrail_entity_id(self, user_identity: Dict) -> str:
        """Extract entity ID from CloudTrail userIdentity"""
        if "userName" in user_identity:
            return user_identity["userName"]
        elif "principalId" in user_identity:
            return user_identity["principalId"]
        elif "arn" in user_identity:
            # Extract from ARN: arn:aws:iam::123456789012:user/alice
            arn_parts = user_identity["arn"].split("/")
            return arn_parts[-1] if len(arn_parts) > 1 else user_identity["arn"]
        else:
            return "unknown"
    
    def _determine_entity_type(self, user_identity: Dict) -> EntityType:
        """Determine entity type from CloudTrail userIdentity"""
        identity_type = user_identity.get("type", "").lower()
        
        if identity_type in ["assumedrole", "awsservice", "federated"]:
            return EntityType.SERVICE
        elif identity_type in ["iamuser", "root"]:
            return EntityType.USER
        else:
            return EntityType.UNKNOWN
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """
        Parse timestamp string to datetime object
        
        Supports multiple formats:
        - ISO 8601: 2025-01-08T10:00:00Z
        - ISO 8601 with microseconds: 2025-01-08T10:00:00.123456Z
        """
        if not timestamp_str:
            return None
        
        try:
            # Remove 'Z' suffix if present
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1]
            
            # Try parsing with microseconds
            try:
                return datetime.fromisoformat(timestamp_str)
            except:
                # Try parsing without microseconds
                return datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")
        
        except Exception as e:
            logger.warning(f"Failed to parse timestamp '{timestamp_str}': {e}")
            return None
    
    def _extract_temporal_features(self, timestamp: datetime) -> TemporalContext:
        """
        Extract temporal features from timestamp
        
        Args:
            timestamp: Event timestamp
        
        Returns:
            TemporalContext object
        """
        hour = timestamp.hour
        day_of_week = timestamp.weekday()  # 0=Monday, 6=Sunday
        is_weekend = day_of_week >= 5
        is_business_hours = 9 <= hour < 17
        
        return TemporalContext(
            hour_of_day=hour,
            day_of_week=day_of_week,
            is_weekend=is_weekend,
            is_business_hours=is_business_hours,
            week_of_year=timestamp.isocalendar()[1],
            month=timestamp.month
        )


# ===== TESTING =====

async def test_normalizer():
    """Test normalizer with sample events"""
    print("Testing Event Normalizer...")
    
    normalizer = EventNormalizer()
    
    # Test Azure AD event
    print("\nTest 1: Azure AD Sign-in")
    azure_event = {
        "source_type": "azure_ad",
        "id": "test-123",
        "createdDateTime": "2025-01-08T10:00:00Z",
        "userPrincipalName": "alice@company.com",
        "userId": "user_001",
        "appId": "app-123",
        "appDisplayName": "Office 365",
        "ipAddress": "192.168.1.100",
        "clientAppUsed": "Browser",
        "correlationId": "corr-123",
        "status": {"errorCode": 0},
        "location": {
            "city": "New York",
            "countryOrRegion": "US",
            "geoCoordinates": {"latitude": 40.7128, "longitude": -74.0060}
        },
        "deviceDetail": {
            "deviceId": "device-123",
            "operatingSystem": "Windows 10",
            "browser": "Edge 110.0"
        },
        "riskLevelDuringSignIn": "low",
        "ingestion_timestamp": "2025-01-08T10:00:01Z"
    }
    
    try:
        normalized = await normalizer.normalize(azure_event)
        print(f"   Normalized Azure AD event")
        print(f"   Entity: {normalized['entity_id']}")
        print(f"   Event Type: {normalized['event_type']}")
        print(f"   Success: {normalized['success']}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test CloudTrail event
    print("\nTest 2: CloudTrail Event")
    cloudtrail_event = {
        "source_type": "cloudtrail",
        "eventVersion": "1.08",
        "userIdentity": {
            "type": "IAMUser",
            "userName": "bob",
            "principalId": "AIDAI123456",
            "arn": "arn:aws:iam::123456789012:user/bob"
        },
        "eventTime": "2025-01-08T10:05:00Z",
        "eventSource": "s3.amazonaws.com",
        "eventName": "GetObject",
        "awsRegion": "us-east-1",
        "sourceIPAddress": "10.0.1.50",
        "userAgent": "aws-cli/2.13.0",
        "requestID": "req-123",
        "eventID": "event-456",
        "eventType": "AwsApiCall",
        "recipientAccountId": "123456789012",
        "ingestion_timestamp": "2025-01-08T10:05:01Z"
    }
    
    try:
        normalized = await normalizer.normalize(cloudtrail_event)
        print(f"   Normalized CloudTrail event")
        print(f"   Entity: {normalized['entity_id']}")
        print(f"   Event Type: {normalized['event_type']}")
        print(f"   Event Subtype: {normalized['event_subtype']}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test API Gateway event
    print("\nTest 3: API Gateway Log")
    api_event = {
        "source_type": "api_gateway",
        "timestamp": "2025-01-08T10:10:00Z",
        "request_id": "req-789",
        "user_id": "service_api_01",
        "method": "GET",
        "endpoint": "/api/users",
        "status_code": 200,
        "latency_ms": 45,
        "request_size_bytes": 512,
        "response_size_bytes": 2048,
        "source_ip": "10.0.2.100",
        "user_agent": "python-requests/2.31.0",
        "api_key_id": "key_123",
        "ingestion_timestamp": "2025-01-08T10:10:01Z"
    }
    
    try:
        normalized = await normalizer.normalize(api_event)
        print(f"   Normalized API Gateway event")
        print(f"   Entity: {normalized['entity_id']}")
        print(f"   Entity Type: {normalized['entity_type']}")
        print(f"   Resource: {normalized['resource']['name']}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n✅ Testing complete!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_normalizer())