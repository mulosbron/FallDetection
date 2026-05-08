#!/usr/bin/env bash
set -euo pipefail

endpoint="http://localhost:8200/v1/inference/fall-detection"
wait_seconds=180
sample_per_class=50
continue_on_error=0

usage() {
  cat <<'EOF'
Usage: ./scripts/run-model-benchmark-sequence.sh [options]

Options:
  --endpoint <url>           Inference endpoint (default: http://localhost:8200/v1/inference/fall-detection)
  --wait-seconds <seconds>   Health wait timeout (default: 180)
  --sample-per-class <n>     Random sample size per class (default: 50)
  --continue-on-error        Continue with next model if a step fails
  -h, --help                 Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --endpoint)
      endpoint="${2:-}"; shift 2 ;;
    --wait-seconds)
      wait_seconds="${2:-}"; shift 2 ;;
    --sample-per-class)
      sample_per_class="${2:-}"; shift 2 ;;
    --continue-on-error)
      continue_on_error=1; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 2
      ;;
  esac
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/.." && pwd)"

env_file="${repo_root}/.env"
if [[ ! -f "${env_file}" ]]; then
  echo ".env not found: ${env_file}" >&2
  exit 1
fi

if ! [[ "${sample_per_class}" =~ ^[0-9]+$ ]] || [[ "${sample_per_class}" -le 0 ]]; then
  echo "SamplePerClass must be greater than 0." >&2
  exit 1
fi

require_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "Missing required command: ${cmd}" >&2
    exit 1
  fi
}

require_cmd docker
require_cmd shuf
require_cmd sed
require_cmd awk
require_cmd find
require_cmd mkdir
require_cmd cp

python_cmd="python"
if ! command -v "${python_cmd}" >/dev/null 2>&1; then
  python_cmd="python3"
fi
require_cmd "${python_cmd}"

prepare_permissions() {
  local models_dir="${repo_root}/models"
  local secrets_dir="${repo_root}/secrets"
  local app_dir="${repo_root}/app"
  local hf_token_path="${secrets_dir}/hf_token.txt"

  mkdir -p "${models_dir}" "${secrets_dir}"

  # Linux bind mount izni: container'i host UID/GID ile calistir.
  export LOCAL_UID="${LOCAL_UID:-$(id -u)}"
  export LOCAL_GID="${LOCAL_GID:-$(id -g)}"

  # Build context + container user (LOCAL_UID) uyumu: 0700 kaynak dizinler imajda da
  # kalir ve 'user:' ile calisirken Permission denied uretir. Traversal + okuma ac.
  if [[ -d "${app_dir}" ]]; then
    chmod -R u=rwX,go=rX "${app_dir}" 2>/dev/null || true
  fi
  if [[ -d "${repo_root}/scripts" ]]; then
    chmod -R u=rwX,go=rX "${repo_root}/scripts" 2>/dev/null || true
  fi
  if [[ -d "${repo_root}/tests" ]]; then
    chmod -R u=rwX,go=rX "${repo_root}/tests" 2>/dev/null || true
  fi

  # models yazilabilir olmali; benchmark indirmeleri burada yapiliyor.
  chmod -R u=rwX,go=rwX "${models_dir}" 2>/dev/null || true

  # Secret klasoru traverse/read edilebilir olmali.
  chmod 755 "${secrets_dir}" 2>/dev/null || true
  if [[ -f "${hf_token_path}" ]]; then
    chmod 644 "${hf_token_path}" 2>/dev/null || true
  fi

  echo "Permission prep done (LOCAL_UID=${LOCAL_UID}, LOCAL_GID=${LOCAL_GID})."
}

set_env_value() {
  local file="$1"
  local key="$2"
  local value="$3"

  # Replace key=... if present; otherwise append key=value.
  if grep -qE "^[[:space:]]*${key}[[:space:]]*=" "${file}"; then
    sed -i -E "s|^[[:space:]]*${key}[[:space:]]*=.*$|${key}=${value}|" "${file}"
  else
    printf '%s=%s\n' "${key}" "${value}" >> "${file}"
  fi
}

