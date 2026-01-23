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

    def _create_service_profiles(self) -> List[ServiceProfile]:
        """Create service account profiles"""
        services = []
        
        # API services
        for i in range(20):
            service = ServiceProfile(
                service_id=f"service_api_{i:02d}",
                service_name=f"api-service-{i:02d}",
                service_type="api",
                source_ips=[f"10.0.{i}.{random.randint(10, 250)}"],
                typical_endpoints=["/api/data", "/api/compute", "/api/storage"],
                call_rate_per_minute=random.randint(10, 100),
                typical_hours=list(range(24))  # 24/7
            )
            services.append(service)
        
        # Batch services
        for i in range(5):
            service = ServiceProfile(
                service_id=f"service_batch_{i:02d}",
                service_name=f"batch-job-{i:02d}",
                service_type="batch",
                source_ips=[f"10.1.{i}.{random.randint(10, 250)}"],
                typical_endpoints=["/api/batch", "/api/export"],
                call_rate_per_minute=5,
                typical_hours=[0, 1, 2, 3]  # Midnight to 3 AM
            )
            services.append(service)
        
        return services
    
    def _load_locations(self) -> List[Dict]:
        """Load geographic locations for GeoIP simulation"""
        return [
            {"city": "New York", "country": "US", "lat": 40.7128, "lon": -74.0060},
            {"city": "San Francisco", "country": "US", "lat": 37.7749, "lon": -122.4194},
            {"city": "London", "country": "UK", "lat": 51.5074, "lon": -0.1278},
            {"city": "Tokyo", "country": "Japan", "lat": 35.6762, "lon": 139.6503},
            {"city": "Sydney", "country": "Australia", "lat": -33.8688, "lon": 151.2093},
            {"city": "Mumbai", "country": "India", "lat": 19.0760, "lon": 72.8777},
            {"city": "Berlin", "country": "Germany", "lat": 52.5200, "lon": 13.4050},
            {"city": "Toronto", "country": "Canada", "lat": 43.6532, "lon": -79.3832},
        ]
    
    # ===== NORMAL EVENT GENERATION =====
    
    def generate_azure_ad_signin(self, user: UserProfile, timestamp: datetime, anomalous: bool = False) -> Dict:
        """Generate Azure AD sign-in event"""
        location = random.choice(user.typical_locations) if not anomalous else random.choice(["Beijing, China", "Moscow, Russia"])
        device = random.choice(user.typical_devices) if not anomalous else f"unknown_device_{random.randint(1000, 9999)}"
        ip = random.choice(user.typical_ips) if not anomalous else f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"
        
        return {
            "id": str(uuid.uuid4()),
            "createdDateTime": timestamp.isoformat() + "Z",
            "userPrincipalName": user.email,
            "userId": user.user_id,
            "appId": "12345678-1234-1234-1234-123456789012",
            "appDisplayName": "Office 365",
            "ipAddress": ip,
            "clientAppUsed": "Browser",
            "correlationId": str(uuid.uuid4()),
            
            "status": {
                "errorCode": 0 if not anomalous or random.random() > 0.3 else 50126,
                "failureReason": None if not anomalous else "Invalid credentials",
                "additionalDetails": None
            },
            
            "location": {
                "city": location.split(",")[0],
                "state": None,
                "countryOrRegion": location.split(", ")[1],
                "geoCoordinates": {
                    "latitude": 40.7128,
                    "longitude": -74.0060
                }
            },
            
            "deviceDetail": {
                "deviceId": device,
                "displayName": device.replace("_", " ").title(),
                "operatingSystem": "Windows 10",
                "browser": "Edge 110.0",
                "isCompliant": True,
                "isManaged": True
            },
            
            "riskLevelDuringSignIn": "high" if anomalous else random.choice(["none", "low"]),
            "riskLevelAggregated": "high" if anomalous else "low",
            "riskDetail": "anomalousActivity" if anomalous else "none",
            "riskState": "atRisk" if anomalous else "none",
            
            # ZTBF metadata
            "source_type": "azure_ad",
            "ingestion_timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    def generate_cloudtrail_event(self, user: UserProfile, timestamp: datetime, anomalous: bool = False) -> Dict:
        """Generate AWS CloudTrail event"""
        service = random.choice(self.cloud_services)
        action = random.choice(self.cloud_actions[service])
        
        # Anomalous behavior: privilege escalation actions
        if anomalous:
            service = "iam"
            action = random.choice(["CreateAccessKey", "AttachUserPolicy", "CreateUser", "PutUserPolicy"])
        
        return {
            "eventVersion": "1.08",
            "userIdentity": {
                "type": "AssumedRole" if anomalous and random.random() > 0.5 else "IAMUser",
                "principalId": f"AIDAI{random.randint(100000, 999999)}",
                "arn": f"arn:aws:iam::123456789012:user/{user.email.split('@')[0]}",
                "accountId": "123456789012",
                "userName": user.email.split('@')[0]
            },
            
            "eventTime": timestamp.isoformat() + "Z",
            "eventSource": f"{service}.amazonaws.com",
            "eventName": action,
            "awsRegion": "us-east-1",
            "sourceIPAddress": random.choice(user.typical_ips) if not anomalous else f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}",
            "userAgent": "aws-cli/2.13.0 Python/3.11.4 Windows/10",
            
            "requestParameters": {
                "bucketName": "company-data-bucket" if service == "s3" else None,
                "userName": f"new_user_{random.randint(1, 100)}" if action == "CreateUser" else None
            } if not anomalous else {
                "userName": "backdoor_admin",
                "policyArn": "arn:aws:iam::aws:policy/AdministratorAccess"
            },
            
            "responseElements": {
                "accessKey": {
                    "accessKeyId": f"AKIAI{random.randint(100000000000000, 999999999999999)}"
                } if action == "CreateAccessKey" else None
            },
            
            "requestID": str(uuid.uuid4()),
            "eventID": str(uuid.uuid4()),
            "eventType": "AwsApiCall",
            "recipientAccountId": "123456789012",
            
            "errorCode": "AccessDenied" if anomalous and random.random() > 0.7 else None,
            "errorMessage": "User is not authorized to perform this action" if anomalous and random.random() > 0.7 else None,
            
            # ZTBF metadata
            "source_type": "cloudtrail",
            "ingestion_timestamp": datetime.utcnow().isoformat() + "Z"
        }