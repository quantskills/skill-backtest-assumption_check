#!/usr/bin/env python3
"""合成数据自检：生成带「植入 bug」的 demo 数据，跑通全部探测器并输出 demo 审计报告。

植入的缺陷（预期应被检出）：
  - 轴1：assumptions.execution=close → close→close 前视（BLOCKER）
  - 轴2：cost_bp=0 → 零成本（BLOCKER）
  - 轴4：历史成分含 8 只退市名（DEL*）不在回测池 → 幸存者偏差（BLOCKER）
  - 轴3：在某买入日植入一字涨停、某日 volume=0 → 不可成交持仓（WARN）
  - 轴5：n_trials=120 且无校正 → 多重比较风险（WARN）
  - 轴7：篮子名义 1e8 vs Top10 ADV → 容量超限（FAIL）

运行：python scripts/self_test.py [--out out/self_test]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "detectors"))

from detectors import DETECTORS
from detectors.base import DEFAULT_ASSUMPTIONS, load_wide, load_panel, load_membership
from audit_cli import Context
from report import render_markdown, render_json, summary, timestamp

SEED = 42


def build_inputs(out_dir: str) -> dict:
    rng = np.random.default_rng(SEED)
    dates = pd.bdate_range("2023-01-02", periods=300)
    symbols = [f"S{i:03d}" for i in range(60)]
    n, m = len(dates), len(symbols)

    # 随机游走价格
    rets = rng.normal(0, 0.02, (n, m))
    close = 10.0 * np.exp(np.cumsum(rets, axis=0))
    open_ = close / (1 + rng.normal(0, 0.005, size=close.shape))
    high = np.maximum(open_, close) * (1 + rng.uniform(0, 0.01, size=close.shape))
    low = np.minimum(open_, close) * (1 - rng.uniform(0, 0.01, size=close.shape))
    volume = rng.integers(1e5, 1e6, size=close.shape).astype(float)
    amount = close * volume

    # 信号：5 日动量（基于 close 生成 → 天然"收盘生成"）
    sig_wide = pd.DataFrame(close, index=dates, columns=symbols).pct_change(5)

    # 权重：每 5 日按信号 Top-10 等权再平衡，中间日 ffill
    weights = pd.DataFrame(0.0, index=dates, columns=symbols)
    for k in range(0, n, 5):
        top = sig_wide.iloc[k].nlargest(10).index
        weights.loc[dates[k], top] = 0.1
    weights = weights.replace(0.0, np.nan).ffill().fillna(0.0)

    # 找一个买入事件，植入"一字涨停"（open==high==low 且较前收 +10%）
    filled = weights.fillna(0.0)
    prev = filled.shift(1).fillna(0.0)
    entries = [(d, s) for d in filled.index for s in filled.columns if filled.loc[d, s] > 0 and prev.loc[d, s] == 0]
    # 跳过首个交易日：那里 panel 内无前收（shift 为 NaN），一字涨停不可判定
    candidates = [e for e in entries if dates.get_loc(e[0]) > 1]
    if candidates:
        d0, s0 = candidates[0]
        i0, j0 = dates.get_loc(d0), symbols.index(s0)
        prev_close = close[i0 - 1, j0]
        close[i0, j0] = prev_close * 1.10
        open_[i0, j0] = high[i0, j0] = low[i0, j0] = close[i0, j0]

    # 再找一个买入事件，植入"停牌"（volume=0）
    if len(candidates) > 1:
        d1, s1 = candidates[1]
        volume[dates.get_loc(d1), symbols.index(s1)] = 0.0

    # 历史成分：额外含 8 只已退市名（不在回测池 → 幸存者偏差）
    hist_syms = symbols + [f"DEL{i:03d}" for i in range(8)]
    membership = pd.DataFrame({
        "date": np.repeat(dates.values, len(hist_syms)),
        "symbol": np.tile(hist_syms, len(dates)),
    })

    panel = pd.DataFrame({
        "date": np.repeat(dates.values, m),
        "symbol": np.tile(symbols, n),
        "open": open_.ravel(),
        "high": high.ravel(),
        "low": low.ravel(),
        "close": close.ravel(),
        "volume": volume.ravel(),
        "amount": amount.ravel(),
    })

    assumptions = {
        "execution": "close",   # 植入：close→close 前视
        "cost_bp": 0,           # 植入：零成本
        "horizon": 5,
        "notional": 1e8,        # 植入：容量超限
        "top_n": 10,
        "n_trials": 120,        # 植入：大量扫参
        "t_years": 300 / 365.25,
        "reported_sharpe": 2.1,
        "benchmark": "沪深300（示例）",
    }

    os.makedirs(out_dir, exist_ok=True)
    sig_wide.to_csv(os.path.join(out_dir, "signal.csv"), index_label="date")
    panel.to_csv(os.path.join(out_dir, "panel.csv"), index=False)
    weights.to_csv(os.path.join(out_dir, "weights.csv"), index_label="date")
    membership.to_csv(os.path.join(out_dir, "membership.csv"), index=False)
    with open(os.path.join(out_dir, "assumptions.json"), "w", encoding="utf-8") as fh:
        json.dump(assumptions, fh, ensure_ascii=False, indent=2)

    return {
        "signal": load_wide(os.path.join(out_dir, "signal.csv")),
        "panel": load_panel(os.path.join(out_dir, "panel.csv")),
        "weights": load_wide(os.path.join(out_dir, "weights.csv")),
        "membership": load_membership(os.path.join(out_dir, "membership.csv")),
        "assumptions": {**DEFAULT_ASSUMPTIONS, **assumptions},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="回测假设审计自检（合成数据）")
    ap.add_argument("--out", default=os.path.join("out", "self_test"))
    args = ap.parse_args()

    inputs = build_inputs(args.out)
    ctx = Context(audit_target="signal_panel（合成 demo，植入前视/零成本/幸存者/容量缺陷）", **inputs)

    findings = []
    for axis_id, key, fn in DETECTORS:
        try:
            findings.extend(fn(ctx))
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] 探测器 {key}(轴{axis_id}) 异常：{exc}", file=sys.stderr)

    ts = timestamp()
    md = render_markdown(findings, ctx, ts)
    js = render_json(findings, ctx, ts)

    md_path = os.path.join(args.out, "audit_report.md")
    js_path = os.path.join(args.out, "audit_report.json")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(md)
    with open(js_path, "w", encoding="utf-8") as fh:
        json.dump(js, fh, ensure_ascii=False, indent=2)

    s = summary(findings)
    print(f"[ok] 自检完成：{s['total']} 条 Finding → {md_path}")
    print(f"     BLOCKER={s['blockers']} MAJOR={s['majors']} MINOR={s['minors']} INFO={s['infos']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
