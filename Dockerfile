# Published base image only (no custom torch rebuild).
# Build from repository root:
#   docker compose build
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

COPY pyproject.toml README.md LICENSE NOTICE ./
COPY src ./src
COPY docs ./docs
COPY licenses ./licenses
COPY libs ./libs
COPY scripts ./scripts
# Canonical manifest lives under package resources; place a copy at /app for TAUDIO_MODELS_ROOT
COPY src/taudio_models/resources/manifest.yaml ./manifest.yaml

# Non-editable install (image is self-contained)
RUN pip install --no-cache-dir ".[denoise]" \
 && mkdir -p /cache/models /data/in /data/out

VOLUME ["/cache", "/data"]

ENTRYPOINT ["taudio-models-denoise"]
CMD ["--help"]
