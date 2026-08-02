"""轴 1：成交时点与未来函数。

对 signal 在两种 forward return 口径下分别算 rank IC：
  - 基线（T+1 开盘成交）: open[T+1+H] / open[T+1] - 1
  - 前视（close→close）  : close[T+H] / close[T] - 1
证据 = 两条 IC 的差距；判定依据 assumptions.execution 口径。
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from .base import Finding, info, panel_wide, rank_ic


def _fwd_open(openp: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """open[T+1+H]/open[T+1]-1，对齐到信号日 T。"""
    return openp.shift(-1 - horizon) / openp.shift(-1) - 1.0


def _fwd_close(close: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """close[T+H]/close[T]-1（前视口径）。"""
    return close.shift(-horizon) / close - 1.0


def _mean_ic(signal: pd.DataFrame, fwd: pd.DataFrame) -> Optional[float]:
    ics = []
    for dt in signal.index.intersection(fwd.index):
        ic = rank_ic(signal.loc[dt], fwd.loc[dt])
        if ic is not None:
            ics.append(ic)
    if not ics:
        return None
    return float(pd.Series(ics).mean())


def run(ctx) -> list[Finding]:
    signal, panel = ctx.signal, ctx.panel
    horizon = int(ctx.assumptions.get("horizon") or 5)
    if signal is None or panel is None:
        return [info(1, "缺少 signal 或 panel，无法做数值重放；改为静态代码取证。")]

    try:
        openp = panel_wide(panel, "open")
        close = panel_wide(panel, "close")
    except KeyError:
        return [info(1, "面板缺少 open/close 字段，无法做数值重放。")]

    ic_open = _mean_ic(signal, _fwd_open(openp, horizon))
    ic_close = _mean_ic(signal, _fwd_close(close, horizon))

    if ic_open is None or ic_close is None:
        return [info(1, "有效截面样本过少，无法计算 rank IC。")]

    gap = abs(ic_close - ic_open)
    exec_mode = str(ctx.assumptions.get("execution") or "").lower()
    evidence = (
        f"T+1 开盘口径 rank IC={ic_open:.4f} vs close→close 前视口径 rank IC={ic_close:.4f}，"
        f"差距 {gap:.4f}（signal 有效截面 {signal.shape[0]} 天）。"
    )

    if exec_mode in ("close", "same_day"):
        return [Finding(1, "FAIL", "BLOCKER",
                        evidence,
                        "信号与成交同日、close→close，前视信息系统性虚增 IC，结论不可采信。",
                        "信号 shift(1)、成交价用 open[T+1]（见 fix-library 轴1）；联动 skill-numerical-leak-check 深挖。")]
    if exec_mode == "open_t1":
        return [Finding(1, "PASS", "INFO",
                        evidence + " 已声明 T+1 开盘成交。",
                        "无。",
                        "无需修复。")]
    # 未声明口径
    return [Finding(1, "WARN", "MAJOR",
                    evidence + " 但 assumptions.execution 未声明。",
                    "成交口径不透明，无法确认是否前视。",
                    "声明成交口径；若用 open[T+1] 则重跑本探测器复检。")]
