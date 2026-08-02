# Portable Loader（无原生 skill 机制的平台）

在 OpenAI Assistants / Codex / Cursor / OpenClaw 等未原生支持本 skill 元数据的平台上，直接加载以下内容即可获得同等能力：

1. **读取 `SKILL.md`**：核心协议（九大审计维度、标准 7 步工作流、严重度分级、QA 清单、合规声明）。这是行为契约，必须完整加载。
2. **按需加载 `references/`**：
   - `audit-axes.md` — 每轴检查点 / 证据 / 判定 / 修复（判定标准）
   - `evidence-collection.md` — 静态代码取证模式清单 + 数据验证方法
   - `severity-model.md` — 严重度分级与总体可信度
   - `fix-library.md` — 每轴修复方案
   - `report-format.md` — 报告输出结构
   - `source_boundary.md` — 数据来源与边界
3. **可选运行 `scripts/`**：`audit_cli.py` 做数据级验证；`self_test.py` 跑通自检 demo。依赖 pandas + numpy（见 `scripts/requirements.txt`）。

## 最小加载清单

```
SKILL.md
references/audit-axes.md
references/severity-model.md
references/report-format.md
```

其余 references 在对应轴被触发时再读取。
