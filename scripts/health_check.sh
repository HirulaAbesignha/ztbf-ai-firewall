#!/bin/bash
# scripts/health_check.sh

echo "🔍 Checking ZTBF Services..."

# Check MinIO
if curl -f http://localhost:9000/minio/health/live > /dev/null 2>&1; then
    echo "✅ MinIO is healthy"
else
    echo "❌ MinIO is down"
    exit 1
fi

# Check API
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Ingestion API is healthy"
else
    echo "❌ Ingestion API is down"
    exit 1
fi

# Check storage
if [ -d "data/events" ]; then
    echo "✅ Storage directory exists"
else
    echo "❌ Storage directory missing"
    exit 1
fi

echo "🎉 All services healthy!"