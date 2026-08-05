"""报告渲染：把 Findings 渲染为 Markdown 与 JSON。

格式契约见 references/report-format.md。
"""
from __future__ import annotations

import json
import datetime

from detectors.base import Finding, AXES, AXIS_NAME

SEV_MARK = {"BLOCKER": "🔴", "MAJOR": "🟠", "MINOR": "🟡", "INFO": "🔵"}


def _by_axis(findings: list[Finding]) -> dict[int, list[Finding]]:
    out: dict[int, list[Finding]] = {a: [] for a, _, _ in AXES}
    for f in findings:
        out.setdefault(f.axis_id, []).append(f)
    return out


def summary(findings: list[Finding]) -> dict:
    return {
        "blockers": sum(1 for f in findings if f.severity == "BLOCKER"),
        "majors": sum(1 for f in findings if f.severity == "MAJOR"),
        "minors": sum(1 for f in findings if f.severity == "MINOR"),
        "infos": sum(1 for f in findings if f.severity == "INFO"),
        "total": len(findings),
    }


def render_markdown(findings: list[Finding], ctx, generated_at: str) -> str:
    groups = _by_axis(findings)
    lines: list[str] = []
    lines.append("# 回测假设审计报告")
    lines.append("")
    lines.append(f"> 生成：{generated_at}　判定基线：T+1 开盘成交 / Top 等权 / 双边 15bp / A 股涨跌停规则")
    lines.append("")
    lines.append("## 0. 审计对象与材料")
    lines.append("")
    lines.append(f"- 审计对象：`{ctx.audit_target or '未指定'}`")
    lines.append(f"- 材料：signal={'有' if ctx.signal is not None else '缺'} / panel={'有' if ctx.panel is not None else '缺'} / "
                 f"weights={'有' if ctx.weights is not None else '缺'} / membership={'有' if ctx.membership is not None else '缺'}")
    lines.append("")

    lines.append("## 1. 九轴判定总览")
    lines.append("")
    lines.append("| 轴 | 判定 | 严重度 | 一句话结论 |")
    lines.append("|---|---|---|---|")
    for axis_id, name, _key in AXES:
        fs = groups.get(axis_id, [])
        if not fs:
            lines.append(f"| {axis_id} {name} | — | — | 未执行 |")
            continue
        # 最严重的作为该轴主判据（严重度升序 INFO<MINOR<MAJOR<BLOCKER）
        worst = max(fs, key=lambda f: ("INFO", "MINOR", "MAJOR", "BLOCKER").index(f.severity))
        first = fs[0]
        verdict = worst.verdict if worst.severity != "INFO" else first.verdict
        sev = worst.severity
        lines.append(f"| {axis_id} {name} | {verdict} | {SEV_MARK[sev]} {sev} | {first.evidence.split('；')[0]} |")
    lines.append("")

    lines.append("## 2. 缺陷清单")
    for axis_id, name, _key in AXES:
        fs = groups.get(axis_id, [])
        if not fs:
            continue
        lines.append(f"### 轴 {axis_id}：{name}")
        for i, f in enumerate(fs, 1):
            lines.append(f"- **{f.verdict}** / {SEV_MARK[f.severity]} {f.severity}")
            lines.append(f"  - 证据：{f.evidence}")
            lines.append(f"  - 影响：{f.impact or '—'}")
            lines.append(f"  - 修复：{f.fix or '—'}")
        lines.append("")

    s = summary(findings)
    lines.append("## 3. 总体可信度")
    lines.append("")
    if s["blockers"] >= 1:
        lines.append(f"❌ 不可采信（{s['blockers']} 个 BLOCKER）—— 修复前结论作废。")
    elif s["majors"] >= 2:
        lines.append("⚠️ 谨慎采信（MAJOR 较多）—— 需修复后重估。")
    elif s["majors"] == 1:
        lines.append("✅ 有条件采信 —— 结论方向可信，量级需复核。")
    else:
        lines.append("🟢 可采信 —— 结论稳健，仍不代表未来表现。")
    lines.append("")
    lines.append("## 4. 合规声明")
    lines.append("")
    lines.append("仅供量化研究、教育与方法论参考，不构成投资建议。审计结论仅反映对给定材料 + 历史数据的检查结果，不代表未来表现。")
    lines.append("")
    return "\n".join(lines)


def render_json(findings: list[Finding], ctx, generated_at: str) -> dict:
    return {
        "schema": "backtest-assumption_check/1",
        "generated_at": generated_at,
        "audit_target": ctx.audit_target,
        "axes": [f.to_dict() for f in findings],
        "summary": summary(findings),
    }


def timestamp() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d")
