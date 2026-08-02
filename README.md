# skill-backtest-assumption-audit

[简体中文](./README.md) | [English](./README.en.md)

**独立的回测假设审计师**：对回测代码 / 策略代码 / 研究回测报告做九大维度的交易假设审计，输出「缺陷 × 证据 × 严重度 × 影响 × 修复」清单。

`role: skill` `output: AuditReport` `paradigm: cross-sectional backtest` `license: GPL-3.0`

---

`skill-backtest-assumption-audit` 是 PandaAI Quant Skills（QUANTSKILLS 组织，07 研究验证与质量工具类）提供的**回测假设审计 Skill**。给定一段回测代码、策略代码或研究回测报告，它独立取证、逐条判定，产出可复现的缺陷清单——**不是回测引擎，是回测假设审计师**。

它把「这个回测结果可信吗」拆成九大可核验的轴，并提供 `scripts/` 里的可运行探测器做数据级验证（lookahead 重放、涨跌停可达性、幸存者重建、换手容量、隐含成本等）。

## 🎯 这个 Skill 解决什么问题

回测结果漂亮不等于结论可信。常见的系统性偏误包括：

- **close→close 前视**：信号与成交用同一时点信息，IC 被系统性抬高
- **零成本**：高换手策略不扣费，净值虚高
- **买不进的持仓**：一字涨停仍被假设成交
- **幸存者偏差**：用当前成分回填历史，退市亏损被隐藏
- **多重比较**：扫了几百组参数，留下的只是运气
- **容量幻觉**：篮子规模远超成交量，实盘根本买不到

本 Skill 强制覆盖 **九大审计维度**，每条缺陷必须有证据，并按严重度分级。

## 九大审计维度

| # | 轴 | 数据验证探测器 |
|---|---|---|
| 1 | 成交时点与未来函数 | `execution_timing` |
| 2 | 交易成本 | `cost_model` |
| 3 | 涨跌停与停牌 | `price_limits` + `suspensions` |
| 4 | 幸存者偏差 | `survivorship` |
| 5 | 参数自由度与多重比较 | `parameter_freedom` |
| 6 | 数据对齐与复权 | `data_alignment` |
| 7 | 换手与容量 | `turnover_capacity` |
| 8 | 基准与超额 | —（静态取证） |
| 9 | 报告透明度 | —（静态取证） |

每轴产出 **PASS / WARN / FAIL / INFO** 判定 + 严重度（🔴 BLOCKER / 🟠 MAJOR / 🟡 MINOR / 🔵 INFO）+ 影响 + 修复建议。完整判定标准见 `references/audit-axes.md`。

## ⚡ 审计流程（标准 7 步）

```
1. 明确审计对象与输入（代码 / 报告 / 信号+面板）
2. 静态取证：按 evidence-collection.md 的模式清单扫九轴
3. 数据验证：有 signal + panel 则跑 scripts
4. 套严重度分级，逐条写「缺陷 × 证据 × 严重度 × 影响 × 修复」
5. 每轴汇总判定，给总体可信度
6. 输出结构化审计报告（Markdown）
7. 给复检建议：哪些修复后需重跑
```

## 🚀 快速开始

```bash
# 安装（Claude Code / OpenClaw / Codex 等支持 skills 目录的平台）
cp -r skill-backtest-assumption-audit ~/.claude/skills/skill-backtest-assumption-audit

# 运行数据级验证（可选，需 pandas + numpy）
python -m pip install -r scripts/requirements.txt
python scripts/audit_cli.py --signal signal.csv --panel panel.csv --weights weights.csv \
    --membership members.csv --assumptions assumptions.json --out out/
```

```text
触发示例 prompt 1：审计这段回测代码的交易假设，它用了当日收盘价成交。
触发示例 prompt 2：这份研报的 Sharpe 可信吗？看看有没有前视、零成本或幸存者偏差。
触发示例 prompt 3：给我这个策略做一次完整的回测假设审计，输出缺陷清单。
```

## 🗃️ 输入要求

- **signal**（可选）：`[date × symbol]` 浮点信号，宽表或长表
- **行情面板 panel**（可选）：长表 `date, symbol, open, high, low, close, volume`，建议含 `amount`、`suspended`、`raw_close`
- **weights**（可选）：持仓权重序列
- **membership**（可选）：历史真实成分（含退市名，幸存者轴用）
- **assumptions.json**（可选）：成本 / 成交口径 / 试验次数等假设（键见 `scripts/audit_cli.py`）

缺输入不臆测：相关维度降级为 **INFO（证据不足 → 建议补充材料）**。

## 📦 目录结构

```text
skill-backtest-assumption-audit/
├── SKILL.md                        # 核心协议（九维 + 7 步工作流 + 严重度分级）
├── references/                     # 方法论：audit-axes / evidence / severity / fixes / report / source_boundary
├── scripts/
│   ├── audit_cli.py                # 审计 CLI 入口
│   ├── self_test.py                # 合成数据自检（带植入 bug，验证能力）
│   ├── report.py                   # Markdown / JSON 报告渲染
│   ├── detectors/                  # 九轴探测器
│   └── requirements.txt
└── agents/                         # openai.yaml / cursor-rule.mdc / portable-loader
```

## 与既有 skill 的关系（互补不重复）

| 既有 skill | 它的边界 | 本 skill 补什么 |
|---|---|---|
| `skill-backtest`（05 标准协议） | 定义「正确回测」的协议 | 审计它是否符合协议 |
| `skill-backtest-overfit`（05） | 只盯选择偏差 / 多重比较一轴 | 全维度；该轴联动深挖 |
| `skill-numerical-leak-check`（07） | 只深挖未来泄露一轴 | lookahead 是九轴之一；建议联动深挖 |
| `skill-pandaai-workflow-audit`（05） | 只审计 PandaAI 工作流 JSON | 审计通用回测代码 / 报告 |

## 📐 核心约束

| 约束 | 说明 |
|---|---|
| 🔍 证据先行 | 每条缺陷必须给出证据（代码行号 / 探测器输出），无证据不下判定 |
| 🌐 独立审计 | 不替用户改代码、不背书结论，只指出假设与偏误 |
| 🚫 只述不荐 | 输出研究层面的结构与事实归纳，不构成投资建议 |
| 📉 分级不刷屏 | 严重度按 BLOCKER/MAJOR/MINOR/INFO 分级，不一刀切 |

## ⚠️ 免责声明

本仓库仅作量化研究方法层面的审计工具。不附带任何市场数据；信号与行情面板由使用者提供，数据合法性与许可由使用者负责。不验证任何收益声明，不构成任何投资建议。审计结论仅反映对给定材料 + 历史数据的检查结果，不代表未来表现。

## 📜 License

This project is licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE).

## 🐼 PandaAI / QUANTSKILLS 社群

<div align="center">
  <img src="https://raw.githubusercontent.com/quantskills/.github/main/profile/assets/pandaai-community-qr.jpg" alt="PandaAI 社群二维码" width="220">
  <br>
  <sub>扫码加入 PandaAI 社群，交流 QUANTSKILLS 技能、Agent 工作流与量化研究实践。</sub>
</div>
