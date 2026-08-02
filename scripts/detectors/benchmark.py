"""轴 8：基准与超额。

本质是代码/报告取证轴，无独立数据探测器。本探测器只把「基准是否声明/可比」
变成一条带判定依据的 Finding，供报告引用。
"""
from __future__ import annotations

from .base import Finding, info


def run(ctx) -> list[Finding]:
    benchmark = ctx.assumptions.get("benchmark")
    if not benchmark:
        return [info(8, "未声明基准；请审读代码/报告确认：基准是否与策略标的可比、超额口径是否一致。")]
    return [Finding(8, "INFO", "INFO",
                    f"声明基准：{benchmark}",
                    "需人工确认可比性与口径一致性（超额同区间/同频率/含成本）。",
                    "选可比基准、统一口径；有风格暴露时补充多因子剥离归因（fix-library 轴8）。")]
