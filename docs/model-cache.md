# Model download and cache

## Policy

- Weights are **never** stored in the git repository.
- `manifest.yaml` declares `urls`, `sha256`, `cache_key`, and license metadata.
- Runtime code downloads into a cache directory, verifies checksum, then returns a local path.

## Cache root resolution

1. Environment variable `TAUDIO_MODEL_CACHE` (recommended for servers / shared disks)
2. Otherwise `~/.cache/taudio-models/models`

Cached file path: `{cache_root}/{cache_key}`.

## API

- `taudio_models.cache.ensure_model(manifest, model_id)` — download if missing/mismatched
- `taudio_models.cache.cache_root()` — resolve cache directory
- CLI: `taudio-models-fetch --list|--model ID|--all`

## Adding a model

1. Confirm the weight is legally redistributable at the chosen URL.
2. Add an entry under `models:` in `manifest.yaml` with `urls` and `sha256`.
3. Point an engine `requires_models` at that id when wiring the engine.
4. Do not commit the binary.
