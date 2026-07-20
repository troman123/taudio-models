# Build context = repository root
# Published base image only — no custom torch rebuild.
FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TAUDIO_MODELS_ROOT=/app \
    TAUDIO_MODEL_CACHE=/cache/models

RUN apt-get update \
 && apt-get install -y --no-install-recommends libsndfile1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy packaging metadata first for better layer cache when only code changes
COPY pyproject.toml README.md LICENSE NOTICE manifest.yaml ./
COPY src ./src
COPY docs ./docs
COPY licenses ./licenses
COPY libs ./libs
COPY scripts ./scripts

RUN pip install --no-cache-dir -e ".[denoise]" \
 && mkdir -p /cache/models /data/in /data/out

VOLUME ["/cache", "/data"]

# Default: show CLI help. Override args for real denoise.
ENTRYPOINT ["taudio-models-denoise"]
CMD ["--help"]
