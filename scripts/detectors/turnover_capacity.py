"""轴 7：换手与容量。

数据级检查：
  1) 从权重序列算单边换手；
  2) 篮子名义金额（assumptions.notional）对每日 Top-n 成交额的占比（容量），
     超过 5% 视为容量受限（买卖本身会冲击价格）。
"""
from __future__ import annotations

import pandas as pd

from .base import Finding, info, one_way_turnover, panel_wide

CAPACITY_LIMIT = 0.05


def run(ctx) -> list[Finding]:
    panel, weights = ctx.panel, ctx.weights
    findings: list[Finding] = []

    turnover = one_way_turnover(weights)
    if turnover is not None:
        ann = float(turnover) * 252.0
        findings.append(Finding(
            7, "PASS" if ann < 10 else "WARN", "MINOR" if ann < 20 else "MAJOR",
            f"单边换手 {turnover:.3f}/日 ≈ {ann:.0f}/年",
            "换手偏高时，未建模成本会显著放大误差（联动轴2）。" if ann >= 10 else "无。",
            "权重序列持久化并按实际换手计入成本（fix-library 轴7）。"))
    else:
        findings.append(info(7, "缺少 weights，无法计算换手；改为代码取证。"))

    notional = float(ctx.assumptions.get("notional") or 0)
    top_n = int(ctx.assumptions.get("top_n") or 10)
    if panel is not None and notional > 0 and "amount" in panel.columns:
        adv = panel_wide(panel, "amount").mean()  # 每只股票日均成交额
        top_adv = adv.nlargest(top_n).sum()
        if top_adv > 0:
            ratio = notional / top_adv
            findings.append(
                Finding(7, "FAIL" if ratio > CAPACITY_LIMIT else "PASS",
                        "MAJOR" if ratio > CAPACITY_LIMIT else "INFO",
                        f"篮子名义 {notional:,.0f} 元 / Top-{top_n} 日均成交额 {top_adv:,.0f} 元 = {ratio:.1%}"
                        f"（容量阈值 {CAPACITY_LIMIT:.0%}）",
                        "篮子规模远超成交额，实盘无法以回测价格成交，冲击成本被忽略。" if ratio > CAPACITY_LIMIT else "无。",
                        "缩小篮子/分日建仓/建冲击成本模型（fix-library 轴7）。"))
    else:
        findings.append(info(7, "缺少面板 amount 或 notional，无法量化容量。"))

    return findings
