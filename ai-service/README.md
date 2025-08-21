# Fall Detection API 🚨

SmolVLM2 tabanlı düşme tespiti yapan containerized FastAPI servisi.

## 🏗️ Sistem Mimarisi

```
FastAPI-POST [görsel] → Model [analiz] → PostgreSQL [sonuç] → FastAPI-GET [hash+sonuç]
```

## 🚀 Hızlı Başlangıç

### 1. Sistem Gereksinimleri
- Docker ve Docker Compose
- NVIDIA GPU (CUDA 12.1+ destekli)
- nvidia-docker runtime

### 2. Servisları Başlat
```bash
# Tüm servisleri başlat
docker-compose up -d

# Sadece AI servisi (pgAdmin olmadan)
docker-compose up -d postgres ai-service

# pgAdmin ile birlikte (veritabanı yönetimi için)
docker-compose --profile admin up -d
```

### 3. Servis Durumunu Kontrol Et
```bash
# Health check
curl http://localhost:8000/health

# API dokümantasyonu
# Browser'da: http://localhost:8000/docs
```

## 📡 API Endpoints

### 🔍 Health Check
```bash
GET /health
```
**Yanıt:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "database_connected": true,
  "gpu_available": true,
  "statistics": {...}
}
```

### 🖼️ Tek Görsel Analizi
```bash
POST /detect-fall/
Content-Type: multipart/form-data
```

**cURL örneği:**
```bash
curl -X POST \
  http://localhost:8000/detect-fall/ \
  -F "file=@/path/to/image.jpg"
```

**Yanıt:**
```json
{
  "image_hash": "abc123...",
  "result": "Yes",
  "confidence": 0.85,
  "image_size": "640x480",
  "processing_time_ms": 1250,
  "cached": false
}
```

### 📚 Batch Görsel Analizi
```bash
POST /detect-fall-batch/
Content-Type: multipart/form-data
```

**cURL örneği:**
```bash
curl -X POST \
  http://localhost:8000/detect-fall-batch/ \
  -F "files=@image1.jpg" \
  -F "files=@image2.jpg" \
  -F "files=@image3.jpg"
```

**Yanıt:**
```json
{
  "results": [
    {
      "filename": "image1.jpg",
      "image_hash": "abc123...",
      "result": "Yes",
      "confidence": 0.85,
      "processing_time_ms": 1250,
      "cached": false
    },
    {...}
  ]
}
```

### 🔍 Hash ile Sonuç Sorgulama
```bash
GET /result/{image_hash}
```

**Örnek:**
```bash
curl http://localhost:8000/result/abc123456...
```

### 📊 İstatistikler
```bash
GET /statistics
```

**Yanıt:**
```json
{
  "total_processed": 1247,
  "fall_detected": 89,
  "no_fall": 1158,
  "avg_processing_time_ms": 1180.5,
  "days_active": 15
}
```

## 🧪 Test Etme

### Otomatik Test Script
```bash
python test_api.py
```

### Manuel Test
```bash
# Health check
curl http://localhost:8000/health

# Tek görsel test
curl -X POST \
  http://localhost:8000/detect-fall/ \
  -F "file=@test_image.jpg"

# İstatistikler
curl http://localhost:8000/statistics
```

## 🔧 Konfigürasyon

### Environment Variables
```bash
# Database
DB_HOST=postgres
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=fall_detection

# Python
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1

# HuggingFace Cache
TRANSFORMERS_CACHE=/app/.cache/transformers
HF_HOME=/app/.cache/huggingface
```

### Docker Compose Profiller
```bash
# Sadece temel servisler
docker-compose up -d

# pgAdmin ile birlikte
docker-compose --profile admin up -d
```

## 📊 Veritabanı

### Tablo Yapısı
```sql
fall_detections:
- id (SERIAL PRIMARY KEY)
- image_hash (VARCHAR(64) UNIQUE)
- result (VARCHAR(10)) -- 'Yes' or 'No'
- confidence (FLOAT)
- created_at (TIMESTAMP)
- image_size (VARCHAR(20))
- processing_time_ms (INTEGER)
```

### pgAdmin Erişim
- URL: http://localhost:8080
- Email: admin@falldetection.com
- Password: admin123

## 🚨 Önemli Özellikler

### ✅ Cache Sistemi
- Aynı görseller (SHA256 hash) için veritabanından sonuç döner
- Duplicate processing önlenir
- Hızlı yanıt süresi

### ✅ Multi-Crop Voting
- Her görsel 3 farklı crop ile analiz edilir
- Çoğunluk oylaması ile sonuç belirlenir
- Daha güvenilir sonuçlar

### ✅ GPU Optimizasyonu
- NVIDIA CUDA desteği
- Model GPU'da çalışır
- Memory management ile efficient kullanım

### ✅ Async Processing
- Non-blocking operations
- Multiple request handling
- Better performance

## 🔧 Sorun Giderme

### Model Yüklenmiyor
```bash
# Container logs kontrol et
docker-compose logs ai-service

# CUDA kontrol et
docker exec -it fall_detection_api nvidia-smi
```

### Database Bağlantı Sorunu
```bash
# PostgreSQL status
docker-compose logs postgres

# Database bağlantı test
docker exec -it fall_detection_db psql -U postgres -d fall_detection
```

### Memory/GPU Sorunları
```bash
# GPU memory kullanımı
docker exec -it fall_detection_api nvidia-smi

# Container resources
docker stats fall_detection_api
```

## 📈 Performance

### Beklenen Performans
- **Tek görsel**: ~1-2 saniye (ilk kez)
- **Cache hit**: ~50-100ms
- **Batch processing**: Paralel olmayan, sıralı işlem
- **Memory usage**: ~4-8GB GPU VRAM

### Optimizasyon İpuçları
1. Model cache volume kullan (daha hızlı restart)
2. Aynı görselleri tekrar gönderme (cache)
3. Batch yerine parallel single requests
4. GPU memory monitoring

## 🔒 Güvenlik

- Non-root user container
- No image storage (memory only)
- Environment variables for config
- Health checks for monitoring

## 📝 Geliştirme

### Local Development
```bash
# Virtual environment
python -m venv venv
source venv/bin/activate

# Dependencies
pip install -r requirements.txt

# Run locally
python main.py
```

### Logs
```bash
# Container logs
docker-compose logs -f ai-service

# Database logs
docker-compose logs -f postgres
```

---

📧 **Support**: [GitHub Issues](https://github.com/your-repo/issues)
🚀 **Version**: 1.0.0
