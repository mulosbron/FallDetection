# Fall Detection API

Containerized FastAPI service for fall detection powered by SmolVLM2. Images are processed in-memory, hashed with SHA256, and results are cached in PostgreSQL. Same image → instant cached response.

## Architecture

```
Client (POST image) → FastAPI → Model → PostgreSQL → FastAPI (GET by hash)
```

## Requirements
- Docker + Docker Compose
- GPU optional (CUDA 12.1 supported). If you want GPU pass-through: install NVIDIA Container Toolkit

## Quick Start

```bash
# from ai-service directory
docker-compose up -d --build

# Check health in browser:
# http://localhost:8000/health
```

Notes
- The model loads on startup in the background. Until it is ready, endpoints may return 503 “Model loading, try again shortly”. Retry after several seconds.
- PostgreSQL is auto-initialized with schema and a statistics view.

## Configuration (env)
```bash
DB_HOST=postgres
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=fall_detection

PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1

HF_HOME=/app/.cache/huggingface
TRANSFORMERS_CACHE=/app/.cache/transformers
```

## API Endpoints

### Health
```
GET /health
```
Example response:
```json
{
  "status": "healthy",
  "model_loaded": true,
  "database_connected": true,
  "gpu_available": true,
  "statistics": {"total_processed": 2, "fall_detected": 1, "no_fall": 1, ...}
}
```

### Detect fall (single image)
```
POST /detect-fall/
Content-Type: multipart/form-data (key: file)
```

Response
```json
{
  "image_hash": "...",
  "result": "Yes",
  "confidence": 0.85,
  "image_size": "640x480",
  "processing_time_ms": 1250,
  "cached": false
}
```

### Detect fall (batch)
```
POST /detect-fall-batch/
Content-Type: multipart/form-data (key: files, repeated)
```

### Get result by hash
```
GET /result/{image_hash}
```

### Statistics
```
GET /statistics
```

## Postman

Collection file:
`api_test/falldetection_ai_service.postman_collection.json`

Usage:
- Import the collection into Postman
- (Optional) create environment variable `baseUrl = http://localhost:8000`
- Single image: Body → form-data → key `file` (Type: File)
- Batch: Body → form-data → multiple rows with key `files` (Type: File)
- Do not set Content-Type manually; Postman will add multipart boundary
- If first requests time out while the model loads, increase Request timeout (e.g., 120s)

## Run locally (without Docker)
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
python main.py
```

## Database

Table: `fall_detections`
```sql
id SERIAL PRIMARY KEY
image_hash VARCHAR(64) UNIQUE NOT NULL
result VARCHAR(10) NOT NULL  -- Yes | No
confidence FLOAT
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
image_size VARCHAR(20)
processing_time_ms INTEGER
```

View: `fall_detection_stats` (averages with proper numeric casts)