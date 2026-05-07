# GGUF VLM Batch Image Test — **SmolVLM2-500M-Video-Instruct Q8 + matching mmproj** (`smolvlm2-500m-video-q8-same_model_test`)

This folder uses **`test_image.py`** and **`metrics.py`** as the only entry points. Outputs are written under `logs/` and `results/<timestamp>/`.

## Prerequisite

Use the running API endpoint `POST /v1/inference/fall-detection` (multipart `file`) with the correct mmproj loaded. Run commands from the **`ai-service` root**.

## Model Files

From Hugging Face `ggml-org/SmolVLM2-500M-Video-Instruct-GGUF`, use:

- `SmolVLM2-500M-Video-Instruct-Q8_0.gguf`
- `mmproj-SmolVLM2-500M-Video-Instruct-Q8_0.gguf`

Place both files in `ai-service/models/` (`./models` on host maps to `/app/model` in container).

## Start Service (Q8)

```bash
cd ai-service
docker compose -f docker-compose.yml -f docker-compose.model.smolvlm2-500m-video-q8.yml up -d --build
```

## Run

```bash
python tests/smolvlm2-500m-video-q8-same_model_test/test_image.py \
  --endpoint "http://localhost:8200/v1/inference/fall-detection"
```

Quick subset:

```bash
python tests/smolvlm2-500m-video-q8-same_model_test/test_image.py \
  --endpoint "http://localhost:8200/v1/inference/fall-detection" \
  --max-per-class 20
```

