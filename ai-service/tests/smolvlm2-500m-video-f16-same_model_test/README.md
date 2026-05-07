# GGUF VLM Batch Image Test — **SmolVLM2-500M-Video-Instruct F16 + matching mmproj** (`smolvlm2-500m-video-f16-same_model_test`)

This follows the same flow as the Q8 harness: `test_image.py` + `metrics.py`. Outputs are written under `logs/` and `results/<timestamp>/`.

## Model Files

From Hugging Face `ggml-org/SmolVLM2-500M-Video-Instruct-GGUF`, use:

- `SmolVLM2-500M-Video-Instruct-f16.gguf`
- `mmproj-SmolVLM2-500M-Video-Instruct-f16.gguf`

Place both files in `ai-service/models/` (`./models` on host maps to `/app/model` in container).

## Start Service (F16)

```bash
cd ai-service
docker compose -f docker-compose.yml -f docker-compose.model.smolvlm2-500m-video-f16.yml up -d --build
```

## Run

```bash
python tests/smolvlm2-500m-video-f16-same_model_test/test_image.py \
  --endpoint "http://localhost:8200/v1/inference/fall-detection"
```

Quick subset:

```bash
python tests/smolvlm2-500m-video-f16-same_model_test/test_image.py \
  --endpoint "http://localhost:8200/v1/inference/fall-detection" \
  --max-per-class 20
```

