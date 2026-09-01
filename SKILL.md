---
name: backtest-assumption-check
description: Use when an agent needs to independently audit the assumptions and biases behind a backtest / strategy code / research backtest report — execution timing and lookahead, trading costs, price limits and suspensions, survivorship bias, parameter freedom and multiple testing, data alignment and adjustment, turnover and capacity, benchmark and excess returns, and reporting transparency. Outputs a structured defect list (axis x evidence x severity x impact x fix).
quantSkills:
  organization: https://github.com/quantskills
  repository: wangofcong/skill-backtest-assumption_check
  repository_url: https://github.com/wangofcong/skill-backtest-assumption_check
  project_type: skill
  collection: 研究验证与质量工具
  license: GPL-3.0
  category: tooling
  tags:
  - backtest-audit
  - lookahead
  - survivorship
  - multiple-testing
  - trading-costs
  platforms:
  - claude-code
  - codex
  - openclaw
  - cursor
  language: zh-en
  status: stable
  validation_level: listed
  maintainer_type: community
  requires: []
  summary_zh: 独立的回测假设审计师：对回测代码/策略代码/研究报告按九大维度（成交时点、成本、涨跌停停牌、幸存者、多重比较、数据对齐、换手容量、基准、透明）逐条取证，输出缺陷×证据×严重度×影响×修复清单，配套可运行校验脚本。
  summary_en: Independent backtest assumption auditor covering nine axes (execution timing, costs, price limits, survivorship, multiple testing, data alignment, turnover, benchmark, transparency), producing a defect list with evidence, severity, impact, and fixes, plus runnable verification scripts.
---

```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "粘贴要审计的回测代码 / 策略代码 / 研究报告，或补充审计重点（可选）",
    "required": false
  },
  "fields": [
    {
      "key": "audit_target",
      "type": "select",
      "label": "审计对象",
      "default": "backtest_code",
      "options": [
        { "value": "backtest_code", "label": "回测代码" },
        { "value": "strategy_code", "label": "策略代码" },
        { "value": "research_report", "label": "研究报告" },
        { "value": "signal_panel", "label": "信号 + 行情面板" }
      ]
    },
    {
      "key": "horizon",
      "type": "select",
      "label": "预测周期",
      "default": "5",
      "options": [
        { "value": "1", "label": "未来 1 日" },
        { "value": "5", "label": "未来 5 日" },
        { "value": "10", "label": "未来 10 日" }
      ]
    },
    {
      "key": "panel_path",
      "type": "textarea",
      "label": "行情 / 信号文件路径",
      "placeholder": "可选：提供 signal 与 OHLCV 面板路径以运行数据级验证",
      "help": "留空时仅做静态代码取证"
    }
  ],
  "prompt_template": "{{#task}}审计任务与材料：\n{{task}}\n\n{{/task}}{{#attachments}}用户上传的材料（已放入工作区）：\n{{attachments}}\n\n{{/attachments}}请对 {{audit_target}} 做回测假设审计{{#panel_path}}（数据文件：{{panel_path}}）{{/panel_path}}，按九大审计维度逐条取证并给出判定，输出「缺陷 × 证据 × 严重度 × 影响 × 修复」清单，输出中文报告。"
}
```

# Backtest Assumption Audit

> 对一份回测代码 / 策略代码 / 研究回测报告做**独立、全维度**的交易假设审计，输出逐条「缺陷 × 证据 × 严重度 × 影响 × 修复」清单。**不是回测引擎，是回测假设审计师**。

## 核心规则

1. **独立审计**：不替用户改代码、不背书结论，只指出假设与偏误
2. **九维全覆盖**：默认检查全部九个维度（见下），不能只挑软柿子
3. **证据先行**：每条缺陷必须有证据（代码位置 / 数据验证输出），无证据不下判定
4. **严重度分级**：阻断 / 重大 / 一般 / 提示（定义见 `references/severity-model.md`）
5. **脚本验证优先**：能用 `scripts/` 做数据验证的，不要靠猜
6. **只述不荐**：输出研究层面的结构与事实归纳，不构成投资建议

## 九大审计维度

| # | 轴 | 判定什么 | 数据验证 detector |
|---|---|---|---|
| 1 | 成交时点与未来函数 | 信号日 vs 成交时点；close→close 前视；是否遵守 T+1 开盘成交 | `execution_timing` |
| 2 | 交易成本 | 佣金 / 印花税 / 滑点 / 冲击是否覆盖；A股双边成本假设是否合理 | `cost_model` |
| 3 | 涨跌停与停牌 | Top 持仓买入日一字涨停（买不进）、卖出日一字跌停；停牌处理 | `price_limits` + `suspensions` |
| 4 | 幸存者偏差 | 股票池是否用当前成分回填历史；退市 / 新股处理 | `survivorship` |
| 5 | 参数自由度与多重比较 | 试验次数 / 样本量 → Deflated Sharpe；选择偏差 | `parameter_freedom` |
| 6 | 数据对齐与复权 | 复权一致性、除权除息、停牌日、财报 point-in-time | `data_alignment` |
| 7 | 换手与容量 | 单边换手、篮子成交额占比（ADV）、冲击成本 | `turnover_capacity` |
| 8 | 基准与超额 | 基准可比性、隐藏基准选择 | —（静态取证） |
| 9 | 报告透明度 | 假设披露完整性、结果可复现性 | —（静态取证） |

