from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.runtime_state import pipeline

router = APIRouter(prefix="/v1/inference")


@router.post("/fall-detection")
async def run_inference(
    file: UploadFile = File(..., description="Image file (jpeg/png/webp etc.)"),
    cameraId: str | None = Form(
        default=None,
        description="Camera identifier (used for prefilter state).",
    ),
    camera_index: str | None = Form(
        default=None,
        description="Alternative camera identifier field for legacy client compatibility.",
    ),
    prompt: str | None = Form(
        default=None,
        description="Optional additional instruction text (default fall question is used).",
    ),
) -> dict:
    content_type = (file.content_type or "").strip().lower()
    if content_type in ("", "application/octet-stream", "binary/octet-stream"):
        name = (file.filename or "").lower()
        if name.endswith((".jpg", ".jpeg")):
            content_type = "image/jpeg"
        elif name.endswith(".png"):
            content_type = "image/png"
        elif name.endswith(".webp"):
            content_type = "image/webp"
        elif name.endswith(".bmp"):
            content_type = "image/bmp"
        elif name.endswith((".tif", ".tiff")):
            content_type = "image/tiff"
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="file must be an image (Content-Type image/* or known image extension)",
        )
    try:
        data = await file.read()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"read failed: {exc}") from exc
    if not data:
        raise HTTPException(status_code=400, detail="empty file")
    camera_id = (cameraId or camera_index or "").strip() or None
    try:
        return await pipeline.infer_fall(data, content_type, prompt, camera_id=camera_id)
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
