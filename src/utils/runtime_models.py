"""真实数据模式所需的数据结构。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import pandas as pd


@dataclass(slots=True)
class DataDiagnostic:
    """单个标的的数据质量诊断。"""

    symbol: str
    asset_type: str
    provider: str
    source_api: str
    adjustment_mode: str
    cache_variant: str
    rows: int
    start_date: str | None
    end_date: str | None
    sorted_ok: bool
    duplicate_dates: int
    missing_required_rows: int
    raw_columns: list[str]
    standardized_columns: list[str]
    fallback_used: bool = False
    cache_hit: bool = False
    latest_update: str | None = None
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["raw_columns"] = ",".join(self.raw_columns)
        data["standardized_columns"] = ",".join(self.standardized_columns)
        return data


@dataclass(slots=True)
class MarketDataBundle:
    """数据加载结果。"""

    histories: dict[str, pd.DataFrame]
    diagnostics: pd.DataFrame
    calendar: list[pd.Timestamp]
    metadata: dict[str, Any]


@dataclass(slots=True)
class ExtendedBacktestResult:
    """增强版回测结果。"""

    equity_curve: pd.DataFrame
    trades: pd.DataFrame
    monthly_records: pd.DataFrame
    risk_records: pd.DataFrame
    metrics: dict[str, float]
    unfilled_orders: pd.DataFrame = field(default_factory=pd.DataFrame)
    recommendation_records: pd.DataFrame = field(default_factory=pd.DataFrame)
    portfolio_snapshots: pd.DataFrame = field(default_factory=pd.DataFrame)
    metadata: dict[str, Any] = field(default_factory=dict)
