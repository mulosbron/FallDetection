FROM ubuntu:24.04 AS llama-builder

ARG DEBIAN_FRONTEND=noninteractive
# CPU-only / VLM: use ggml-org mainline (no fork required). Optionally override with LLAMA_REPO_URL.
ARG LLAMA_REPO_URL=https://github.com/ggml-org/llama.cpp.git
ARG LLAMA_REPO_REF=master

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    cmake \
    build-essential \
    ninja-build \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN git clone --depth=1 --branch "${LLAMA_REPO_REF}" "${LLAMA_REPO_URL}" llama-src
WORKDIR /build/llama-src
RUN cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DLLAMA_BUILD_SERVER=ON \
    -DLLAMA_BUILD_WEBUI=OFF \
    -DLLAMA_MTMD=ON
RUN cmake --build build --config Release -j

FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgomp1 \
    bash \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system app && useradd --system --gid app --create-home --home-dir /home/app app

COPY --from=llama-builder /build/llama-src/build/bin/llama-cli /usr/local/bin/llama-cli
COPY --from=llama-builder /build/llama-src/build/bin/llama-server /usr/local/bin/llama-server
COPY --from=llama-builder /build/llama-src/build/bin/lib*.so* /usr/local/lib/
RUN chmod +x /usr/local/bin/llama-cli /usr/local/bin/llama-server
RUN ldconfig

COPY --chown=app:app requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app main.py .
COPY --chown=app:app app ./app
COPY --chown=app:app scripts ./scripts
RUN chmod +x /app/scripts/bootstrap_model.sh
RUN sed -i 's/\r$//' /app/scripts/bootstrap_model.sh
RUN mkdir -p /app/model && chown -R app:app /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/app/scripts/bootstrap_model.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
