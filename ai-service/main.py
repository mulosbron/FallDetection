from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import torch
from PIL import Image
import io
import time
import logging
import asyncio
from typing import List, Optional
from contextlib import asynccontextmanager
import uvloop

from database import db_manager
from model_service import ModelService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Global model service instance
model_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global model_service
    
    # Startup
    logging.info("🚀 Starting Fall Detection Service...")
    
    # Connect to database
    await db_manager.connect()
    
    # Initialize model service (background)
    model_service = ModelService()
    asyncio.create_task(model_service.initialize())
    logging.info("🧠 Model loading in background...")
    logging.info("✅ Service ready!")
    
    yield
    
    # Shutdown
    logging.info("🛑 Shutting down...")
    if model_service:
        await model_service.cleanup()
    await db_manager.disconnect()

# Create FastAPI app
app = FastAPI(
    title="Fall Detection API",
    description="AI-powered fall detection service using SmolVLM2",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Fall Detection API", 
        "version": "1.0.0",
        "status": "active"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check model status
        model_status = await model_service.health_check() if model_service else False
        
        # Check database status
        try:
            stats = await db_manager.get_statistics()
            db_status = True
        except:
            db_status = False
            stats = {}
        
        return {
            "status": "healthy" if (model_status and db_status) else "unhealthy",
            "model_loaded": model_status,
            "database_connected": db_status,
            "gpu_available": torch.cuda.is_available(),
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.post("/detect-fall/")
async def detect_fall_single(file: UploadFile = File(...)):
    """Tek görsel için düşme tespiti"""
    if not model_service or not getattr(model_service, "is_initialized", False):
        raise HTTPException(status_code=503, detail="Model loading, try again shortly")
    
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Read image bytes
        image_bytes = await file.read()
        image_hash = db_manager.calculate_image_hash(image_bytes)
        
        # Check if result already exists
        existing_result = await db_manager.check_existing_result(image_hash)
        if existing_result:
            logging.info(f"🔄 Cache hit for image hash: {image_hash[:8]}...")
            return existing_result
        
        # Process new image
        start_time = time.time()
        
        # Convert to PIL Image
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_size = f"{image.size[0]}x{image.size[1]}"
        
        # Run fall detection
        result = await model_service.detect_fall(image)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Save to database
        await db_manager.save_result(
            image_hash=image_hash,
            result=result["result"],
            confidence=result.get("confidence"),
            image_size=image_size,
            processing_time_ms=processing_time
        )
        
        response = {
            "image_hash": image_hash,
            "result": result["result"],
            "confidence": result.get("confidence"),
            "image_size": image_size,
            "processing_time_ms": processing_time,
            "cached": False
        }
        
        logging.info(f"✅ Processed image {image_hash[:8]}... -> {result['result']} ({processing_time}ms)")
        return response
        
    except Exception as e:
        logging.error(f"❌ Error processing image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.post("/detect-fall-batch/")
async def detect_fall_batch(files: List[UploadFile] = File(...)):
    """Birden fazla görsel için düşme tespiti"""
    if not model_service or not getattr(model_service, "is_initialized", False):
        raise HTTPException(status_code=503, detail="Model loading, try again shortly")
    
    if len(files) > 10:  # Limit batch size
        raise HTTPException(status_code=400, detail="Maximum 10 images per batch")
    
    results = []
    
    for file in files:
        if not file.content_type.startswith('image/'):
            results.append({
                "filename": file.filename,
                "error": "File must be an image"
            })
            continue
            
        try:
            # Read image bytes
            image_bytes = await file.read()
            image_hash = db_manager.calculate_image_hash(image_bytes)
            
            # Check cache first
            existing_result = await db_manager.check_existing_result(image_hash)
            if existing_result:
                existing_result["filename"] = file.filename
                results.append(existing_result)
                continue
            
            # Process new image
            start_time = time.time()
            
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            image_size = f"{image.size[0]}x{image.size[1]}"
            
            result = await model_service.detect_fall(image)
            processing_time = int((time.time() - start_time) * 1000)
            
            # Save to database
            await db_manager.save_result(
                image_hash=image_hash,
                result=result["result"],
                confidence=result.get("confidence"),
                image_size=image_size,
                processing_time_ms=processing_time
            )
            
            response = {
                "filename": file.filename,
                "image_hash": image_hash,
                "result": result["result"],
                "confidence": result.get("confidence"),
                "image_size": image_size,
                "processing_time_ms": processing_time,
                "cached": False
            }
            
            results.append(response)
            
        except Exception as e:
            results.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    return {"results": results}

@app.get("/result/{image_hash}")
async def get_result(image_hash: str):
    """Hash ile sonuç sorgulama"""
    result = await db_manager.check_existing_result(image_hash)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return result

@app.get("/statistics")
async def get_statistics():
    """Sistem istatistikleri"""
    try:
        stats = await db_manager.get_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    # Use uvloop for better async performance
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        access_log=True
    )
