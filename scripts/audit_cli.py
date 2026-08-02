#!/usr/bin/env python3
"""回测假设审计 CLI（协议 + 可运行脚本的入口）。

用法：
  python scripts/audit_cli.py --signal signal.csv --panel panel.parquet \
      --weights weights.csv --membership members.csv \
      --assumptions assumptions.json --out out/

说明：
  - signal / weights  宽表（date 索引 + symbol 列）或长表（date, symbol, value/signal/weight）
  - panel             长表（date, symbol, open, high, low, close, volume[, amount, suspended, raw_close]）
  - membership        长表（date, symbol），真实历史成分（含退市名）
  - assumptions       JSON，键见 DEFAULT_ASSUMPTIONS
  - 缺输入 → 相关探测器降级为 INFO（证据不足），不会臆测
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field

import pandas as pd

# 允许 scripts/ 与 scripts/detectors/ 下的直接运行
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "detectors"))

from detectors import DETECTORS
from detectors.base import DEFAULT_ASSUMPTIONS, load_wide, load_panel, load_membership
from report import render_markdown, render_json, summary, timestamp


@dataclass
class Context:
    audit_target: str
    signal: pd.DataFrame | None = None
    panel: pd.DataFrame | None = None
    weights: pd.DataFrame | None = None
    membership: pd.DataFrame | None = None
    universe: pd.DataFrame | None = None
    assumptions: dict = field(default_factory=dict)


def load_assumptions(path: str | None) -> dict:
    merged = dict(DEFAULT_ASSUMPTIONS)
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            user = json.load(fh)
        merged.update({k: v for k, v in user.items() if v is not None})
    return merged


def main() -> int:
    ap = argparse.ArgumentParser(description="回测假设审计")
    ap.add_argument("--signal", help="signal 文件（date×symbol）")
    ap.add_argument("--panel", help="行情面板（长表 date,symbol,OHLCV）")
    ap.add_argument("--weights", help="权重序列（date×symbol）")
    ap.add_argument("--membership", help="历史成分（date,symbol）")
    ap.add_argument("--universe", help="回测股票池文件（可选）")
    ap.add_argument("--assumptions", help="假设 JSON 文件")
    ap.add_argument("--audit-target", default="backtest_code", help="审计对象描述")
    ap.add_argument("--out", default="out", help="输出目录")
    args = ap.parse_args()

    assumptions = load_assumptions(args.assumptions)

    ctx = Context(
        audit_target=args.audit_target,
        signal=load_wide(args.signal),
        panel=load_panel(args.panel),
        weights=load_wide(args.weights),
        membership=load_membership(args.membership),
        assumptions=assumptions,
    )
    if args.universe and os.path.exists(args.universe):
        u = pd.read_csv(args.universe)
        ctx.universe = u["symbol"] if "symbol" in u.columns else u.iloc[:, 0]

    findings = []
    for axis_id, key, fn in DETECTORS:
        try:
            findings.extend(fn(ctx))
        except Exception as exc:  # noqa: BLE001 —— 单个探测器失败不阻塞审计
            print(f"[warn] 探测器 {key}(轴{axis_id}) 异常：{exc}", file=sys.stderr)

    os.makedirs(args.out, exist_ok=True)
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
    print(f"[ok] 审计完成：{s['total']} 条 Finding → {md_path}")
    print(f"     BLOCKER={s['blockers']} MAJOR={s['majors']} MINOR={s['minors']} INFO={s['infos']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
