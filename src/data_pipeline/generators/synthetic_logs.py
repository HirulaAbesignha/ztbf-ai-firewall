"""
Synthetic Log Generator for ZTBF Testing

"""

import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import json


@dataclass
class UserProfile:
    """Profile for a synthetic user"""
    user_id: str
    email: str
    name: str
    department: str
    role: str
    is_admin: bool
    is_privileged: bool
    
    # Behavioral patterns
    typical_locations: List[str]
    typical_devices: List[str]
    typical_ips: List[str]
    typical_hours: List[int]  # Hours of day (0-23)
    typical_endpoints: List[str]
    typical_cloud_actions: List[str]
    
    # Usage patterns
    avg_logins_per_day: int
    avg_api_calls_per_day: int


@dataclass
class ServiceProfile:
    """Profile for a service account"""
    service_id: str
    service_name: str
    service_type: str  # "api", "batch", "microservice"
    
    # Behavioral patterns
    source_ips: List[str]
    typical_endpoints: List[str]
    call_rate_per_minute: int
    typical_hours: List[int]  # For batch services


class SyntheticLogGenerator:
    """Generate realistic synthetic security logs"""
    
    def __init__(self, seed: Optional[int] = None):
        if seed:
            random.seed(seed)
        
        self.users = self._create_user_profiles()
        self.services = self._create_service_profiles()
        self.locations = self._load_locations()
        self.cloud_services = ["s3", "ec2", "iam", "lambda", "rds", "dynamodb"]
        self.cloud_actions = {
            "s3": ["GetObject", "PutObject", "DeleteObject", "ListBucket"],
            "ec2": ["RunInstances", "TerminateInstances", "DescribeInstances"],
            "iam": ["CreateUser", "AttachUserPolicy", "CreateAccessKey", "AssumeRole"],
            "lambda": ["InvokeFunction", "CreateFunction", "UpdateFunction"],
            "rds": ["CreateDBInstance", "DescribeDBInstances", "ModifyDBInstance"],
            "dynamodb": ["GetItem", "PutItem", "Query", "Scan"]
        }
    
    def _create_user_profiles(self) -> List[UserProfile]:
        """Create diverse user profiles"""
        departments = ["Engineering", "Sales", "Marketing", "Finance", "HR", "IT"]
        locations = [
            ("New York, US", "40.7128,-74.0060", "192.168.1."),
            ("San Francisco, US", "37.7749,-122.4194", "10.0.1."),
            ("London, UK", "51.5074,-0.1278", "172.16.1."),
            ("Tokyo, Japan", "35.6762,139.6503", "192.168.10."),
        ]
        
        users = []
        for i in range(100):  # 100 synthetic users
            dept = random.choice(departments)
            location = random.choice(locations)
            is_admin = i < 5  # 5 admins
            is_privileged = i < 20  # 20 privileged users
            
            user = UserProfile(
                user_id=f"user_{i:03d}",
                email=f"user{i:03d}@company.com",
                name=f"User {i:03d}",
                department=dept,
                role="Admin" if is_admin else ("Manager" if is_privileged else "Developer"),
                is_admin=is_admin,
                is_privileged=is_privileged,
                
                typical_locations=[location[0]],
                typical_devices=[f"device_{i}_laptop", f"device_{i}_mobile"],
                typical_ips=[f"{location[2]}{random.randint(10, 250)}"],
                typical_hours=list(range(9, 18)),  # 9 AM - 5 PM
                typical_endpoints=[
                    "/api/users", "/api/projects", "/api/files", "/api/reports"
                ],
                typical_cloud_actions=["DescribeInstances", "GetObject", "ListBucket"],
                
                avg_logins_per_day=3,
                avg_api_calls_per_day=random.randint(50, 500)
            )
            users.append(user)
        
        return users