from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.routers.health import router as health_router
from app.routers.inference import router as inference_router
from app.runtime_state import llama_runtime


@asynccontextmanager
async def lifespan(_: FastAPI):
    await llama_runtime.ensure_started()
    try:
        yield
    finally:
        await llama_runtime.stop()


app = FastAPI(
    title="Fall Detection AI Service",
    description="GGUF VLM fall detection via persistent llama-server (ggml-org/llama.cpp CPU derlemesi).",
    version="2.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(inference_router)
