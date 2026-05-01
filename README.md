# FallDetection Platform

Multi-service architecture for a fall detection scenario:
- `FallDetectionAPI/`: .NET API + SignalR
- `ai-service/`: FastAPI-based AI inference service
- `mock-camera-service/`: MediaMTX + FFmpeg test camera streaming
- `factory-dashboard/`: React dashboard (HLS monitoring + event panel)
- `bruno_falldetection/`: API test collection

## Quick flow

1. `mock-camera-service` publishes test video streams via RTSP/HLS.
2. `FallDetectionAPI` manages camera inventory and event flow.
3. `ai-service` is called by the API to produce predictions.
4. `factory-dashboard` shows video and events through API + SignalR + HLS.

## Default ports

| Service | Port | Compose path |
|--------|-----:|--------------|
| WebAPI | 5000 | `FallDetectionAPI/docker-compose.yml` |
| SignalR | 5001 | `FallDetectionAPI/docker-compose.yml` |
| AI | 8200 | `ai-service/docker-compose.yml` |
| MediaMTX | 8554 (RTSP), 8888 (HLS) | `mock-camera-service/docker-compose.yml` |
| Dashboard | 3000 | `factory-dashboard/docker-compose.yml` |

## Run services with Docker

There is no single central compose file; each service is started from its own folder.

First, create the shared network once:

```bash
docker network create fall_detection_network
```

Then use this typical startup order:

1. Mock camera
```bash
cd mock-camera-service && docker compose up -d --build
```

2. AI service (a token may be required for initial model download)
```bash
# PowerShell
$env:HF_TOKEN="hf_xxx"
cd ai-service && docker compose up -d --build
```

3. API + SignalR + Postgres
```bash
cd FallDetectionAPI && docker compose up -d --build
```

4. Dashboard
```bash
cd factory-dashboard && docker compose up -d --build
```

Access:
- Dashboard: `http://localhost:3000`
- API: `http://localhost:5000`
- SignalR: `http://localhost:5001`
- HLS: `http://localhost:8888`

## Folder structure

```text
FallDetection/
├── FallDetectionAPI/        # .NET API + SignalR + layered backend
├── ai-service/              # FastAPI-based AI service
├── mock-camera-service/     # RTSP/HLS test streaming infrastructure
├── factory-dashboard/       # React dashboard
└── bruno_falldetection/     # Bruno API test collection
```
