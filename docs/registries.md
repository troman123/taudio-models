# Dual registries (public)

Open `taudio-models` owns **public** names only.

| Registry | Example ids | Role |
|----------|-------------|------|
| `PublicAssetRegistry` | `deepfilternet3` | Resource + upstream_ref + lib path |
| `PublicCapabilityRegistry` | `denoise.speech` | Generic capability hooks (`register_capability`) |

Internal short names (`de3`, `dn.speech`) live in closed **TaudioProcess** and must **not** collide with public ids. Internal registries `alias_of` / `extends` these public entries.

```python
from taudio_models import open_capability_registry, PublicAssetRegistry

assets = PublicAssetRegistry()
print([a.id for a in assets.list_assets()])

caps = open_capability_registry()
print([c.id for c in caps.list_capabilities()])
# caps.run_file("denoise.speech", "in.wav", "out/")  # needs vendored DF + libdf
```
