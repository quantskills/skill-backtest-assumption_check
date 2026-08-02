"""轴 5：参数自由度与多重比较。

用经典近似估算「N 次独立试验、T 年数据、真实 SR=0」下最大年化 Sharpe 的期望：
    E[max SR] ≈ sqrt(2·ln N / T)
若报告 Sharpe 与之可比，说明结果可能只是多次试验的幸存者。
"""
from __future__ import annotations

import math

import pandas as pd

from .base import Finding, info


def _t_years(ctx) -> float | None:
    t = ctx.assumptions.get("t_years")
    if t:
        return float(t)
    if ctx.panel is not None and "date" in ctx.panel.columns:
        span = (ctx.panel["date"].max() - ctx.panel["date"].min()).days
        if span > 0:
            return span / 365.25
    if ctx.signal is not None and len(ctx.signal.index) > 1:
        span = (ctx.signal.index[-1] - ctx.signal.index[0]).days
        if span > 0:
            return span / 365.25
    return None


def run(ctx) -> list[Finding]:
    n_trials = ctx.assumptions.get("n_trials")
    if n_trials is None:
        return [info(5, "未披露试验次数 n_trials，无法量化多重比较风险；请补充参数网格/因子数。")]

    try:
        n = int(n_trials)
    except (TypeError, ValueError):
        return [info(5, "n_trials 无法解析。")]

    t = _t_years(ctx)
    if t is None or t <= 0:
        return [info(5, "缺少样本区间，无法估算样本年数 T。")]

    expected_max = math.sqrt(2.0 * math.log(n) / t)
    reported = ctx.assumptions.get("reported_sharpe")
    evidence = f"N={n} 次试验、样本约 {t:.1f} 年：零假设下期望最大年化 Sharpe ≈ {expected_max:.2f}"

    if reported is not None:
        try:
            r = float(reported)
            evidence += f"；报告 Sharpe={r:.2f}"
            evidence += "，处于选择偏差合理范围内。" if r <= expected_max * 1.2 else "，显著高于随机试验期望，疑似选择偏差。"
        except (TypeError, ValueError):
            pass

    if n >= 100:
        return [Finding(5, "WARN", "MAJOR", evidence,
                        "大量试验且无校正，出现高 Sharpe 的偶然性高。",
                        "披露全部试验 → 算 Deflated Sharpe → 独立样本外确认（fix-library 轴5）；联动 skill-backtest-overfit 深挖。")]
    if n >= 20:
        return [Finding(5, "WARN", "MINOR", evidence,
                        "试验次数较多，建议做多重检验校正。",
                        "同上，至少披露试验次数并预留 holdout。")]
    return [Finding(5, "PASS", "INFO", evidence + "；试验次数较少。", "无。", "无需修复。")]
