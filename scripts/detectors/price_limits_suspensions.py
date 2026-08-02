"""轴 3：涨跌停与停牌。

数据验证两件事：
  1) 持仓「买入日」是否一字涨停（买不进）或「卖出日」一字跌停（卖不出）；
  2) 持仓「交易日」是否停牌（volume==0 / 价格缺失）却仍被假设成交。
一字板近似判据：open==high==low（无价格区间）且较前收涨/跌幅 ≥ 9%（主板近似；科创板/北交所规则不同，以面板 limit_up/limit_down 字段为准，若有）。
"""
from __future__ import annotations

import pandas as pd

from .base import Finding, info, panel_wide

UP_APPROX = 0.09


def _entry_days(weights: pd.DataFrame) -> list[tuple[pd.Timestamp, str]]:
    """从权重序列找「首次由 0/NaN → >0」的 (日期, symbol) 买入事件。"""
    filled = weights.fillna(0.0)
    prev = filled.shift(1).fillna(0.0)
    entry = (filled > 0) & (prev == 0)
    rows = []
    for dt in entry.index:
        for sym in entry.columns[entry.loc[dt]]:
            rows.append((dt, sym))
    return rows


def run(ctx) -> list[Finding]:
    panel, weights = ctx.panel, ctx.weights
    findings: list[Finding] = []
    if panel is None or weights is None:
        return [info(3, "缺少 panel 或 weights，无法验证涨跌停/停牌可达性；改为静态代码取证。")]

    close = panel_wide(panel, "close")
    openp = panel_wide(panel, "open")
    high = panel_wide(panel, "high")
    low = panel_wide(panel, "low")

    # 一字板判据：open==high==low 且较前收涨跌幅超阈值
    prev_close = close.shift(1)
    ret = close / prev_close - 1.0
    oneword = (openp == high) & (high == low) & (openp.notna() & low.notna())
    limit_up = oneword & (ret > UP_APPROX)
    limit_down = oneword & (ret < -UP_APPROX)

    entry = _entry_days(weights)
    bought_at_up, sold_at_down, suspended = [], [], []

    volume = panel_wide(panel, "volume") if "volume" in panel.columns else None
    suspended_flag = panel_wide(panel, "suspended") if "suspended" in panel.columns else None

    for dt, sym in entry:
        try:
            if bool(limit_up.loc[dt, sym]):
                bought_at_up.append((dt.strftime("%Y-%m-%d"), sym))
            if bool(limit_down.loc[dt, sym]):
                sold_at_down.append((dt.strftime("%Y-%m-%d"), sym))
        except KeyError:
            continue
        # 停牌：volume==0 或价格缺失 或显式 suspended 标记
        if suspended_flag is not None:
            try:
                if bool(suspended_flag.loc[dt, sym]):
                    suspended.append((dt.strftime("%Y-%m-%d"), sym))
                    continue
            except KeyError:
                pass
        if volume is not None:
            try:
                v = volume.loc[dt, sym]
                if pd.isna(v) or v == 0:
                    suspended.append((dt.strftime("%Y-%m-%d"), sym))
            except KeyError:
                pass

    total_entries = len(entry)
    n_up, n_down, n_sus = len(bought_at_up), len(sold_at_down), len(suspended)

    if total_entries == 0:
        return [info(3, "权重序列中没有可识别的买入事件；改用代码取证。")]

    parts = []
    if n_up:
        parts.append(f"买入日一字涨停 {n_up} 例（如 {bought_at_up[:3]}）")
    if n_down:
        parts.append(f"卖出日一字跌停 {n_down} 例（如 {sold_at_down[:3]}）")
    if n_sus:
        parts.append(f"停牌日仍假设成交 {n_sus} 例（如 {suspended[:3]}）")
    if not parts:
        parts.append("未发现不可成交持仓")

    evidence = f"共 {total_entries} 次买入事件；" + "；".join(parts) + "。"

    if n_up or n_down or n_sus:
        return [Finding(3, "WARN", "MAJOR", evidence,
                        "部分持仓在无法成交的价位/日期被假设成交，收益含不可实现部分。",
                        "买入剔除一字涨停、卖出剔除一字跌停、停牌日不计收益（fix-library 轴3）。")]
    return [Finding(3, "PASS", "INFO", evidence, "无。", "无需修复。")]
