# GGUF VLM Batch Image Test — **SmolVLM2-256M-Video-Instruct Q8 + mmproj FP16** (`smolvlm2-256m-video-q8-fp16_model_test`)

Service model: `ggml-org/SmolVLM2-256M-Video-Instruct-GGUF` (`SmolVLM2-256M-Video-Instruct-Q8_0.gguf`) + `mmproj-SmolVLM2-256M-Video-Instruct-f16.gguf`.

This folder uses **`test_image.py`** and **`metrics.py`** as entry points. Logs and generated outputs include **ANALYSIS RESULTS**, `fall_detection_results.csv`, `results/<timestamp>/evaluation_report.txt`, and `metrics_summary.json`.

## Labels

- `0` = falling person (`tests/dataset/falling_0/`)
- `1` = random image (`tests/dataset/falling_1/`)
- API mapping: `fall_detected` → `0`, `no_fall` → `1` (`Yes`/`No` is normalized as well)

## Prerequisite

Use the running endpoint `POST /v1/inference/fall-detection` (multipart `file`) with mmproj loaded. Run commands from the **`ai-service` root**.

## Run

Docker example port: `8200`

```bash
cd ai-service
python tests/smolvlm2-256m-video-q8-fp16_model_test/test_image.py \
  --falling-0-dir "tests/dataset/falling_0" \
  --falling-1-dir "tests/dataset/falling_1" \
  --endpoint "http://localhost:8200/v1/inference/fall-detection"
```

Default `--falling-*-dir` already points to `tests/dataset/`, so endpoint-only run is enough in most cases:

```bash
python tests/smolvlm2-256m-video-q8-fp16_model_test/test_image.py \
  --endpoint "http://localhost:8200/v1/inference/fall-detection"
```

## Quick subset

```bash
python tests/smolvlm2-256m-video-q8-fp16_model_test/test_image.py \
  --endpoint "http://localhost:8200/v1/inference/fall-detection" \
  --max-per-class 20
```

## Outputs (`tests/smolvlm2-256m-video-q8-fp16_model_test/results/<timestamp>/`)

| File | Description |
|-------|-------------|
| `evaluation_report.txt` | Confusion matrix, FP/FN, metrics, textual interpretation |
| `fall_detection_results.csv` | `Image`, `True Label`, `Predicted Label`, `Predicted Text` |
| `prediction_details.csv` | `raw_output`, latency, status |
| `metrics_summary.json` | Summary |

Logs: `tests/smolvlm2-256m-video-q8-fp16_model_test/logs/`

## Accuracy around ~50%

In a balanced dataset, if the model always predicts `no_fall` (label `1`), accuracy can look close to random chance; this does not indicate a good model. Inspect FN/FP and recall.

## Working Directory Note

Running the test from inside this folder with incorrect relative paths can generate junk paths such as `tests/smolvlm2-256m-video-q8-fp16_model_test/tests/...`. Always run from `ai-service` root as shown above; `.gitignore` excludes this accidental subtree.

## Compare with F16 (Video)

See `tests/smolvlm2-256m-video-f16-same_model_test/` and root `docker-compose.model.smolvlm2-256m-video-f16.yml`.