wait_for_ai_service_health() {
  local timeout_seconds="$1"
  local health_url="http://localhost:8200/health"
  local poll_interval_seconds=2
  local started_at
  started_at="$(date +%s)"
  local deadline=$((started_at + timeout_seconds))

  echo "Waiting for AI service health (timeout: ${timeout_seconds} sec)..."

  while [[ "$(date +%s)" -lt "${deadline}" ]]; do
    if command -v curl >/dev/null 2>&1; then
      if curl -fsS --max-time 5 "${health_url}" >/dev/null 2>&1; then
        local now; now="$(date +%s)"
        local elapsed; elapsed="$(awk "BEGIN { printf \"%.1f\", ${now}-${started_at} }")"
        echo "Health OK received (${elapsed} sec). Proceeding to test."
        return 0
      fi
    else
      # Fallback to wget if curl is unavailable.
      if command -v wget >/dev/null 2>&1 && wget -q -T 5 -O /dev/null "${health_url}" >/dev/null 2>&1; then
        local now; now="$(date +%s)"
        local elapsed; elapsed="$(awk "BEGIN { printf \"%.1f\", ${now}-${started_at} }")"
        echo "Health OK received (${elapsed} sec). Proceeding to test."
        return 0
      fi
    fi
    sleep "${poll_interval_seconds}"
  done

  echo "AI service health timeout: 200 OK was not received within ${timeout_seconds} sec (${health_url})." >&2
  return 1
}

invoke_step() {
  local model_name="$1"
  local model_repo="$2"
  local model_file="$3"
  local mmproj_file="$4"
  local test_script="$5"
  local falling0_dir="$6"
  local falling1_dir="$7"

  echo ""
  echo "============================================================"
  echo "Model: ${model_name}"
  echo "Test : ${test_script}"
  echo "============================================================"

  set_env_value "${env_file}" "MODEL_NAME" "${model_name}"
  set_env_value "${env_file}" "MODEL_REPO" "${model_repo}"
  set_env_value "${env_file}" "MODEL_DIR" "/app/model"
  set_env_value "${env_file}" "MODEL_FILE" "${model_file}"
  set_env_value "${env_file}" "MODEL_PATH" "/app/model/${model_file}"
  set_env_value "${env_file}" "MMPROJ_FILE" "${mmproj_file}"
  set_env_value "${env_file}" "MMPROJ_PATH" "/app/model/${mmproj_file}"

  echo ".env updated."

  (
    cd -- "${repo_root}"
    echo "docker compose down"
    docker compose down

    echo "docker compose up -d --build"
    docker compose up -d --build

    wait_for_ai_service_health "${wait_seconds}"

    echo "Starting Python test..."
    "${python_cmd}" "${test_script}" \
      --endpoint "${endpoint}" \
      --falling-0-dir "${falling0_dir}" \
      --falling-1-dir "${falling1_dir}"
  )
}

dataset_root="${repo_root}/tests/dataset"
falling0_source="${dataset_root}/falling_0"
falling1_source="${dataset_root}/falling_1"

if [[ ! -d "${falling0_source}" ]]; then
  echo "Dataset not found: ${falling0_source}" >&2
  exit 1
fi
if [[ ! -d "${falling1_source}" ]]; then
  echo "Dataset not found: ${falling1_source}" >&2
  exit 1
fi

prepare_permissions

