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
        
        logger.info("🔄 Event Normalizer initialized")
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