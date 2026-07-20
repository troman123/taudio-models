# Agent guide (Cloud + local) — taudio-models

This repo is the **open-source model layer** only.

## Hard rules

1. **Never commit model weights.**
2. **Never add Git LFS for weights.** Use `manifest.yaml` `weights:` + `taudio_models.cache.ensure_model`.
3. **Never add proprietary SDKs** — see `docs/nonfree.md`.
4. **Never add engine/pipeline APIs** (`process_file`, batch runners, stem mixing). Those belong in private TaudioProcess.
5. Keep packaging under **MPL-2.0** (file-level copyleft). Copy upstream LICENSE into `licenses/<name>/` when vendoring `libs/` — do not re-license upstream as MPL.
6. Stable open API: `list_models` / `get_model` / `ensure_weights` / `load_model` + unified `ModelParams`.
7. Public registries: `PublicAssetRegistry` + `PublicCapabilityRegistry` (`register_capability`). Use generic ids only (`deepfilternet3`, `denoise.speech`). Never add internal short names (`de3`, `dn.speech`) here.
8. Denoise MVP: capability `denoise.speech` → asset `deepfilternet3`. Prefer `pip install -e ".[denoise]"` or `docker compose build && docker compose run --rm smoke`. Do not commit `*.so` / weight binaries.
9. Keep Docker usage in-repo (`Dockerfile`, `compose.yaml`, `scripts/docker_smoke.sh`) so clones can run without host Python.

## Layout

- `src/taudio_models/` — catalog registry, cache, Model.load
- `libs/` — optional vendored model code (not process orchestration)
- `manifest.yaml` — `catalog` + `weights`

## Cache

1. `$TAUDIO_MODEL_CACHE`
2. else `~/.cache/taudio-models/models`
