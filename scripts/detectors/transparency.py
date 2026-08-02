"""轴 9：报告透明度。

本质是代码/报告取证轴。数据探测器只能检查「报告关键假设是否已在 assumptions
中给出」作为提示，完整性仍由 agent 审读判断。
"""
from __future__ import annotations

from .base import Finding, info

REQUIRED = {
    "execution": "成交口径",
    "cost_bp": "成本假设",
    "horizon": "预测周期",
}


def run(ctx) -> list[Finding]:
    missing = [label for key, label in REQUIRED.items() if ctx.assumptions.get(key) in (None, "", 0)]
    if missing:
        return [Finding(9, "WARN", "MINOR",
                        f"关键假设未提供：{'、'.join(missing)}",
                        "报告可复现性不足，他人无法按披露信息重算。",
                        "补全假设清单 + 固定随机种子/数据版本 + 附复现步骤（fix-library 轴9）。")]
    return [Finding(9, "PASS", "INFO",
                    "关键假设（成交口径/成本/预测周期）已提供；建议同时披露样本区间、数据版本与参数表。",
                    "无。",
                    "无需修复。")]
