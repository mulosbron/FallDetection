from fastapi import APIRouter
import os

from app.runtime_state import settings, llama_runtime, pipeline
from app.models.weights_info import get_model_weights_info

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    server_exists = llama_runtime.server_binary_exists()
    model_exists = os.path.exists(settings.model_path)
    mmproj_exists = os.path.exists(settings.mmproj_path)
    ready = False
    try:
        ready = await llama_runtime._is_ready()
    except Exception:
        ready = False
    token_exists = os.path.exists(settings.hf_token_file)
    download_ready = token_exists and model_exists and mmproj_exists
    model_info = get_model_weights_info(settings.model_path)

    return {
        "status": "healthy"
        if server_exists and model_exists and mmproj_exists and ready
        else "degraded",
        "service": settings.service_name,
        "model": settings.model_name,
        "runtime": "llama-server-persistent",
        "model_repo": settings.model_repo,
        "llama_server_path": settings.llama_server_path,
        "llama_server_exists": server_exists,
        "llama_server_url": llama_runtime.base_url,
        "llama_server_ready": ready,
        "model_path": settings.model_path,
        "model_exists": model_exists,
        "mmproj_path": settings.mmproj_path,
        "mmproj_exists": mmproj_exists,
        "model_size_bytes": model_info.size_bytes,
        "hf_token_file": settings.hf_token_file,
        "hf_token_available": token_exists,
        "download_ready": download_ready,
        "download_retry_policy": {
            "max_retries": settings.download_max_retries,
            "retry_delay_seconds": settings.download_retry_delay_seconds,
            "timeout_seconds": settings.download_timeout_seconds,
        },
        "prefilter": {
            "settings": {
                "enabled": settings.prefilter_enabled,
                "motion_min_area": settings.prefilter_motion_min_area,
                "motion_warmup_frames": settings.prefilter_motion_warmup_frames,
                "motion_diff_threshold": settings.prefilter_motion_diff_threshold,
                "person_check_every_n_frames": settings.prefilter_person_check_every_n_frames,
                "person_min_bbox_area": settings.prefilter_person_min_bbox_area,
                "send_cooldown_ms": settings.prefilter_send_cooldown_ms,
            },
            "stats": pipeline.get_prefilter_summary(),
        },
    }
