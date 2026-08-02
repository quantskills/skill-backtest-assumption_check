"""轴 2：交易成本。

核心判据：假设双边成本 cost_bp。若为 0 或缺失 → FAIL BLOCKER（零成本）。
有权重序列时给出换手与「按生态基线 15bp」折算的年化成本拖累作为证据。
"""
from __future__ import annotations

import pandas as pd

from .base import Finding, one_way_turnover

BASELINE_BP = 15  # 生态基线双边成本


def run(ctx) -> list[Finding]:
    cost_bp = ctx.assumptions.get("cost_bp")
    if cost_bp is None:
        cost_bp = 0  # 未声明视同未计入

    turnover = one_way_turnover(ctx.weights)
    turn_txt = ""
    if turnover is not None:
        ann_turn = float(turnover) * 252.0
        drag = ann_turn * BASELINE_BP / 10000.0
        turn_txt = f"（单边换手 {turnover:.3f}/日 ≈ {ann_turn:.0f}/年；按基线 {BASELINE_BP}bp 双边折算年化拖累 ≈ {drag:.1%}）"

    try:
        cost_bp = float(cost_bp)
    except (TypeError, ValueError):
        return [Finding(2, "FAIL", "BLOCKER", "assumptions.cost_bp 无法解析。", "成本假设不可用。", "以 JSON 数字提供 cost_bp（bp）。")]

    if cost_bp == 0:
        return [Finding(2, "FAIL", "BLOCKER",
                        f"假设成本 = 0bp {turn_txt}",
                        "零成本 + 换手让净值系统性虚高，长期结论必然失真。",
                        "双边成本从毛收益扣减（基线 15bp，按账户参数建模）；重跑本探测器复检隐含成本。")]
    if cost_bp < BASELINE_BP:
        return [Finding(2, "WARN", "MAJOR",
                        f"假设成本 {cost_bp:g}bp，低于生态基线 {BASELINE_BP}bp{turn_txt}",
                        "成本偏低，收益/Sharpe 可能被高估。",
                        "成本对齐基线或实际账户参数；做成本敏感性分析。")]
    return [Finding(2, "PASS", "INFO",
                    f"假设成本 {cost_bp:g}bp，达到/高于基线 {BASELINE_BP}bp{turn_txt}",
                    "无。",
                    "无需修复。")]
