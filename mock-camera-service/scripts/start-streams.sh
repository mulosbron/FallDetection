#!/bin/sh
set -eu

VIDEO_FOLDER="${VIDEO_FOLDER:-/videos}"
RTSP_HOST="${RTSP_HOST:-rtsp_server}"
RTSP_PORT="${RTSP_PORT:-8554}"
RTSP_PATH_PREFIX="${RTSP_PATH_PREFIX:-/live}"
VIDEO_BITRATE="${VIDEO_BITRATE:-2M}"
VIDEO_MAXRATE="${VIDEO_MAXRATE:-2M}"
VIDEO_BUFSIZE="${VIDEO_BUFSIZE:-1M}"
VIDEO_PRESET="${VIDEO_PRESET:-ultrafast}"
INJECTOR_LOG_LEVEL="${INJECTOR_LOG_LEVEL:-warning}"

log() {
  printf '[injector] %s\n' "$1"
}

wait_for_rtsp_server() {
  log "Waiting for RTSP server: ${RTSP_HOST}:${RTSP_PORT}"
  while ! nc -z "${RTSP_HOST}" "${RTSP_PORT}" >/dev/null 2>&1; do
    sleep 2
  done
  log "RTSP server is reachable."
}

stream_loop() {
  input_file="$1"
  stream_path="$2"

  while true; do
    log "Starting stream: ${input_file} -> ${stream_path}"
    ffmpeg -loglevel "${INJECTOR_LOG_LEVEL}" \
      -re \
      -stream_loop -1 \
      -i "${input_file}" \
      -c:v libx264 \
      -preset "${VIDEO_PRESET}" \
      -tune zerolatency \
      -b:v "${VIDEO_BITRATE}" \
      -maxrate "${VIDEO_MAXRATE}" \
      -bufsize "${VIDEO_BUFSIZE}" \
      -rtsp_transport tcp \
      -f rtsp "rtsp://${RTSP_HOST}:${RTSP_PORT}${stream_path}" || true

    log "Stream dropped, retrying in 2s: ${stream_path}"
    sleep 2
  done
}

wait_for_rtsp_server

camera_index=1
started_count=0

for video_file in "${VIDEO_FOLDER}"/*; do
  if [ ! -f "${video_file}" ]; then
    continue
  fi

  case "${video_file}" in
    *.mp4|*.MP4|*.avi|*.AVI|*.mov|*.MOV|*.mkv|*.MKV|*.webm|*.WEBM)
      stream_path="${RTSP_PATH_PREFIX}/camera${camera_index}"
      stream_loop "${video_file}" "${stream_path}" &
      started_count=$((started_count + 1))
      camera_index=$((camera_index + 1))
      ;;
    *)
      ;;
  esac
done

if [ "${started_count}" -eq 0 ]; then
  log "No supported video found: ${VIDEO_FOLDER}"
  exit 1
fi

log "Started ${started_count} streams in total."
wait
