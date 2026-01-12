
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