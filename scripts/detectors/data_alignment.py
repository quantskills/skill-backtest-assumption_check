"""轴 6：数据对齐与复权。

数据级检查：对已复权 close 计算日收益，标记「异常跳变」——日收益超过
全样本 5 个标准差（或绝对值 >25%）的日，可能是未处理的除权除息/数据断裂。
面板同时含 close（复权）与 raw_close（未复权）时，额外校验两者口径是否一致。
"""
from __future__ import annotations

import pandas as pd

from .base import Finding, info, panel_wide


def run(ctx) -> list[Finding]:
    panel = ctx.panel
    if panel is None:
        return [info(6, "缺少 panel，无法校验复权/对齐；改为代码取证（join 键、point-in-time）。")]

    try:
        close = panel_wide(panel, "close")
    except KeyError:
        return [info(6, "面板缺少 close 字段。")]

    ret = close.pct_change()
    std = ret.stack().std()
    if pd.isna(std) or std == 0:
        return [info(6, "复权收益无波动，无法校验异常跳变。")]

    spikes = ret[ret.abs() > max(5 * std, 0.25)]
    n_spikes = int(spikes.notna().sum().sum())
    max_abs = float(ret.abs().max().max()) if len(ret) else 0.0

    evidence = (
        f"复权日收益异常跳变 {n_spikes} 例（阈值 max(5σ≈{5 * std:.3f}, 25%)）；"
        f"样本内最大单日收益 {max_abs:.1%}"
    )

    if "raw_close" in panel.columns:
        raw = panel_wide(panel, "raw_close")
        ratio = (close / raw).replace([float("inf"), -float("inf")], float("nan"))
        stable = float(ratio.stack().dropna().std()) if not ratio.empty else 0.0
        evidence += f"；复权/未复权比 std={stable:.4f}"
        if stable > 0.01:
            return [Finding(6, "WARN", "MAJOR", evidence + "（口径不一致）",
                            "混用复权/未复权口径，收益含除权跳变。",
                            "统一复权口径、按除权除息事件校验连续性（fix-library 轴6）。")]

    if n_spikes > 0:
        return [Finding(6, "WARN", "MINOR", evidence,
                        "存在异常跳变，可能为未处理除权或数据断裂。",
                        "核对除权除息日历，统一复权口径（fix-library 轴6）。")]
    return [Finding(6, "PASS", "INFO", evidence + "；未发现异常跳变。", "无。", "无需修复。")]
