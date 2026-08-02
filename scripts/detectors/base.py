"""共享基础：Finding 数据类、输入加载、默认假设、rank IC 工具。

依赖：pandas + numpy（无 scipy）。面板建议长表格式：
  date, symbol, open, high, low, close, volume[, limit_up, limit_down, suspended]
signal / weights 支持宽表（date 索引 + symbol 列）或长表（date, symbol, value）。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, asdict, field

import numpy as np
import pandas as pd

VERDICTS = ("PASS", "WARN", "FAIL", "INFO")
SEVERITIES = ("INFO", "MINOR", "MAJOR", "BLOCKER")

# 九大审计维度（顺序即报告顺序）
AXES = [
    (1, "成交时点与未来函数", "execution_timing"),
    (2, "交易成本", "cost_model"),
    (3, "涨跌停与停牌", "price_limits_suspensions"),
    (4, "幸存者偏差", "survivorship"),
    (5, "参数自由度与多重比较", "parameter_freedom"),
    (6, "数据对齐与复权", "data_alignment"),
    (7, "换手与容量", "turnover_capacity"),
    (8, "基准与超额", "benchmark"),
    (9, "报告透明度", "transparency"),
]
AXIS_NAME = {a: n for a, n, _ in AXES}
AXIS_KEY = {a: k for a, _, k in AXES}

# 判定基线（对齐生态 skill-backtest 标准协议）
DEFAULT_ASSUMPTIONS = {
    "execution": "open_t1",      # open_t1 | close | vwap | 未声明
    "cost_bp": 15,               # 双边成本（bp），生态基线
    "horizon": 5,                # 预测周期（日）
    "notional": 1e7,             # 篮子名义金额（元）
    "top_n": 10,                 # Top 持仓数
    "n_trials": None,            # 试验次数（多重比较）
    "t_years": None,             # 样本年数
    "reported_sharpe": None,     # 报告的年化 Sharpe
    "benchmark": None,           # 基准描述
}


@dataclass
class Finding:
    axis_id: int
    verdict: str
    severity: str
    evidence: str
    impact: str = ""
    fix: str = ""

    def __post_init__(self):
        if self.verdict not in VERDICTS:
            raise ValueError(f"非法 verdict: {self.verdict}")
        if self.severity not in SEVERITIES:
            raise ValueError(f"非法 severity: {self.severity}")

    @property
    def axis_name(self) -> str:
        return AXIS_NAME.get(self.axis_id, str(self.axis_id))

    def to_dict(self) -> dict:
        d = asdict(self)
        d["axis_name"] = self.axis_name
        d["axis_key"] = AXIS_KEY.get(self.axis_id, "")
        return d


def info(axis_id: int, evidence: str) -> Finding:
    """证据不足的标准降级 Finding。"""
    return Finding(axis_id, "INFO", "INFO", evidence)


# ---------- 输入加载 ----------

def _read(path: str) -> pd.DataFrame:
    lower = path.lower()
    if lower.endswith((".csv", ".txt")):
        return pd.read_csv(path)
    if lower.endswith((".parquet", ".pq")):
        return pd.read_parquet(path)
    if lower.endswith((".xlsx", ".xls")):
        return pd.read_excel(path)
    raise ValueError(f"不支持的输入格式: {path}")


def _date_index(df: pd.DataFrame) -> pd.DataFrame:
    """把日期列设为索引：优先名为 date 的列，否则首个未命名列（CSV 写索引未命名时的常见形态）。"""
    df = df.copy()
    first = str(df.columns[0])
    if "date" in df.columns:
        col = "date"
    elif first in ("", "Unnamed: 0", "index", "date"):
        col = df.columns[0]
    else:
        return df
    df[col] = pd.to_datetime(df[col], errors="coerce")
    return df.set_index(col).sort_index()


def load_wide(path: str | None) -> pd.DataFrame | None:
    """signal / weights：宽表（date 索引 + symbol 列）或长表（date, symbol, value）。"""
    if not path or not os.path.exists(path):
        return None
    df = _read(path)
    if "symbol" in df.columns:
        value_col = next((c for c in ("value", "signal", "weight", "ret") if c in df.columns), None)
        if value_col is None:
            raise ValueError(f"长表 {path} 缺少 value/signal/weight 列")
        df = df.pivot(index="date", columns="symbol", values=value_col)
    return _date_index(df).sort_index()


def load_panel(path: str | None) -> pd.DataFrame | None:
    """行情面板：长表（date, symbol, open/high/low/close/volume...）。"""
    if not path or not os.path.exists(path):
        return None
    df = _read(path)
    if "symbol" not in df.columns:
        raise ValueError(f"面板 {path} 必须是长表（含 symbol 列）")
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["date", "symbol"]).reset_index(drop=True)


def load_membership(path: str | None) -> pd.DataFrame | None:
    """历史成分 / 生命周期：长表（date, symbol）。"""
    if not path or not os.path.exists(path):
        return None
    df = _read(path)
    df["date"] = pd.to_datetime(df["date"])
    return df


# ---------- 面板工具 ----------

def panel_wide(panel: pd.DataFrame, field: str) -> pd.DataFrame:
    """面板长表 → 宽表（date 索引 × symbol 列）。"""
    if field not in panel.columns:
        raise KeyError(f"面板缺少字段: {field}")
    return panel.pivot(index="date", columns="symbol", values=field).sort_index()


def one_way_turnover(weights: pd.DataFrame) -> float | None:
    """单边换手：mean_t( sum_s |w_t - w_{t-1}| ) / 2。"""
    if weights is None or weights.shape[0] < 2:
        return None
    diff = weights.diff().abs().sum(axis=1)
    return float(diff.iloc[1:].mean() / 2.0)


def rank_ic(a: pd.Series, b: pd.Series) -> float | None:
    """秩相关（Spearman IC），逐截面；样本过少返回 None。"""
    m = a.notna() & b.notna()
    a, b = a[m], b[m]
    if len(a) < 20:
        return None
    ra, rb = a.rank(), b.rank()
    return float(ra.corr(rb))
