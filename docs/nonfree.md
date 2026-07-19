# Non-free / not in this repository

The following must **not** be committed to `taudio-models`:

| Item | Reason | How to use locally |
|------|--------|--------------------|
| `mpa_sdk` and related proprietary filters | Not open-source redistributable | Keep outside this repo; document private path in your local framework config |
| License-unknown or non-redistributable checkpoints | Cannot ship or auto-download in a public project | Do not add to `manifest.yaml` |
| Closed ffmpeg plugin builds with unclear redistribution terms | Prefer system ffmpeg | Install ffmpeg via OS package manager |

If you need a private sidecar cache of non-free assets, keep it completely outside this git tree and never open a PR that adds those files.