mapfile -t falling0_files < <(find "${falling0_source}" -maxdepth 1 -type f \( \
  -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.webp' -o -iname '*.bmp' -o -iname '*.tiff' \
  \) -print)
mapfile -t falling1_files < <(find "${falling1_source}" -maxdepth 1 -type f \( \
  -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.webp' -o -iname '*.bmp' -o -iname '*.tiff' \
  \) -print)

if [[ "${#falling0_files[@]}" -lt "${sample_per_class}" ]]; then
  echo "Not enough files for falling_0. Required=${sample_per_class}, available=${#falling0_files[@]}" >&2
  exit 1
fi
if [[ "${#falling1_files[@]}" -lt "${sample_per_class}" ]]; then
  echo "Not enough files for falling_1. Required=${sample_per_class}, available=${#falling1_files[@]}" >&2
  exit 1
fi

sample_root="${dataset_root}/_benchmark_random_sample"
sample0_dir="${sample_root}/falling_0"
sample1_dir="${sample_root}/falling_1"

rm -rf -- "${sample_root}"
mkdir -p -- "${sample0_dir}" "${sample1_dir}"

mapfile -t selected0 < <(printf '%s\n' "${falling0_files[@]}" | shuf -n "${sample_per_class}")
mapfile -t selected1 < <(printf '%s\n' "${falling1_files[@]}" | shuf -n "${sample_per_class}")

for f in "${selected0[@]}"; do
  cp -f -- "${f}" "${sample0_dir}/"
done
for f in "${selected1[@]}"; do
  cp -f -- "${f}" "${sample1_dir}/"
done

echo "Random sample created: class0=${#selected0[@]}, class1=${#selected1[@]}, total=$(( ${#selected0[@]} + ${#selected1[@]} ))"
echo "Sample folder: ${sample_root}"

# Model sequence (mirrors the PowerShell script)
models=(
  "smolvlm2-256m-video-instruct-q8|ggml-org/SmolVLM2-256M-Video-Instruct-GGUF|SmolVLM2-256M-Video-Instruct-Q8_0.gguf|mmproj-SmolVLM2-256M-Video-Instruct-Q8_0.gguf|tests/smolvlm2-256m-video-q8-same_model_test/test_image.py"
  "smolvlm2-256m-video-instruct-q8|ggml-org/SmolVLM2-256M-Video-Instruct-GGUF|SmolVLM2-256M-Video-Instruct-Q8_0.gguf|mmproj-SmolVLM2-256M-Video-Instruct-f16.gguf|tests/smolvlm2-256m-video-q8-fp16_model_test/test_image.py"
  "smolvlm2-256m-video-instruct-f16|ggml-org/SmolVLM2-256M-Video-Instruct-GGUF|SmolVLM2-256M-Video-Instruct-f16.gguf|mmproj-SmolVLM2-256M-Video-Instruct-f16.gguf|tests/smolvlm2-256m-video-f16-same_model_test/test_image.py"
  "smolvlm2-500m-video-instruct-q8|ggml-org/SmolVLM2-500M-Video-Instruct-GGUF|SmolVLM2-500M-Video-Instruct-Q8_0.gguf|mmproj-SmolVLM2-500M-Video-Instruct-Q8_0.gguf|tests/smolvlm2-500m-video-q8-same_model_test/test_image.py"
  "smolvlm2-500m-video-instruct-q8|ggml-org/SmolVLM2-500M-Video-Instruct-GGUF|SmolVLM2-500M-Video-Instruct-Q8_0.gguf|mmproj-SmolVLM2-500M-Video-Instruct-f16.gguf|tests/smolvlm2-500m-video-q8-fp16_model_test/test_image.py"
  "smolvlm2-500m-video-instruct-f16|ggml-org/SmolVLM2-500M-Video-Instruct-GGUF|SmolVLM2-500M-Video-Instruct-f16.gguf|mmproj-SmolVLM2-500M-Video-Instruct-f16.gguf|tests/smolvlm2-500m-video-f16-same_model_test/test_image.py"
)

overall_rc=0
for m in "${models[@]}"; do
  IFS='|' read -r model_name model_repo model_file mmproj_file test_script <<< "${m}"

  if invoke_step "${model_name}" "${model_repo}" "${model_file}" "${mmproj_file}" "${test_script}" "${sample0_dir}" "${sample1_dir}"; then
    :
  else
    rc=$?
    echo "Step failed for model '${model_name}' (exit=${rc})." >&2
    overall_rc="${rc}"
    if [[ "${continue_on_error}" -eq 0 ]]; then
      exit "${rc}"
    fi
  fi
done

echo ""
echo "All model runs completed."
exit "${overall_rc}"
