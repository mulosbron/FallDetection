#!/bin/bash

# Fall Detection Service Başlatma Script'i
echo "🚀 Fall Detection Service Starting..."

# GPU kontrolü
if command -v nvidia-smi &> /dev/null; then
    echo "✅ NVIDIA GPU detected"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
else
    echo "⚠️ No NVIDIA GPU detected, service will run on CPU"
fi

# Docker kontrolü
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found! Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found! Please install Docker Compose first."
    exit 1
fi

# NVIDIA Docker runtime kontrolü
if docker info | grep -q nvidia; then
    echo "✅ NVIDIA Docker runtime detected"
else
    echo "⚠️ NVIDIA Docker runtime not detected, GPU features may not work"
fi

# Mevcut container'ları kapat
echo "🛑 Stopping existing containers..."
docker-compose down

# Yeni container'ları başlat
echo "🏗️ Building and starting services..."
docker-compose up -d --build

# Servis durumunu kontrol et
echo "⏳ Waiting for services to start..."
sleep 10

# Health check
echo "🔍 Checking service health..."
max_retries=30
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Services are healthy!"
        break
    else
        echo "⏳ Waiting for services... ($((retry_count + 1))/$max_retries)"
        sleep 5
        retry_count=$((retry_count + 1))
    fi
done

if [ $retry_count -eq $max_retries ]; then
    echo "❌ Services failed to start properly!"
    echo "📋 Container logs:"
    docker-compose logs --tail=20
    exit 1
fi

# Servis bilgileri
echo ""
echo "🎉 Fall Detection Service is running!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📡 API Endpoints:"
echo "   Health Check:    http://localhost:8000/health"
echo "   API Docs:        http://localhost:8000/docs"
echo "   Single Image:    POST http://localhost:8000/detect-fall/"
echo "   Batch Images:    POST http://localhost:8000/detect-fall-batch/"
echo "   Statistics:      GET http://localhost:8000/statistics"
echo ""
echo "🗄️ Database:"
echo "   PostgreSQL:      localhost:5432"
echo "   pgAdmin:         http://localhost:8080 (start with --profile admin)"
echo ""
echo "🔧 Management:"
echo "   View logs:       docker-compose logs -f"
echo "   Stop services:   docker-compose down"
echo "   Restart:         docker-compose restart"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test script öneri
echo ""
echo "🧪 Test the service:"
echo "   python test_api.py"
echo ""
echo "📊 Quick test:"
echo "   curl http://localhost:8000/health"
echo ""

# Background'da log takibi başlat (isteğe bağlı)
read -p "📋 Show live logs? (y/N): " show_logs
if [[ $show_logs == "y" || $show_logs == "Y" ]]; then
    echo "📋 Showing live logs (Ctrl+C to exit)..."
    docker-compose logs -f
fi
