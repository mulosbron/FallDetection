#!/usr/bin/env bash
set -euo pipefail

echo "[bootstrap] starting AI service bootstrap..."

MODEL_REPO="${MODEL_REPO:-ggml-org/SmolVLM2-500M-Video-Instruct-GGUF}"
MODEL_FILE="${MODEL_FILE:-SmolVLM2-500M-Video-Instruct-Q8_0.gguf}"
MMPROJ_FILE="${MMPROJ_FILE:-mmproj-SmolVLM2-500M-Video-Instruct-f16.gguf}"
MODEL_DIR="${MODEL_DIR:-/app/model}"
MODEL_PATH="${MODEL_PATH:-${MODEL_DIR}/${MODEL_FILE}}"
MMPROJ_PATH="${MMPROJ_PATH:-${MODEL_DIR}/${MMPROJ_FILE}}"
HF_TOKEN_FILE="${HF_TOKEN_FILE:-/run/secrets/hf_token.txt}"

DOWNLOAD_MAX_RETRIES="${DOWNLOAD_MAX_RETRIES:-5}"
DOWNLOAD_RETRY_DELAY_SECONDS="${DOWNLOAD_RETRY_DELAY_SECONDS:-5}"
DOWNLOAD_TIMEOUT_SECONDS="${DOWNLOAD_TIMEOUT_SECONDS:-120}"

if [[ ! -x "/usr/local/bin/llama-cli" ]]; then
  echo "[bootstrap] ERROR: /usr/local/bin/llama-cli not found or not executable"
  exit 1
fi

mkdir -p "${MODEL_DIR}"

# Priority: HF_TOKEN environment variable (docker compose / CI), otherwise HF_TOKEN_FILE.
EFFECTIVE_HF_TOKEN=""
if [[ -n "${HF_TOKEN:-}" ]]; then
  EFFECTIVE_HF_TOKEN="$(printf '%s' "${HF_TOKEN}" | tr -d '\r\n')"
elif [[ -f "${HF_TOKEN_FILE}" ]]; then
  EFFECTIVE_HF_TOKEN="$(tr -d '\r\n' < "${HF_TOKEN_FILE}")"
elif [[ -f "/run/secrets/hf_token" ]]; then
  # Backward compatibility for older secret filename.
  EFFECTIVE_HF_TOKEN="$(tr -d '\r\n' < /run/secrets/hf_token)"
else
  echo "[bootstrap] ERROR: Hugging Face token is required: HF_TOKEN or /run/secrets/hf_token.txt (alternative: /run/secrets/hf_token)"
  exit 1
fi
if [[ -z "${EFFECTIVE_HF_TOKEN}" ]]; then
  echo "[bootstrap] ERROR: HF token is empty"
  exit 1
fi

download_hf_file() {
  local dest="$1"
  local filename="$2"
  local endpoint="https://huggingface.co/${MODEL_REPO}/resolve/main/${filename}"
  if [[ -f "${dest}" ]]; then
    echo "[bootstrap] already exists: ${dest}"
    return 0
  fi
  echo "[bootstrap] downloading ${filename} from ${MODEL_REPO} ..."
  local tmp_file="${dest}.part"
  local i
  for ((i=1; i<=DOWNLOAD_MAX_RETRIES; i++)); do
    echo "[bootstrap] download attempt ${i}/${DOWNLOAD_MAX_RETRIES} (${filename})"
    if curl -fL --retry 2 --retry-delay 2 --connect-timeout 20 --max-time "${DOWNLOAD_TIMEOUT_SECONDS}" \
      -H "Authorization: Bearer ${EFFECTIVE_HF_TOKEN}" \
      "${endpoint}" \
      -o "${tmp_file}"; then
      mv "${tmp_file}" "${dest}"
      echo "[bootstrap] downloaded: ${dest}"
      return 0
    fi
    echo "[bootstrap] attempt ${i} failed for ${filename}"
    rm -f "${tmp_file}" || true
    sleep "${DOWNLOAD_RETRY_DELAY_SECONDS}"
  done
  echo "[bootstrap] ERROR: download failed for ${filename} after ${DOWNLOAD_MAX_RETRIES} attempts"
  exit 1
}

download_hf_file "${MODEL_PATH}" "${MODEL_FILE}"
download_hf_file "${MMPROJ_PATH}" "${MMPROJ_FILE}"

exec "$@"
