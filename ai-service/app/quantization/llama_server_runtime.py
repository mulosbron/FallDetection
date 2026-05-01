from __future__ import annotations

"""
llama-server (OpenAI-compatible HTTP API) client.

Binary is compatible with ggml-org/llama.cpp `llama-server`:
- Server: tools/server (llama-server)
- Endpoint: POST /v1/chat/completions (and for multimodal mode: -m + --mmproj)
- Image: official multimodal / OpenAI image_url payload
  https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md
"""

import asyncio
import base64
import contextlib
import os
import shutil
import time
from dataclasses import dataclass
from typing import Any

import requests

@dataclass
class LlamaServerResult:
    text: str
    latency_ms: int


class LlamaServerRuntime:
    def __init__(
        self,
        llama_server_path: str,
        model_path: str,
        mmproj_path: str | None,
        host: str,
        port: int,
        threads: int,
        ctx_size: int,
        n_gpu_layers: int,
        max_tokens: int,
        temperature: float,
        timeout_seconds: int,
        ready_timeout_seconds: int,
        poll_interval_seconds: int,
        chat_completion_model: str,
    ):
        self.llama_server_path = llama_server_path
        self.model_path = model_path
        self.mmproj_path = mmproj_path
        self.host = host
        self.port = port
        self.threads = threads
        self.ctx_size = ctx_size
        self.n_gpu_layers = n_gpu_layers
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self.ready_timeout_seconds = ready_timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.chat_completion_model = chat_completion_model.strip()
        self.process: asyncio.subprocess.Process | None = None
        self._lock = asyncio.Lock()

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def server_binary_exists(self) -> bool:
        return shutil.which(self.llama_server_path) is not None

    def build_command(self) -> list[str]:
        cmd = [
            self.llama_server_path,
            "-m",
            self.model_path,
            "--host",
            "0.0.0.0",
            "--port",
            str(self.port),
            "--threads",
            str(self.threads),
            "--ctx-size",
            str(self.ctx_size),
            "--n-gpu-layers",
            str(self.n_gpu_layers),
            "--temp",
            str(self.temperature),
            "--n-predict",
            str(self.max_tokens),
            "--parallel",
            "1",
            "--no-webui",
        ]
        if self.mmproj_path and os.path.isfile(self.mmproj_path):
            cmd.extend(["--mmproj", self.mmproj_path])
            # SmolVLM: Jinja template causes tokenization failures (#17871); --no-jinja is the safe path
            cmd.append("--no-jinja")
            # docs/multimodal.md: for CPU-only / no-VRAM setups, keep projector off GPU
            if self.n_gpu_layers <= 0:
                cmd.append("--no-mmproj-offload")
        return cmd

    def _chat_completions_body(self, extra: dict[str, Any]) -> dict[str, Any]:
        body: dict[str, Any] = {
            "stream": False,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.chat_completion_model:
            body["model"] = self.chat_completion_model
        body.update(extra)
        return body

    def _post_v1_chat_completions(self, body: dict[str, Any]) -> dict[str, Any]:
        res = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json=body,
            timeout=self.timeout_seconds,
        )
        if not res.ok:
            detail = (res.text or "")[:4000]
            raise RuntimeError(f"llama-server HTTP {res.status_code}: {detail or res.reason}")
        return res.json()

    async def _is_ready(self) -> bool:
        def ping() -> bool:
            try:
                res = requests.get(f"{self.base_url}/health", timeout=3)
                return res.status_code == 200
            except Exception:
                return False

        return await asyncio.to_thread(ping)

    async def ensure_started(self) -> None:
        async with self._lock:
            if self.process and self.process.returncode is None:
                return
            command = self.build_command()
            self.process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            deadline = time.monotonic() + self.ready_timeout_seconds
            while time.monotonic() < deadline:
                if self.process.returncode is not None:
                    stderr_text = ""
                    if self.process.stderr:
                        stderr_text = (await self.process.stderr.read()).decode("utf-8", errors="ignore").strip()
                    stdout_text = ""
                    if self.process.stdout:
                        stdout_text = (await self.process.stdout.read()).decode("utf-8", errors="ignore").strip()
                    details = stderr_text or stdout_text or "no startup logs captured"
                    raise RuntimeError(f"llama-server exited unexpectedly during startup: {details[:600]}")
                if await self._is_ready():
                    return
                await asyncio.sleep(self.poll_interval_seconds)
            raise TimeoutError(f"llama-server not ready in {self.ready_timeout_seconds}s")

    async def stop(self) -> None:
        async with self._lock:
            if not self.process or self.process.returncode is not None:
                return
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=10)
            except TimeoutError:
                self.process.kill()
                await self.process.wait()
            finally:
                self.process = None

    async def infer(self, prompt: str) -> LlamaServerResult:
        await self.ensure_started()

        body = self._chat_completions_body(
            {
                "messages": [
                    {"role": "system", "content": "You are a strict binary classifier. Reply with only fall_detected or no_fall."},
                    {"role": "user", "content": prompt},
                ],
            }
        )

        start = time.perf_counter()
        data = await asyncio.to_thread(self._post_v1_chat_completions, body)
        latency_ms = int((time.perf_counter() - start) * 1000)

        content = ""
        choices = data.get("choices", [])
        if choices:
            msg = choices[0].get("message", {}) or {}
            content = str(msg.get("content", "") or "").strip()
            if not content:
                content = str(msg.get("reasoning_content", "") or "").strip()
        if not content:
            with contextlib.suppress(Exception):
                content = str(data["choices"][0]["text"]).strip()
        return LlamaServerResult(text=content, latency_ms=latency_ms)

    async def infer_vision(
        self,
        image_bytes: bytes,
        mime_type: str,
        user_text: str,
        prepend_classifier_instruction: bool = True,
    ) -> LlamaServerResult:
        await self.ensure_started()
        if not self.mmproj_path or not os.path.isfile(self.mmproj_path):
            raise RuntimeError(
                "Vision requires a mmproj GGUF (set MMPROJ_PATH / place mmproj next to main weights in MODEL_DIR)."
            )
        b64 = base64.standard_b64encode(image_bytes).decode("ascii")
        safe_mime = mime_type.split(";")[0].strip() or "image/jpeg"
        data_uri = f"data:{safe_mime};base64,{b64}"
        # SmolVLM template expects content[0] to be image (text-first can trigger "Failed to tokenize prompt").
        vision_user_text = user_text
        if prepend_classifier_instruction:
            vision_user_text = (
                "You are a strict binary fall detector. Reply with exactly one token: fall_detected or no_fall.\n\n"
                + user_text
            )
        body = self._chat_completions_body(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": data_uri}},
                            {"type": "text", "text": vision_user_text},
                        ],
                    },
                ],
            }
        )

        start = time.perf_counter()
        data = await asyncio.to_thread(self._post_v1_chat_completions, body)
        latency_ms = int((time.perf_counter() - start) * 1000)

        content = ""
        choices = data.get("choices", [])
        if choices:
            msg = choices[0].get("message", {}) or {}
            content = str(msg.get("content", "") or "").strip()
            if not content:
                content = str(msg.get("reasoning_content", "") or "").strip()
        if not content:
            with contextlib.suppress(Exception):
                content = str(data["choices"][0]["text"]).strip()
        return LlamaServerResult(text=content, latency_ms=latency_ms)
