"""回测假设审计探测器注册表。

每个探测器模块暴露 `run(ctx) -> list[Finding]`。ctx 为 audit_cli 构建的
Context（signal/panel/weights/membership/assumptions）。顺序即报告顺序。
"""
from __future__ import annotations

from .execution_timing import run as run_execution_timing
from .cost_model import run as run_cost_model
from .price_limits_suspensions import run as run_price_limits
from .survivorship import run as run_survivorship
from .parameter_freedom import run as run_parameter_freedom
from .data_alignment import run as run_data_alignment
from .turnover_capacity import run as run_turnover_capacity
from .benchmark import run as run_benchmark
from .transparency import run as run_transparency

DETECTORS = [
    (1, "execution_timing", run_execution_timing),
    (2, "cost_model", run_cost_model),
    (3, "price_limits_suspensions", run_price_limits),
    (4, "survivorship", run_survivorship),
    (5, "parameter_freedom", run_parameter_freedom),
    (6, "data_alignment", run_data_alignment),
    (7, "turnover_capacity", run_turnover_capacity),
    (8, "benchmark", run_benchmark),
    (9, "transparency", run_transparency),
]
