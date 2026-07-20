# Agent guide (Cloud + local) — taudio-models

This repo is the **open adapter layer** for vendored OSS audio libs.

Canonical design: [docs/adapter-layer.md](docs/adapter-layer.md)

## Hard rules

1. **Never commit model weights.**
2. **Never add Git LFS for weights.** Use `manifest.yaml` `weights:` + `taudio_models.cache.ensure_model`.
3. **Never add proprietary SDKs** — see `docs/nonfree.md`.
4. **Never add product engine APIs** (`process_file` pipelines). Those belong in private TaudioProcess.
5. Keep packaging under **MPL-2.0**. Copy upstream LICENSE into `licenses/<name>/` when vendoring `libs/`.
6. **Adapter is the call surface:** `register_capability` + `run_file` / `run_array`. One capability = one interface.
7. Public ids only in this repo (`deepfilternet3`, `denoise.speech`). Never commit private short names (`de3`, `dn.speech`).
8. **`libs/` = inference.** `backends/` = thin per-lib adapters only. Do not reimplement algorithms.
9. Private may **runtime-register** extensions onto this adapter; open never imports private code.
10. Prefer vendored `libs/`; Docker/pip are packaging aids. Canonical manifest: `src/taudio_models/resources/manifest.yaml`.
11. Never commit weights or `*.so`.
12. Prefer `resolve_models_root()` over ad-hoc path guesses.

## Layout

- `libs/` — vendored upstream OSS
- `backends/` — per-lib thin adapters
- `capabilities/` — open capability registration
- `registry/` — adapter registries (assets + capabilities)
