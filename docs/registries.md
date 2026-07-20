# Dual registries (adapter)

Open `taudio-models` owns the **adapter** registries (public ids).

| Registry | Example ids | Role |
|----------|-------------|------|
| `PublicAssetRegistry` | `deepfilternet3` | Resource + upstream_ref + lib path (+ runtime aliases) |
| `PublicCapabilityRegistry` | `denoise.speech` | Capability hooks (`register_capability`, `run_*`) |

Private short names (`de3`, `dn.speech`) are **runtime-registered** onto this adapter by TaudioProcess — never committed here.

Design: [adapter-layer.md](adapter-layer.md).

```python
from taudio_models import open_capability_registry, PublicAssetRegistry

assets = PublicAssetRegistry()
print([a.id for a in assets.list_assets()])

caps = open_capability_registry()
print([c.id for c in caps.list_capabilities()])
# caps.run_file("denoise.speech", "in.wav", "out/")
```
