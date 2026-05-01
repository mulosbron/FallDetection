from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=(),
    )
    service_name: str = "ai-service"
    # API response label; override via MODEL_NAME for a specific deployment.
    model_name: str = "smolvlm2-500m-video-instruct-q8-f16mmproj"
    # "model" field in llama-server /v1/chat/completions body (.env: CHAT_COMPLETION_MODEL). Falls back to model_name if empty.
    chat_completion_model: str = ""
    # ggml-org/SmolVLM2-500M-Video-Instruct-GGUF - filenames follow SmolVLM2-500M-Video-Instruct-*.
    model_repo: str = "ggml-org/SmolVLM2-500M-Video-Instruct-GGUF"
    model_dir: str = "/app/model"
    model_file: str = "SmolVLM2-500M-Video-Instruct-Q8_0.gguf"
    model_path: str = "/app/model/SmolVLM2-500M-Video-Instruct-Q8_0.gguf"
    mmproj_file: str = "mmproj-SmolVLM2-500M-Video-Instruct-f16.gguf"
    mmproj_path: str = "/app/model/mmproj-SmolVLM2-500M-Video-Instruct-f16.gguf"
    hf_token_file: str = "/run/secrets/hf_token"
    llama_cli_path: str = "/usr/local/bin/llama-cli"
    llama_server_path: str = "/usr/local/bin/llama-server"
    llama_server_host: str = "127.0.0.1"
    llama_server_port: int = 8080
    llama_server_ready_timeout_seconds: int = 120
    llama_server_poll_interval_seconds: int = 2
    threads: int = 6
    ctx_size: int = 8192
    n_gpu_layers: int = 0
    max_tokens: int = 24
    temperature: float = 0.1
    inference_timeout_seconds: int = 300
    prefilter_enabled: bool = True
    prefilter_motion_min_area: int = 900
    prefilter_motion_warmup_frames: int = 20
    prefilter_motion_diff_threshold: int = 25
    prefilter_person_check_every_n_frames: int = 4
    prefilter_person_min_bbox_area: int = 2800
    prefilter_send_cooldown_ms: int = 3000
    download_max_retries: int = 5
    download_retry_delay_seconds: int = 5
    download_timeout_seconds: int = 120
    log_level: str = "INFO"

    def resolved_chat_completion_model(self) -> str:
        s = self.chat_completion_model.strip()
        return s if s else self.model_name
