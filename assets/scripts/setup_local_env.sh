#!/bin/bash
# ZTBF Local Environment Setup Script

set -e  # Exit on error

echo "ZTBF Data Pipeline - Local Environment Setup"
echo "================================================"
echo ""

# ===== CHECK PREREQUISITES =====
echo "Checking prerequisites..."

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python $PYTHON_VERSION found"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed"
    echo "   Install from: https://docs.docker.com/get-docker/"
    exit 1
fi
echo "Docker found"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "docker-compose not found, trying 'docker compose'"
    DOCKER_COMPOSE_CMD="docker compose"
else
    DOCKER_COMPOSE_CMD="docker-compose"
    echo "Docker Compose found"
fi

echo ""

# ===== CREATE DIRECTORY STRUCTURE =====
echo "Creating directory structure..."

mkdir -p data/events
mkdir -p data/queue
mkdir -p logs
mkdir -p configs
mkdir -p deployment/docker

echo "Directories created"
echo ""

# ===== SETUP PYTHON ENVIRONMENT =====
echo "Setting up Python virtual environment..."

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate

echo "Installing Python dependencies..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

echo "Python dependencies installed"
echo ""

# ===== START DOCKER SERVICES =====
echo "Starting Docker services..."

cd deployment/docker

# Start MinIO
$DOCKER_COMPOSE_CMD up -d minio minio-init

echo "Waiting for MinIO to be ready..."
sleep 10

# Check MinIO health
if curl -f http://localhost:9000/minio/health/live > /dev/null 2>&1; then
    echo "MinIO is running"
    echo "   - API: http://localhost:9000"
    echo "   - Console: http://localhost:9001"
    echo "   - Username: minioadmin"
    echo "   - Password: minioadmin"
else
    echo "MinIO failed to start"
    exit 1
fi

# Start Redis (optional)
read -p "Do you want to start Redis? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    $DOCKER_COMPOSE_CMD up -d redis
    echo "Redis is running on port 6379"
fi

cd ../..

echo ""

# ===== GENERATE SAMPLE DATA =====
echo "Generating sample data..."

python3 src/data_pipeline/generators/synthetic_logs.py \
    --count 1000 \
    --output data/synthetic_events_normal.json \
    --scenario normal

echo "Generated 1,000 sample events"
echo ""

# ===== CREATE SYSTEMD SERVICES (Optional) =====
read -p "Do you want to create systemd services for auto-start? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Creating systemd service files..."
    
    # Create service file for ingestion API
    cat > /tmp/ztbf-api.service <<EOF
[Unit]
Description=ZTBF Ingestion API
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/uvicorn src.data_pipeline.ingestion.api:app --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

    # Create service file for processor
    cat > /tmp/ztbf-processor.service <<EOF
[Unit]
Description=ZTBF Event Processor
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/python src/data_pipeline/processing/processor.py --workers 8
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

    echo "Service files created in /tmp/"
    echo "To install (requires sudo):"
    echo "  sudo cp /tmp/ztbf-*.service /etc/systemd/system/"
    echo "  sudo systemctl daemon-reload"
    echo "  sudo systemctl enable ztbf-api ztbf-processor"
    echo "  sudo systemctl start ztbf-api ztbf-processor"
fi

echo ""

# ===== VERIFY INSTALLATION =====
echo "Verifying installation..."

# Check if all required Python packages are installed
python3 -c "import fastapi, pydantic, pandas, pyarrow" && echo "Core Python packages OK"

# Check if data directories exist
[ -d "data/events" ] && echo "Data directories OK"

# Check if logs directory exists
[ -d "logs" ] && echo "Logs directory OK"

echo ""

# ===== COMPLETION =====
echo "Setup Complete!"
echo ""
echo "================================================"
echo "NEXT STEPS"
echo "================================================"
echo ""
echo "1. Start the Ingestion API:"
echo "   uvicorn src.data_pipeline.ingestion.api:app --reload --port 8000"
echo ""
echo "2. Start the Event Processor (in another terminal):"
echo "   python src/data_pipeline/processing/processor.py --workers 8"
echo ""
echo "3. Test the pipeline:"
echo "   python scripts/test_pipeline.py"
echo ""
echo "4. Access services:"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - API Health: http://localhost:8000/health"
echo "   - MinIO Console: http://localhost:9001"
echo ""
echo "5. Generate and ingest test data:"
echo "   python scripts/ingest_synthetic_data.py --rate 100"
echo ""
echo "================================================"
echo "DOCUMENTATION"
echo "================================================"
echo ""
echo "- Phase 1 Guide: docs/phase1_implementation_guide.md"
echo "- Architecture: architecture/data_pipeline_design.md"
echo "- Configuration: configs/pipeline_config.yaml"
echo ""
echo "Happy coding! 🚀"