每轴产出 **PASS / WARN / FAIL / INFO** 判定 + 严重度 + 影响 + 修复。完整判定标准见 `references/audit-axes.md`。

## 工作流（标准 7 步）

```
1. 明确审计对象与输入（代码 / 报告 / 信号+面板；audit_target 类型）
2. 静态取证：读代码或报告，按 evidence-collection.md 的模式清单扫九轴
3. 数据验证：有 signal + panel 则跑 scripts（lookahead 回放 / 涨跌停可达 / 幸存者重建 / 换手容量 / 隐含成本）
4. 套严重度分级，逐条写「缺陷 × 证据 × 严重度 × 影响 × 修复」
5. 每轴汇总判定，给总体结论与可信度
6. 输出结构化审计报告（Markdown，格式见 report-format.md）
7. 给复检建议：哪些修复后需重跑、如何证明修复有效
```

## 脚本用法（可运行验证）

```bash
# 全维度审计：给定 signal + 行情面板 + 假设，输出 Markdown + JSON 报告
python scripts/audit_cli.py --signal signal.csv --panel panel.parquet --assumptions assumptions.json --out out/

# 合成数据自检：生成带植入 bug 的 demo，验证审计能力
python scripts/self_test.py
```

无对应输入时，相关探测器降级为「证据不足 → 建议补充材料」，绝不臆测。

## 接口映射

| 本 skill 概念 | 你的项目对应 |
|---|---|
| 审计对象 | 回测代码 / 策略代码 / 研究报告 / signal + panel |
| `signal` | `[date × symbol]` 浮点 DataFrame（可选） |
| 行情面板 `panel` | 含 `open` / `high` / `low` / `close` / `volume`（建议含涨跌停、停牌标记） |
| `assumptions` | 成本 / 成交时点 / 滑点 / 手续费假设（JSON） |
| Findings | `{axis, verdict, severity, evidence, impact, fix}` |

**判定基线**：T+1 开盘成交、Top 等权、双边 15bp、A 股涨跌停规则 —— 对齐生态 `skill-backtest` 标准协议。

## 按需加载

| 何时读 | 文件 |
|---|---|
| 九轴判定标准 / 检查点 | `references/audit-axes.md` |
| 静态代码取证模式清单 | `references/evidence-collection.md` |
| 严重度怎么定 | `references/severity-model.md` |
| 修复方案库 | `references/fix-library.md` |
| 报告输出格式 | `references/report-format.md` |
| 数据来源与边界 | `references/source_boundary.md` |

## QA 检查清单

- [ ] 九轴都过了一遍，没有只挑软柿子？
- [ ] 每条缺陷都有证据（代码行号 / 数据验证输出）？
- [ ] 严重度按 `severity-model.md` 分级，没有全标成「重大」？
- [ ] lookahead 尝试了数值重放，或明确联动 `skill-numerical-leak-check` 深挖？
- [ ] 报告是「缺陷×证据×严重度×影响×修复」结构，不是只有结论？
- [ ] 能用脚本跑的验证都跑了，没靠猜？

## 跨工具适配

- OpenAI Codex / Assistants → `agents/openai.yaml`
- Cursor → `agents/cursor-rule.mdc`
- 无原生 skill 机制 → `agents/portable-loader.md`

---

## 项目边界（量化研究合规声明）

- **数据来源**：本 skill 不附带任何市场数据；信号与行情面板由使用者提供（可经 pandadata 导出），数据合法性与许可由使用者负责。
- **假设与参数**：审计判定的假设基线对齐生态标准协议（T+1 开盘成交、Top 等权、双边 15bp、A 股涨跌停规则），以该基线为参照，不等同于真实交易。
- **已知限制**：不自动重跑回测、不模拟市场冲击；判定质量取决于输入材料完整度；对单股序列建模 / 时序模型不适用（默认 pooled cross-section 范式）。
- **风险边界**：审计结论仅反映对给定材料 + 历史数据的检查结果，不代表未来表现。
- **用途定位**：**仅供量化研究、教育与方法论参考**。不构成任何形式的投资建议、交易信号或获利保证。使用者据此实盘交易的全部后果由使用者自负。
