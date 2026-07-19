# Agent guide (Cloud + local)

This repo is the **open-source engines** dependency for local `TaudioProcess`.

## Hard rules

1. **Never commit model weights** (`.ckpt`, `.pth`, `.onnx`, `.safetensors`, large `.bin`).
2. **Never add Git LFS for weights.** Use `manifest.yaml` URLs + `taudio_engines.cache.ensure_model`.
3. **Never add proprietary SDKs** (e.g. `mpa_sdk`) — see `docs/nonfree.md`.
4. Keep umbrella packaging under **MIT**. Preserve upstream LICENSE files under `licenses/<name>/` and update `NOTICE` when vendoring libs into `libs/`.
5. Prefer small, reviewable PRs: one engine or one manifest/model entry at a time.
6. **Stable API only:** TaudioProcess talks via `open_registry().list_models / get_model / run_model` and unified `ModelParams`. Do not expose lib-specific kwargs outside `ModelParam` schemas. See `docs/api.md`.

## Layout

- `src/taudio_engines/` — manifest loaders + download/cache API
- `libs/` — vendored engine source (code only)
- `manifest.yaml` — engines + model download metadata
- `scripts/` — CLI helpers

## Model cache

Runtime downloads go to:

1. `$TAUDIO_MODEL_CACHE` if set
2. else `~/.cache/taudio-engines/models`

Do not write weights into the git working tree except under `.cache/` (gitignored).

## Useful prompts for Cloud Agents

- Add a vendored lib under `libs/` with its LICENSE copied to `licenses/`.
- Register model download URLs + sha256 in `manifest.yaml`.
- Improve `ensure_model` (retries, progress, mirrors).
