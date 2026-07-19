# Agent guide (Cloud + local) — taudio-models

This repo is the **open-source model layer** only.

## Hard rules

1. **Never commit model weights.**
2. **Never add Git LFS for weights.** Use `manifest.yaml` `weights:` + `taudio_models.cache.ensure_model`.
3. **Never add proprietary SDKs** — see `docs/nonfree.md`.
4. **Never add engine/pipeline APIs** (`process_file`, batch runners, stem mixing). Those belong in private TaudioProcess.
5. Keep packaging under **MIT**; copy upstream LICENSE into `licenses/<name>/` when vendoring `libs/`.
6. Stable open API: `list_models` / `get_model` / `ensure_weights` / `load_model` + unified `ModelParams`.

## Layout

- `src/taudio_models/` — catalog registry, cache, Model.load
- `libs/` — optional vendored model code (not process orchestration)
- `manifest.yaml` — `catalog` + `weights`

## Cache

1. `$TAUDIO_MODEL_CACHE`
2. else `~/.cache/taudio-models/models`
