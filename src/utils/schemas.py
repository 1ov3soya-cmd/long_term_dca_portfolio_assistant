"""项目通用数据结构。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import pandas as pd


@dataclass(slots=True)
class Holding:
    """单个持仓。"""

    symbol: str
    asset_type: str
    quantity: int
    avg_cost: float


@dataclass(slots=True)
class RiskSignal:
    """统一后的风险监控结果。"""

    symbol: str
    asset_type: str
    status: str
    reasons: list[str] = field(default_factory=list)
    pause_buy: bool = False
    manual_review: bool = False
    metric_value: float | None = None
    price_status: str = "GREEN"
    price_reasons: list[str] = field(default_factory=list)
    manual_pause_buy: bool = False
    manual_force_review: bool = False
    thesis_broken: bool = False
    logic_reasons: list[str] = field(default_factory=list)
    final_pause_buy: bool = False
    final_force_review: bool = False
    final_priority_level: int = 6
    final_reason_codes: list[str] = field(default_factory=list)
    final_human_readable_action: str = "正常"
    logic_note: str = ""
    effective_from: str | None = None
    updated_at: str | None = None
    updated_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["reasons"] = "；".join(self.reasons)
        data["price_reasons"] = "；".join(self.price_reasons)
        data["logic_reasons"] = "；".join(self.logic_reasons)
        data["final_reason_codes"] = ",".join(self.final_reason_codes)
        return data


@dataclass(slots=True)
class AllocationSuggestion:
    """月度定投建议明细。"""

    symbol: str
    asset_type: str
    target_weight: float
    current_weight: float
    recommended_amount: float
    status: str
    pause_buy: bool
    manual_review: bool
    reasons: list[str] = field(default_factory=list)
    manual_pause_buy: bool = False
    manual_force_review: bool = False
    thesis_broken: bool = False
    final_priority_level: int = 6
    final_reason_codes: list[str] = field(default_factory=list)
    final_human_readable_action: str = "正常"
    logic_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["reasons"] = "；".join(self.reasons)
        data["final_reason_codes"] = ",".join(self.final_reason_codes)
        return data


@dataclass(slots=True)
class MonthlyRecommendation:
    """月度定投建议输出。"""

    as_of_date: pd.Timestamp
    total_budget: float
    etf_budget: float
    stock_budget: float
    suggestions: list[AllocationSuggestion]
    manual_review_items: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame([item.to_dict() for item in self.suggestions])


@dataclass(slots=True)
class BacktestResult:
    """回测结果容器。"""

    equity_curve: pd.DataFrame
    trades: pd.DataFrame
    monthly_records: pd.DataFrame
    risk_records: pd.DataFrame
    metrics: dict[str, float]
