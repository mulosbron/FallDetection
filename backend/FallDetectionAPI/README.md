# Fall Detection API

A .NET 9.0 Web API for factory security systems that performs fall detection using AI. The system simulates 4 cameras, processes video frames through a queue system, forwards them to an AI service, and the AI service persists results in PostgreSQL.

## 🏗️ Architecture

```
Video Simulation → .NET API → Bounded Queue → Background Service → FastAPI (AI Service) → PostgreSQL
```

## ⚡ Features

- 4 camera video simulation (~10 FPS each)
- Bounded queue and background batch processing (max 10 frames/flush)
- Robust retry with exponential backoff
- Docker Compose ready
- Results persisted by AI service in PostgreSQL
- Unified .NET endpoints to query health, statistics and results

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- .NET 9.0 SDK (optional, local dev)

### Using Docker Compose (Recommended)
```bash
# Start the backend API
docker compose up -d --build

# View logs
docker compose logs -f backend

# Stop
docker compose down
```

## 📡 API Endpoints

### Camera Simulation (`/api/camera`)
```http
POST /api/camera/start          # Start 4-camera simulation
POST /api/camera/stop           # Stop simulation
GET  /api/camera/status         # Simulation status, queue count
GET  /api/camera/metrics        # Performance metrics
```

### Results & Health (`/api/results`)
```http
GET /api/results/statistics/ai-service    # AI service statistics
GET /api/results/result/{imageHash}       # Query single result by SHA256 image hash
GET /api/results/hashes                   # List all image hashes (from PostgreSQL)
GET /api/results/health/ai-service        # AI service health (status, model, db, gpu)
GET /api/results/health/net-api           # .NET API health (uptime, memory, env)
```

### Frames (`/api/frames`)
```http
POST /api/frames                # Upload single frame (multipart/form-data)
GET  /api/frames/{jobId}        # Get job status by id
GET  /api/frames/queue/status   # Current queue size and status
```

## ⚙️ Configuration

`appsettings.json` (backend):
```json
{
  "ConnectionStrings": {
    "Default": "Host=localhost;Port=5432;Database=fall_detection;Username=postgres;Password=postgres"
  },
  "AiService": {
    "BaseUrl": "http://ai-service:8000"
  },
  "Queue": {
    "Capacity": 200,
    "FlushIntervalMs": 1000,
    "MaxBatchSize": 10
  }
}
```

## 🔄 Workflow

1. .NET API simulates frames from 4 video files
2. Frames are queued (bounded, cap=200)
3. Background service flushes batches (≤10) to AI service
4. AI service detects fall and writes results to PostgreSQL
5. .NET API exposes endpoints to query AI statistics, health, and results

## 🧪 Testing Cheatsheet

```bash
# .NET API health
curl http://localhost:5000/api/results/health/net-api

# AI service health (proxied by .NET)
curl http://localhost:5000/api/results/health/ai-service

# AI service statistics (proxied by .NET)
curl http://localhost:5000/api/results/statistics/ai-service

# Start camera simulation
curl -X POST http://localhost:5000/api/camera/start

# Check simulation status
curl http://localhost:5000/api/camera/status

# Upload one frame
curl -X POST http://localhost:5000/api/frames \
  -F "image=@test.jpg" \
  -F "cameraId=1"

# Query a result by hash (from AI service DB)
curl http://localhost:5000/api/results/result/{IMAGE_HASH}

# List all hashes (from PostgreSQL via .NET)
curl http://localhost:5000/api/results/hashes
```

## 📊 Response Examples

### AI Service Health
```json
{
  "source": "AI Service Health Check",
  "timestamp": "2025-08-22T00:45:00.000Z",
  "health": {
    "status": "healthy",
    "model_loaded": true,
    "database_connected": true,
    "gpu_available": true
  }
}
```

### AI Service Statistics
```json
{
  "source": "AI Service Database",
  "timestamp": "2025-08-22T00:45:00.000Z",
  "statistics": {
    "total_processed": 470,
    "fall_detected": 2,
    "no_fall": 468,
    "avg_processing_time_ms": 3253.41,
    "days_active": 2
  }
}
```

### Single Result
```json
{
  "source": "AI Service Database",
  "timestamp": "2025-08-22T00:45:00.000Z",
  "result": {
    "image_hash": "...",
    "result": "No",
    "confidence": 1.0,
    "image_size": "800x600",
    "processing_time_ms": 3200,
    "cached": true
  }
}
```

## 🧰 Development

```bash
# Build
dotnet build

# Clean
dotnet clean

# Run
dotnet run
```

Notes:
- The AI service owns all database writes for detection results.
- The .NET API provides a clean integration surface and observability endpoints.
