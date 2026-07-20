# 适配层设计（taudio-models）

> 本文是开发契约。代码与文档冲突时以本文为准。

## 一句话

**适配层是唯一调用入口。**  
开源模型经薄适配挂上来；私有扩展也**注册**进适配层；私有产品代码**只调适配层**，不直连 `libs/`，不直连扩展实现。

## 为什么

各开源库能力相近、接口不同。需要一层统一对外（类似多厂商 Token API 的转发层）：

- 调用方只认「能力 id + 统一接口」
- 换底层库 = 换适配，不换调用方式
- 私有扩展与开源能力走同一扇门

## 分层

```text
私有产品（TaudioProcess AudioEngine / 业务）
        │  只调用适配层 run_file / run_array
        ▼
适配层（taudio-models PublicCapabilityRegistry）
        │  已注册的能力 id（开源 + 运行时挂上的私有扩展）
        ▼
backends/*（按库薄适配） ──► libs/*（上游真实现）
```

| 层 | 职责 | 禁止 |
|----|------|------|
| `libs/` | 上游开源实现 | 产品短名、业务流水线 |
| `backends/` | 单库 → 统一接口的薄转发 | 重写算法、第二套推理 |
| **适配层** | 注册表 + `run_file` / `run_array` | 旁路调用、按库暴露多套 API |
| 私有扩展 | 实现后 **register** 进适配层 | 被产品代码直接 import 调用 |
| 私有产品 | 调适配层（扩展 id 或底层 id） | 直连 libs / 直连扩展模块 |

## 统一接口（一个能力一套）

每个能力 id 对外只有：

- `run_file(input, output_dir, *, asset_id=, params=) -> list[Path]`
- `run_array(audio, sample_rate, *, asset_id=, params=) -> (audio, sr)`

示例：

| 能力 id | 来源 | 含义 |
|---------|------|------|
| `denoise.speech` | 开源注册 | 底层降噪能力（默认 asset `deepfilternet3`） |
| `dn.speech` | 私有运行时注册 | 产品扩展（可组合/转发到底层能力） |

调用扩展：`adapter.run_file("dn.speech", ...)`  
调用底层：`adapter.run_file("denoise.speech", ...)`  
**同一适配层，同一套方法。**

## 注册

### 开源

```python
@register_capability("denoise.speech")
def build(...): ...
```

实现只做：选 asset → 调对应 `backends/` → 进 `libs/`。

### 私有

1. 用同一 `@register_capability("dn.speech")`（或等价 API）把扩展挂进适配层  
2. 启动时 `open_adapter()`：导入扩展模块 +（可选）注册 asset 别名（如 `de3` → `deepfilternet3`）  
3. 产品只拿 `open_adapter()` 返回的 registry 调用  

开源仓**不提交**私有 id；私有 id 仅运行时挂载。

## Asset

- 开源稳定 id：`deepfilternet3` 等  
- 私有短名：运行时 `register_alias("de3", "deepfilternet3")`，仍由适配层 `ensure` 解析  
- 不在开源 manifest 里写死私有短名  

## 明确禁止

1. 私有再维护一套「主调用」registry（旧 `InternalCapabilityRegistry.run_*`）与适配层并行  
2. 产品 `import` 扩展实现并直接调用  
3. 产品或私有扩展绕过适配层直接调 `libs/`  
4. 每个开源库对外再暴露一套不同的调用 API  

## 改造对照（本轮）

| 旧 | 新 |
|----|----|
| `InternalCapabilityRegistry` 自己 `run_*` 再转发 | 删除；扩展 **register** 进适配层 |
| `AudioEngine` → Internal → Public | `AudioEngine` → **仅**适配层 |
| 文档多套「extends / 外包」说法 | 以本文为准 |

## 调用示例

```python
# 私有仓
from taudio.adapter import open_adapter

adapter = open_adapter()  # 已挂私有扩展 + asset 别名

# 扩展能力
adapter.run_file("dn.speech", "in.wav", "out/")

# 底层开源能力（同一层）
adapter.run_file("denoise.speech", "in.wav", "out/")
```
