#!/bin/sh
set -eu

HLS_BASE_URL="${HLS_BASE_URL:-http://rtsp_server:8888}"
HLS_PATH_PREFIX="${HLS_PATH_PREFIX:-/live}"
FRAME_POST_URL_BASE="${FRAME_POST_URL_BASE:-http://fall_detection_backend:8080/api/frames/raw}"
BACKEND_HEALTH_URL="${BACKEND_HEALTH_URL:-http://fall_detection_backend:8080/api/health}"
# 30 FPS => ~0.033s between consecutive frame posts per camera
FRAME_INTERVAL_SECONDS="${FRAME_INTERVAL_SECONDS:-0.033}"
VIDEO_FOLDER="${VIDEO_FOLDER:-/videos}"

log() {
  printf '[publisher] %s\n' "$1"
}

ensure_curl() {
  if command -v curl >/dev/null 2>&1; then
    return
  fi

  log "Installing curl..."
  apk add --no-cache curl >/dev/null
}

wait_for_url() {
  url="$1"
  log "Waiting for: ${url}"
  while ! wget -q -O /dev/null "$url"; do
    sleep 2
  done
  log "Ready: ${url}"
}

post_camera_loop() {
  camera_index="$1"
  playlist_url="${HLS_BASE_URL}${HLS_PATH_PREFIX}/camera${camera_index}/stream.m3u8"
  post_url="${FRAME_POST_URL_BASE}?cameraId=${camera_index}"
  tmp_file="/tmp/camera_${camera_index}.jpg"

  while true; do
    ffmpeg -hide_banner -loglevel error -y \
      -i "${playlist_url}" \
      -frames:v 1 \
      -q:v 2 \
      "${tmp_file}" || true

    if [ -s "${tmp_file}" ]; then
      curl -fsS -X POST \
        -H "Content-Type: image/jpeg" \
        --data-binary "@${tmp_file}" \
        "${post_url}" >/dev/null || true
    fi

    sleep "${FRAME_INTERVAL_SECONDS}"
  done
}

camera_count=0
for video_file in "${VIDEO_FOLDER}"/*; do
  if [ -f "${video_file}" ]; then
    case "${video_file}" in
      *.mp4|*.MP4|*.avi|*.AVI|*.mov|*.MOV|*.mkv|*.MKV|*.webm|*.WEBM)
        camera_count=$((camera_count + 1))
        ;;
      *)
        ;;
    esac
  fi
done

if [ "${camera_count}" -eq 0 ]; then
  log "No video found: ${VIDEO_FOLDER}"
  exit 1
fi

ensure_curl
wait_for_url "${HLS_BASE_URL}${HLS_PATH_PREFIX}/camera1/index.m3u8"
wait_for_url "${BACKEND_HEALTH_URL}"

camera_index=1
while [ "${camera_index}" -le "${camera_count}" ]; do
  post_camera_loop "${camera_index}" &
  camera_index=$((camera_index + 1))
done

log "Automatic frame publishing started for ${camera_count} cameras in total."
wait
