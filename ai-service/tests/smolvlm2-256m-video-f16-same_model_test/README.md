# GGUF VLM Batch Image Test — **SmolVLM2-256M-Video-Instruct F16 + matching mmproj** (`smolvlm2-256m-video-f16-same_model_test`)

This follows the same flow as the Q8 harness: `test_image.py` + `metrics.py`. Outputs are written under this folder's `logs/` and `results/<timestamp>/`.

## F16 Service

From Hugging Face `ggml-org/SmolVLM2-256M-Video-Instruct-GGUF`, use:

- `SmolVLM2-256M-Video-Instruct-f16.gguf`
- `mmproj-SmolVLM2-256M-Video-Instruct-f16.gguf`

Place these in `ai-service/models/` (`./models` in compose maps to `/app/model` in container). Start the container with F16 settings:

```bash
cd ai-service
docker compose -f docker-compose.yml -f docker-compose.model.smolvlm2-256m-video-f16.yml up -d --build
```

The base `docker-compose.yml` keeps Video Q8 paths. `docker-compose.model.smolvlm2-256m-video-f16.yml` overrides model/mmproj filenames and `MODEL_NAME`.

## Dataset

Default dataset paths are `tests/dataset/falling_0` and `tests/dataset/falling_1` (same as Q8 harness). You can override with `--falling-0-dir` / `--falling-1-dir`.

## Run

From `ai-service` root (example port 8200):

```bash
python tests/smolvlm2-256m-video-f16-same_model_test/test_image.py \
  --endpoint "http://localhost:8200/v1/inference/fall-detection"
```

Quick subset:

```bash
python tests/smolvlm2-256m-video-f16-same_model_test/test_image.py \
  --endpoint "http://localhost:8200/v1/inference/fall-detection" \
  --max-per-class 20
```

## Compare with Q8

1. First run the full Q8 (same mmproj) evaluation: `tests/smolvlm2-256m-video-q8-same_model_test/`.
2. Restart service with F16 (`docker-compose.model.smolvlm2-256m-video-f16.yml`).
3. Run this script against the same endpoint and compare both `results/*/metrics_summary.json` files.

## Labels

- `0` = falling (`falling_0`)
- `1` = random (`falling_1`)
- API mapping: `fall_detected` → `0`, `no_fall` → `1`

Accuracy alone can be misleading; focus on fall-class recall / F1 and FN count (same warning as `tests/smolvlm2-256m-video-q8-same_model_test/README.md`).
