"""月度建议引擎。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.allocator import DCAAllocator
from src.portfolio import PortfolioState
from src.risk_monitor import RiskMonitor
from src.utils.schemas import MonthlyRecommendation


class SignalEngine:
    """组合建议引擎。"""

    def __init__(self, configs: dict[str, dict[str, Any]], project_root: str | Path) -> None:
        self.configs = configs
        self.project_root = Path(project_root)
        manual_cfg = configs.get("universe", {}).get("manual_flags", {})
        manual_flag_file = manual_cfg.get("logic_risk_flag_file")
        thesis_flag_file = manual_cfg.get("thesis_flag_file")
        manual_path = self.project_root / manual_flag_file if manual_flag_file else None
        thesis_path = self.project_root / thesis_flag_file if thesis_flag_file else None
        self.risk_monitor = RiskMonitor(configs["risk"], manual_path, thesis_path)
        self.allocator = DCAAllocator(configs["portfolio"])

    def generate_monthly_recommendation(
        self,
        as_of_date: str | pd.Timestamp,
        histories: dict[str, pd.DataFrame],
        portfolio_state: PortfolioState,
        target_table: pd.DataFrame,
        equity_curve: pd.DataFrame | None = None,
    ) -> dict[str, Any]:
        """生成月度定投建议。"""

        latest_prices = self._latest_prices(histories, as_of_date)
        current_table = portfolio_state.to_frame(latest_prices, target_table)
        asset_risks = self.risk_monitor.evaluate_assets(histories, portfolio_state, target_table, as_of_date)
        portfolio_risk = self.risk_monitor.evaluate_portfolio(equity_curve) if equity_curve is not None else None
        monthly_budget = float(self.configs["portfolio"]["portfolio"]["monthly_budget"])
        suggestions = self.allocator.allocate(target_table, current_table, asset_risks, monthly_budget)

        manual_review_items: list[str] = []
        for signal in asset_risks.values():
            if signal.manual_review or signal.thesis_broken or signal.manual_force_review:
                manual_review_items.append(
                    f"{signal.symbol}: {signal.final_human_readable_action} | 原因: {'；'.join(signal.reasons)}"
                )
        if portfolio_risk and portfolio_risk.manual_review:
            manual_review_items.append(f"组合层: {'；'.join(portfolio_risk.reasons)}")

        recommendation = MonthlyRecommendation(
            as_of_date=pd.Timestamp(as_of_date),
            total_budget=monthly_budget,
            etf_budget=monthly_budget * float(self.configs["portfolio"]["asset_allocation"]["etf_total_weight"]),
            stock_budget=monthly_budget * float(self.configs["portfolio"]["asset_allocation"]["stock_total_weight"]),
            suggestions=suggestions,
            manual_review_items=manual_review_items,
            notes=[
                "本建议仅用于人工确认，不接自动下单。",
                "人工逻辑红线与价格红线会统一合并，暂停新增优先于正常定投。",
                "当前版本不自动卖出，卖出仍需人工复核后执行。",
            ],
        )

        risk_frame = pd.DataFrame([item.to_dict() for item in asset_risks.values()])
        return {
            "recommendation": recommendation,
            "current_table": current_table,
            "risk_table": risk_frame,
            "portfolio_risk": portfolio_risk,
            "latest_prices": latest_prices,
        }

    @staticmethod
    def _latest_prices(histories: dict[str, pd.DataFrame], as_of_date: str | pd.Timestamp) -> dict[str, float]:
        prices: dict[str, float] = {}
        cutoff = pd.Timestamp(as_of_date)
        for symbol, frame in histories.items():
            if frame.empty:
                prices[symbol] = 0.0
                continue
            sliced = frame.loc[frame["date"] <= cutoff]
            prices[symbol] = float(sliced["close"].iloc[-1]) if not sliced.empty else 0.0
        return prices
