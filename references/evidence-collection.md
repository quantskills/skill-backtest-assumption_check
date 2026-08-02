# 取证方法：静态代码扫描模式 + 数据验证

> 审计的第一原则是**证据先行**。本文件给出每类缺陷的取证途径：A) 静态代码 / 报告取证（grep 模式清单）；B) 数据验证（scripts 探测器）。

## A. 静态取证模式清单（代码 / 报告）

> 这是 grep / 审读的起点，按轴组织。命中模式只是**线索**，需结合上下文确认，不构成最终判定。

| 轴 | 可疑模式（grep） | 说明 |
|---|---|---|
| 1 成交时点 | `close.shift(0)`、`df["ret"] = df.close.pct_change()`、信号列没 `shift(1)`、`open[t]` 用在同日信号上 | 前视最常藏在「信号即日成交」里 |
| 1 成交时点 | `signal.iloc[i]` 配 `price.iloc[i]`（同日） | 疑似 close→close |
| 2 成本 | 搜不到 `cost` / `fee` / `commission` / `slippage` / `tax`；`fee = 0` | 零成本是高换手回测的头号虚高来源 |
| 3 涨跌停 | 无 `limit` / `paused` / `停牌` / `涨停`；成交不校验价格可达 | 一字板买不进 / 卖不出 |
| 4 幸存者 | 股票池 = `today` / `current` / `index_members_now`；无历史成分文件 | 当前成分回填历史 |
| 5 自由度 | `for p in params`、`grid`、`sweep`、`trials`；报告没写试验次数 | 扫参后未校正 |
| 6 数据对齐 | `merge` 没对齐日期键；财报用 `period` 不用 `announce`；复权口径混用 | point-in-time 前视 / 复权不一致 |
| 7 换手 | 无权重序列持久化；无 `turnover` 统计；篮子金额没有和 ADV 比 | 换手 / 容量未评估 |
| 8 基准 | 基准 = 自定义组合 / 无风险利率；`excess = strategy - 0` | 基准错配 |
| 9 透明 | 无样本区间、无参数表、无数据版本、无随机种子 | 不可复现 |

**取证动作**：
1. 列出命中行号与上下文（代码引用要精确到文件:行）。
2. 对每条命中选择「确认 / 排除」：读上下文判断是否真的违反基线。
3. 无法从代码确认的，转入数据验证（B 节）或标为「证据不足（INFO）」。

## B. 数据验证（scripts 探测器）

> 给定 signal + panel + assumptions，用脚本产出可引用的数值证据。运行方式见 `SKILL.md` 脚本用法。

| 探测器 | 输入 | 输出证据 | 对应轴 |
|---|---|---|---|
| `execution_timing` | signal、panel、assumptions.execution | 前缀回放两条净值曲线；lookahead 收益差 | 1 |
| `cost_model` | 净值 / 收益序列、assumptions.cost | 隐含双边成本估计（bp），对比假设 | 2 |
| `price_limits` | panel（含 limit up/down 或 high/low）、持仓序列 | 涨停买入 / 跌停卖出日清单 | 3 |
| `suspensions` | panel 停牌标记、持仓序列 | 停牌日持仓清单 | 3 |
| `survivorship` | 历史成分 / 生命周期文件、回测池 | 缺退市名的比例、收益缺口估计 | 4 |
| `parameter_freedom` | N 试验、样本量、年化波动 | Deflated Sharpe、期望最大 Sharpe | 5 |
| `data_alignment` | panel、除权事件表 | 复权跨除权日一致性检查 | 6 |
| `turnover_capacity` | 权重序列、成交额面板 | 单边换手、篮子 / ADV 占比 | 7 |

**证据引用规范**：报告中的每条缺陷都要能指向「代码行号」或「探测器输出文件名 + 关键数字」，二者至少其一。

## C. 取证边界

- 不要为取证去改用户的策略代码。
- 若输入材料缺（如只有报告没有代码），相应轴降级为 **INFO（证据不足 → 建议补充材料）**，并在报告里显式列出缺哪些材料。
- 探测器输出只是证据，**判定与严重度仍由审计者（agent）综合给出**，并写入报告。
