from app.config import Settings
from app.inference.pipeline import InferencePipeline
from app.quantization.llama_server_runtime import LlamaServerRuntime

settings = Settings()
llama_runtime = LlamaServerRuntime(
    llama_server_path=settings.llama_server_path,
    model_path=settings.model_path,
    mmproj_path=settings.mmproj_path,
    host=settings.llama_server_host,
    port=settings.llama_server_port,
    threads=settings.threads,
    ctx_size=settings.ctx_size,
    n_gpu_layers=settings.n_gpu_layers,
    max_tokens=settings.max_tokens,
    temperature=settings.temperature,
    timeout_seconds=settings.inference_timeout_seconds,
    ready_timeout_seconds=settings.llama_server_ready_timeout_seconds,
    poll_interval_seconds=settings.llama_server_poll_interval_seconds,
    chat_completion_model=settings.resolved_chat_completion_model(),
)
pipeline = InferencePipeline(settings=settings, runtime=llama_runtime)
