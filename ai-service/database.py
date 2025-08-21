import asyncpg
import hashlib
import json
import os
from datetime import datetime
from typing import Optional, List, Dict
import logging

# Database configuration
DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
    "database": os.getenv("DB_NAME", "fall_detection")
}

class DatabaseManager:
    def __init__(self):
        self.pool = None
        
    async def connect(self):
        """PostgreSQL bağlantı havuzu oluştur"""
        try:
            self.pool = await asyncpg.create_pool(**DATABASE_CONFIG)
            await self.create_tables()
            logging.info("✅ Database connected successfully")
        except Exception as e:
            logging.error(f"❌ Database connection failed: {e}")
            raise
            
    async def disconnect(self):
        """Bağlantı havuzunu kapat"""
        if self.pool:
            await self.pool.close()
            
    async def create_tables(self):
        """Gerekli tabloları oluştur"""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS fall_detections (
            id SERIAL PRIMARY KEY,
            image_hash VARCHAR(64) UNIQUE NOT NULL,
            result VARCHAR(10) NOT NULL,
            confidence FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            image_size VARCHAR(20),
            processing_time_ms INTEGER
        );
        
        CREATE INDEX IF NOT EXISTS idx_image_hash ON fall_detections(image_hash);
        CREATE INDEX IF NOT EXISTS idx_created_at ON fall_detections(created_at);
        """
        
        async with self.pool.acquire() as conn:
            await conn.execute(create_table_query)
            
    def calculate_image_hash(self, image_bytes: bytes) -> str:
        """Görsel için SHA256 hash hesapla"""
        return hashlib.sha256(image_bytes).hexdigest()
        
    async def check_existing_result(self, image_hash: str) -> Optional[Dict]:
        """Varolan sonucu kontrol et"""
        query = """
        SELECT image_hash, result, confidence, created_at, image_size, processing_time_ms
        FROM fall_detections 
        WHERE image_hash = $1
        """
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, image_hash)
            if row:
                return {
                    "image_hash": row["image_hash"],
                    "result": row["result"],
                    "confidence": row["confidence"],
                    "created_at": row["created_at"].isoformat(),
                    "image_size": row["image_size"],
                    "processing_time_ms": row["processing_time_ms"],
                    "cached": True
                }
        return None
        
    async def save_result(self, image_hash: str, result: str, confidence: float = None, 
                         image_size: str = None, processing_time_ms: int = None) -> bool:
        """Sonucu veritabanına kaydet"""
        query = """
        INSERT INTO fall_detections (image_hash, result, confidence, image_size, processing_time_ms)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (image_hash) DO NOTHING
        """
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(query, image_hash, result, confidence, image_size, processing_time_ms)
            return True
        except Exception as e:
            logging.error(f"Database save error: {e}")
            return False
            
    async def get_statistics(self) -> Dict:
        """Genel istatistikleri getir"""
        query = """
        SELECT 
            COUNT(*) as total_processed,
            COUNT(CASE WHEN result = 'Yes' THEN 1 END) as fall_detected,
            COUNT(CASE WHEN result = 'No' THEN 1 END) as no_fall,
            AVG(processing_time_ms) as avg_processing_time,
            COUNT(DISTINCT DATE(created_at)) as days_active
        FROM fall_detections
        """
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query)
            return {
                "total_processed": row["total_processed"],
                "fall_detected": row["fall_detected"],
                "no_fall": row["no_fall"],
                "avg_processing_time_ms": round(row["avg_processing_time"], 2) if row["avg_processing_time"] else 0,
                "days_active": row["days_active"]
            }

# Global database manager instance
db_manager = DatabaseManager()
