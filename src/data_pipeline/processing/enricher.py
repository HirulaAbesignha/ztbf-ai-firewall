"""
Event Enricher for ZTBF

"""
import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)


@dataclass
class EnricherConfig:
    """Configuration for event enricher"""
    enable_geoip: bool = True
    enable_entity_metadata: bool = True
    enable_device_fingerprint: bool = True
    enable_resource_classification: bool = True
    entity_cache_ttl: int = 3600  # seconds


class EventEnricher:
    """
    Enriches normalized events with contextual data
    
    Features:
    - GeoIP lookup (free tier compatible)
    - Entity metadata caching
    - Device fingerprint parsing
    - Resource sensitivity classification
    """
    
    def __init__(self, config: Optional[EnricherConfig] = None):
        """
        Initialize enricher
        
        Args:
            config: Enricher configuration
        """
        self.config = config or EnricherConfig()
        
        # Entity metadata cache (in-memory for MVP)
        self.entity_cache: Dict[str, Dict] = {}
        
        # GeoIP database (mock for MVP, use MaxMind GeoLite2 in production)
        self.geoip_db = self._load_geoip_database()
        
        # Resource sensitivity rules
        self.sensitivity_rules = self._load_sensitivity_rules()
        
        logger.info("🔍 Event Enricher initialized")
        logger.info(f"   - GeoIP: {'enabled' if self.config.enable_geoip else 'disabled'}")
        logger.info(f"   - Entity metadata: {'enabled' if self.config.enable_entity_metadata else 'disabled'}")
    
    async def enrich(self, normalized_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich normalized event with additional context
        
        Args:
            normalized_event: Normalized event dictionary
        
        Returns:
            Enriched event dictionary
        """
        try:
            enriched = normalized_event.copy()
            
            # 1. GeoIP enrichment
            if self.config.enable_geoip and enriched.get("source_ip"):
                if not enriched.get("location"):
                    location = await self.geoip_lookup(enriched["source_ip"])
                    if location:
                        enriched["location"] = location
            
            # 2. Entity metadata enrichment
            if self.config.enable_entity_metadata and enriched.get("entity_id"):
                entity_metadata = await self.get_entity_metadata(
                    enriched["entity_id"],
                    enriched.get("entity_type")
                )
                if entity_metadata:
                    enriched["entity_metadata"] = entity_metadata
            
            # 3. Device fingerprint enrichment
            if self.config.enable_device_fingerprint:
                if enriched.get("user_agent") and not enriched.get("device"):
                    device = self.parse_user_agent(enriched["user_agent"])
                    if device:
                        enriched["device"] = device
            
            # 4. Resource sensitivity classification
            if self.config.enable_resource_classification and enriched.get("resource"):
                sensitivity = self.classify_resource_sensitivity(enriched["resource"])
                enriched["resource"]["sensitivity_level"] = sensitivity
            
            # 5. Anonymize PII
            enriched = self._anonymize_pii(enriched)
            
            return enriched
        
        except Exception as e:
            logger.error(f"Enrichment error: {e}", exc_info=True)
            # Return original event if enrichment fails
            return normalized_event
    
    # ===== GEOIP LOOKUP =====
    
    def _load_geoip_database(self) -> Dict[str, Dict]:
        """
        Load GeoIP database (mock for MVP)
        
        In production: Use MaxMind GeoLite2 or ip-api.com
        """
        # Mock database with common IP ranges
        return {
            "192.168.": {"city": "Local Network", "country": "Private", "latitude": 0.0, "longitude": 0.0},
            "10.0.": {"city": "Local Network", "country": "Private", "latitude": 0.0, "longitude": 0.0},
            "172.16.": {"city": "Local Network", "country": "Private", "latitude": 0.0, "longitude": 0.0},
            "203.0.113.": {"city": "Test Network", "country": "TEST", "latitude": 0.0, "longitude": 0.0},
            # Sample public IPs
            "8.8.8.": {"city": "Mountain View", "country": "US", "country_code": "US", "latitude": 37.4056, "longitude": -122.0775},
            "1.1.1.": {"city": "San Francisco", "country": "US", "country_code": "US", "latitude": 37.7749, "longitude": -122.4194},
        }
    
    async def geoip_lookup(self, ip_address: str) -> Optional[Dict]:
        """
        Lookup geographic location from IP address
        
        Args:
            ip_address: IP address to lookup
        
        Returns:
            Location dictionary or None
        """
        try:
            # Check cache (prefix-based for simplicity)
            for prefix, location in self.geoip_db.items():
                if ip_address.startswith(prefix):
                    logger.debug(f"GeoIP lookup: {ip_address} → {location['city']}, {location['country']}")
                    return location
            
            # Default to unknown
            logger.debug(f"GeoIP lookup: {ip_address} → Unknown")
            return {
                "city": "Unknown",
                "country": "Unknown",
                "country_code": "XX",
                "latitude": None,
                "longitude": None
            }
        
        except Exception as e:
            logger.warning(f"GeoIP lookup failed for {ip_address}: {e}")
            return None
    
    # ===== ENTITY METADATA =====
    
    async def get_entity_metadata(
        self,
        entity_id: str,
        entity_type: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Get entity metadata from cache or fetch
        
        Args:
            entity_id: Entity identifier
            entity_type: Entity type (user, service, device)
        
        Returns:
            Entity metadata dictionary or None
        """
        try:
            # Check cache
            if entity_id in self.entity_cache:
                cached = self.entity_cache[entity_id]
                # Check if cache is still valid (TTL)
                if (datetime.utcnow() - cached["cached_at"]).seconds < self.config.entity_cache_ttl:
                    logger.debug(f"Entity metadata (cached): {entity_id}")
                    return cached["metadata"]
            
            # Fetch metadata (mock for MVP)
            metadata = self._fetch_entity_metadata(entity_id, entity_type)
            
            # Cache metadata
            self.entity_cache[entity_id] = {
                "metadata": metadata,
                "cached_at": datetime.utcnow()
            }
            
            logger.debug(f"Entity metadata (fetched): {entity_id}")
            return metadata
        
        except Exception as e:
            logger.warning(f"Failed to get entity metadata for {entity_id}: {e}")
            return None
    
    def _fetch_entity_metadata(
        self,
        entity_id: str,
        entity_type: Optional[str]
    ) -> Dict:
        """
        Fetch entity metadata (mock implementation)
        
        In production: Query identity provider, CMDB, or HR system
        """
        # Mock metadata based on entity_id pattern
        if "@" in entity_id:
            # User entity
            department = "Engineering" if "user" in entity_id else "Operations"
            is_admin = entity_id.startswith("admin") or entity_id.endswith("_admin")
            
            return {
                "department": department,
                "role": "Admin" if is_admin else "Developer",
                "job_title": "Software Engineer",
                "manager": "manager@company.com",
                "is_admin": is_admin,
                "is_privileged": is_admin,
                "account_creation_date": "2024-01-01T00:00:00Z",
                "last_password_change": "2024-12-01T00:00:00Z"
            }
        
        elif "service" in entity_id:
            # Service entity
            return {
                "service_type": "api_service",
                "environment": "production",
                "owner_team": "Platform Engineering",
                "is_admin": False,
                "is_privileged": True
            }
        
        else:
            # Unknown entity
            return {
                "is_admin": False,
                "is_privileged": False
            }


    