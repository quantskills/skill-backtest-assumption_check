# 审计报告输出格式

> 报告是交付物。固定结构，让不同审计间可比。Markdown 为主（scripts 同时产出 JSON 便于程序消费）。

## 报告结构

```markdown
# 回测假设审计报告

## 0. 审计对象与材料
- 审计对象类型：回测代码 / 策略代码 / 研究报告 / 信号+面板
- 材料清单：提供/缺失（缺失项标出，相关轴降级为 INFO）
- 判定基线：T+1 开盘成交 / Top 等权 / 双边 15bp / A 股涨跌停规则

## 1. 九轴判定总览
| 轴 | 判定 | 严重度 | 一句话结论 |
|---|---|---|---|
| 1 成交时点 | FAIL | 🔴 BLOCKER | close→close 前视 |
| 2 交易成本 | FAIL | 🔴 BLOCKER | 成本=0 |
| ... | | | |

## 2. 缺陷清单（逐条）
每条：
### 缺陷 #1 — 轴 1：成交时点与未来函数
- **判定**：FAIL　**严重度**：🔴 BLOCKER
- **证据**：`strategy.py:42` 信号未 shift；`execution_timing` 回放显示 close→close 年化收益虚高 +6.2%
- **影响**：结论方向/量级系统性失真，不可采信
- **修复**：信号 shift(1)，成交价用 open[T+1]（见 fix-library 轴1）
- **复检**：重跑 execution_timing，两条曲线不再重合

## 3. 总体可信度
❌ 不可采信（≥1 BLOCKER）—— 修复前结论作废

## 4. 复检建议
- 优先修 BLOCKER → 重跑 → 再审计
- 联动：skill-numerical-leak-check（轴1深挖）/ skill-backtest-overfit（轴5深挖）

## 5. 合规声明
仅供量化研究、教育与方法论参考，不构成投资建议。
```

## scripts 输出契约

`audit_cli.py --out out/` 产出：

- `out/audit_report.md` —— 人类可读（如上结构）。
- `out/audit_report.json` —— 机器可读：

```json
{
  "schema": "backtest-assumption-audit/1",
  "generated_at": "2026-08-01",
  "axes": [
    {
      "axis_id": 1,
      "axis": "execution_timing",
      "verdict": "FAIL",
      "severity": "BLOCKER",
      "evidence": "lookahead replay gap = 6.2% annualized",
      "impact": "...",
      "fix": "..."
    }
  ],
  "summary": { "blockers": 2, "majors": 0, "minors": 1, "infos": 2 }
}
```

## 写作纪律

1. **每条缺陷 5 要素齐全**：缺陷 / 证据 / 严重度 / 影响 / 修复。
2. **证据可引用**：代码行号或探测器输出 + 关键数字。
3. **判定来自证据**：无法取证 → INFO（证据不足），不臆测。
4. **结论先行的总览表 + 逐条细节**，别只给结论也不只给流水账。
