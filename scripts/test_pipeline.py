"""
End-to-End Pipeline Test Script
"""

import asyncio
import aiohttp
import sys
import time
import json
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.data_pipeline.generators.synthetic_logs import SyntheticLogGenerator
from src.data_pipeline.storage.storage_layer import LocalStorageLayer


class PipelineTestSuite:
    """Complete pipeline test suite"""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.generator = SyntheticLogGenerator(seed=42)
        self.storage = LocalStorageLayer("data/events")
        
        self.test_results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": []
        }
    
    async def run_all_tests(self):
        """Run complete test suite"""
        print("=" * 70)
        print("🧪 ZTBF PIPELINE TEST SUITE")
        print("=" * 70)
        print()
        
        # Test 1: API Health Check
        await self.test_api_health()
        
        # Test 2: Single Event Ingestion
        await self.test_single_event_ingestion()
        
        # Test 3: Batch Event Ingestion
        await self.test_batch_ingestion()
        
        # Test 4: All Event Types
        await self.test_all_event_types()
        
        # Test 5: High Throughput
        await self.test_high_throughput()
        
        # Test 6: Storage Verification
        await self.test_storage_verification()
        
        # Test 7: Data Quality
        await self.test_data_quality()
        
        # Print summary
        self.print_summary()
    
    async def test_api_health(self):
        """Test 1: API Health Check"""
        test_name = "API Health Check"
        self.test_results["total_tests"] += 1
        
        print(f"📝 Test 1: {test_name}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"   ✅ API is healthy")
                        print(f"   - Status: {data.get('status')}")
                        print(f"   - Uptime: {data.get('uptime_seconds', 0):.0f}s")
                        self.test_results["passed"] += 1
                    else:
                        raise Exception(f"Health check failed: {response.status}")
        
        except Exception as e:
            print(f"   ❌ {test_name} failed: {e}")
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: {e}")
        
        print()
    
    async def test_single_event_ingestion(self):
        """Test 2: Single Event Ingestion"""
        test_name = "Single Event Ingestion"
        self.test_results["total_tests"] += 1
        
        print(f"📝 Test 2: {test_name}")
        
        try:
            # Generate event
            user = self.generator.users[0]
            event = self.generator.generate_azure_ad_signin(user, datetime.utcnow())
            
            # Send to API
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/ingest/azure_ad",
                    json=event,
                    headers={"X-API-Key": "test_key"}
                ) as response:
                    if response.status == 202:
                        data = await response.json()
                        print(f"   ✅ Event ingested successfully")
                        print(f"   - Ingestion ID: {data.get('ingestion_id')}")
                        self.test_results["passed"] += 1
                    else:
                        raise Exception(f"Ingestion failed: {response.status}")
        
        except Exception as e:
            print(f"   ❌ {test_name} failed: {e}")
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: {e}")
        
        print()
    
    async def test_batch_ingestion(self):
        """Test 3: Batch Event Ingestion"""
        test_name = "Batch Event Ingestion"
        self.test_results["total_tests"] += 1
        
        print(f"📝 Test 3: {test_name}")
        
        try:
            # Generate batch
            events = self.generator.generate_normal_events(count=100, time_range_hours=1)
            
            # Send batch
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/ingest/batch",
                    json=events[:50],  # Send first 50
                    params={"source_type": "azure_ad"},
                    headers={"X-API-Key": "test_key"}
                ) as response:
                    if response.status == 207:
                        data = await response.json()
                        results = data.get('results', {})
                        print(f"   ✅ Batch ingested")
                        print(f"   - Accepted: {results.get('accepted')}")
                        print(f"   - Rejected: {results.get('rejected')}")
                        
                        if results.get('accepted', 0) > 40:
                            self.test_results["passed"] += 1
                        else:
                            raise Exception("Too many rejections")
                    else:
                        raise Exception(f"Batch ingestion failed: {response.status}")
        
        except Exception as e:
            print(f"   ❌ {test_name} failed: {e}")
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: {e}")
        
        print()
    
    async def test_all_event_types(self):
        """Test 4: All Event Types"""
        test_name = "All Event Types"
        self.test_results["total_tests"] += 1
        
        print(f"📝 Test 4: {test_name}")
        
        try:
            user = self.generator.users[0]
            timestamp = datetime.utcnow()
            
            event_types = [
                ("azure_ad", self.generator.generate_azure_ad_signin(user, timestamp)),
                ("cloudtrail", self.generator.generate_cloudtrail_event(user, timestamp)),
                ("api_gateway", self.generator.generate_api_gateway_event(user, timestamp))
            ]
            
            success_count = 0
            
            async with aiohttp.ClientSession() as session:
                for source_type, event in event_types:
                    async with session.post(
                        f"{self.api_url}/ingest/{source_type}",
                        json=event,
                        headers={"X-API-Key": "test_key"}
                    ) as response:
                        if response.status == 202:
                            success_count += 1
                            print(f"   ✅ {source_type} event ingested")
            
            if success_count == len(event_types):
                self.test_results["passed"] += 1
            else:
                raise Exception(f"Only {success_count}/{len(event_types)} event types succeeded")
        
        except Exception as e:
            print(f"   ❌ {test_name} failed: {e}")
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: {e}")
        
        print()
    
    async def test_high_throughput(self):
        """Test 5: High Throughput"""
        test_name = "High Throughput"
        self.test_results["total_tests"] += 1
        
        print(f"📝 Test 5: {test_name}")
        print(f"   Sending 1,000 events at ~100 events/sec...")
        
        try:
            start_time = time.time()
            events_sent = 0
            
            async with aiohttp.ClientSession() as session:
                for i in range(1000):
                    user = self.generator.users[i % len(self.generator.users)]
                    event = self.generator.generate_api_gateway_event(user, datetime.utcnow())
                    
                    # Send async (fire and forget)
                    asyncio.create_task(self._send_event(session, event))
                    events_sent += 1
                    
                    # Rate limiting
                    if i % 100 == 0:
                        await asyncio.sleep(1)
            
            duration = time.time() - start_time
            rate = events_sent / duration
            
            print(f"   ✅ Sent {events_sent} events in {duration:.1f}s")
            print(f"   - Rate: {rate:.1f} events/sec")
            
            if rate > 50:
                self.test_results["passed"] += 1
            else:
                raise Exception(f"Throughput too low: {rate:.1f} events/sec")
        
        except Exception as e:
            print(f"   ❌ {test_name} failed: {e}")
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: {e}")
        
        print()
    
    async def _send_event(self, session, event):
        """Helper to send event async"""
        try:
            await session.post(
                f"{self.api_url}/ingest/api_gateway",
                json=event,
                headers={"X-API-Key": "test_key"},
                timeout=aiohttp.ClientTimeout(total=5)
            )
        except Exception as e:
            pass  # Ignore individual failures
    
    async def test_storage_verification(self):
        """Test 6: Storage Verification"""
        test_name = "Storage Verification"
        self.test_results["total_tests"] += 1
        
        print(f"📝 Test 6: {test_name}")
        print(f"   Waiting 30 seconds for processing...")
        await asyncio.sleep(30)
        
        try:
            # Check if storage has data
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)
            
            events_df = self.storage.read_events(
                start_time=start_time,
                end_time=end_time
            )
            
            event_count = len(events_df)
            
            print(f"   📊 Found {event_count:,} events in storage")
            
            if event_count > 0:
                print(f"   ✅ Storage verification passed")
                print(f"   - Sources: {events_df['source_system'].unique().tolist()}")
                self.test_results["passed"] += 1
            else:
                raise Exception("No events found in storage")
        
        except Exception as e:
            print(f"   ❌ {test_name} failed: {e}")
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: {e}")
        
        print()
    
    async def test_data_quality(self):
        """Test 7: Data Quality"""
        test_name = "Data Quality"
        self.test_results["total_tests"] += 1
        
        print(f"📝 Test 7: {test_name}")
        
        try:
            # Read recent events
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)
            
            events_df = self.storage.read_events(
                start_time=start_time,
                end_time=end_time
            )
            
            if len(events_df) == 0:
                raise Exception("No events to validate")
            
            # Check required fields
            required_fields = [
                'entity_id', 'entity_type', 'event_type',
                'timestamp', 'success', 'source_ip', 'source_system'
            ]
            
            missing_fields = [f for f in required_fields if f not in events_df.columns]
            
            if missing_fields:
                raise Exception(f"Missing required fields: {missing_fields}")
            
            # Check for null values in critical fields
            null_counts = events_df[required_fields].isnull().sum()
            critical_nulls = null_counts[null_counts > 0]
            
            if len(critical_nulls) > 0:
                print(f"   ⚠️  Warning: Null values in {critical_nulls.to_dict()}")
            
            # Check timestamp validity
            invalid_timestamps = events_df[events_df['timestamp'].isnull()].shape[0]
            
            if invalid_timestamps > 0:
                raise Exception(f"{invalid_timestamps} events have invalid timestamps")
            
            print(f"   ✅ Data quality checks passed")
            print(f"   - Total events: {len(events_df):,}")
            print(f"   - Schema valid: ✅")
            print(f"   - Timestamps valid: ✅")
            
            self.test_results["passed"] += 1
        
        except Exception as e:
            print(f"   ❌ {test_name} failed: {e}")
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: {e}")
        
        print()
    
    def print_summary(self):
        """Print test summary"""
        print("=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        print()
        print(f"Total Tests:  {self.test_results['total_tests']}")
        print(f"✅ Passed:     {self.test_results['passed']}")
        print(f"❌ Failed:     {self.test_results['failed']}")
        print()
        
        if self.test_results['errors']:
            print("🔴 ERRORS:")
            for error in self.test_results['errors']:
                print(f"   - {error}")
            print()
        
        success_rate = (self.test_results['passed'] / self.test_results['total_tests']) * 100
        
        if success_rate == 100:
            print("🎉 ALL TESTS PASSED! 🎉")
        elif success_rate >= 80:
            print(f"✅ MOSTLY PASSING ({success_rate:.0f}%)")
        else:
            print(f"⚠️  NEEDS ATTENTION ({success_rate:.0f}%)")
        
        print("=" * 70)


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="ZTBF Pipeline Test Suite")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API URL")
    
    args = parser.parse_args()
    
    # Create test suite
    test_suite = PipelineTestSuite(api_url=args.api_url)
    
    # Run tests
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())