"""轴 4：幸存者偏差。

给定「真实历史成分 membership（date, symbol，含后来退市/被剔除的名字）」与
「回测所用股票池 universe（signal 的列 或 --universe 文件）」，
统计被漏掉的退市/剔除名字占比。
"""
from __future__ import annotations

import pandas as pd

from .base import Finding, info


def run(ctx) -> list[Finding]:
    membership = ctx.membership
    if membership is None:
        return [info(4, "缺少历史成分 membership（date,symbol），无法重建历史池；请提供 pandadata 指数成分或生命周期文件。")]

    if membership.empty or "symbol" not in membership.columns:
        return [info(4, "membership 为空或缺少 symbol 列。")]

    historical = set(membership["symbol"].astype(str))
    if ctx.signal is not None:
        universe = set(map(str, ctx.signal.columns))
    elif ctx.universe is not None:
        universe = set(map(str, ctx.universe))
    else:
        return [info(4, "缺少回测股票池（signal 列或 --universe），无法对比。")]

    missing = sorted(historical - universe)
    ratio = len(missing) / len(historical) if historical else 0.0

    evidence = (
        f"历史成分 {len(historical)} 个，回测池 {len(universe)} 个；"
        f"被漏掉的历史名 {len(missing)} 个（占比 {ratio:.1%}），如 {missing[:5]}"
    )

    if ratio > 0.1:
        return [Finding(4, "FAIL", "BLOCKER", evidence,
                        "股票池明显剔除了退市/被剔除历史名，收益存在幸存者偏差，结论被高估。",
                        "按披露日快照重建历史池、含退市收益路径（fix-library 轴4）。")]
    if ratio > 0:
        return [Finding(4, "WARN", "MAJOR", evidence,
                        "存在少量被漏掉的历史名，收益有小幅高估。",
                        "补全历史成分并披露退市收益缺口。")]
    return [Finding(4, "PASS", "INFO", evidence + "；未发现幸存者偏差。", "无。", "无需修复。")]
