"""月度定投分配逻辑。"""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.utils.schemas import AllocationSuggestion, RiskSignal


class DCAAllocator:
    """基于目标权重偏离生成低频买入建议。"""

    def __init__(self, portfolio_config: dict[str, Any]) -> None:
        self.portfolio_config = portfolio_config
        self.asset_allocation = portfolio_config["asset_allocation"]

    def allocate(
        self,
        target_table: pd.DataFrame,
        current_table: pd.DataFrame,
        risk_map: dict[str, RiskSignal],
        monthly_budget: float,
    ) -> list[AllocationSuggestion]:
        """生成月度建议。"""

        merged = target_table.merge(
            current_table[["symbol", "asset_type", "current_weight"]],
            on=["symbol", "asset_type"],
            how="left",
        )
        merged["current_weight"] = merged["current_weight"].fillna(0.0)

        suggestions: list[AllocationSuggestion] = []
        for asset_type, ratio in {
            "etf": self.asset_allocation["etf_total_weight"],
            "stock": self.asset_allocation["stock_total_weight"],
        }.items():
            group = merged.loc[merged["asset_type"] == asset_type].copy()
            if group.empty:
                continue

            group_budget = monthly_budget * ratio
            group["eligible"] = group["symbol"].map(lambda x: not risk_map.get(x).pause_buy if x in risk_map else True)
            group["gap"] = (group["target_weight"] - group["current_weight"]).clip(lower=0.0)

            eligible = group.loc[group["eligible"]].copy()
            if eligible.empty:
                for _, row in group.iterrows():
                    signal = risk_map.get(row["symbol"])
                    suggestions.append(self._build_suggestion(row, signal, 0.0))
                continue

            total_gap = float(eligible["gap"].sum())
            if total_gap > 0:
                eligible["recommended_amount"] = group_budget * eligible["gap"] / total_gap
            else:
                normalized = eligible["target_weight"] / eligible["target_weight"].sum()
                eligible["recommended_amount"] = group_budget * normalized

            recommended_map = eligible.set_index("symbol")["recommended_amount"].to_dict()
            for _, row in group.iterrows():
                signal = risk_map.get(row["symbol"])
                suggestions.append(self._build_suggestion(row, signal, float(recommended_map.get(row["symbol"], 0.0))))
        return suggestions

    @staticmethod
    def _build_suggestion(row: pd.Series, signal: RiskSignal | None, recommended_amount: float) -> AllocationSuggestion:
        return AllocationSuggestion(
            symbol=row["symbol"],
            asset_type=row["asset_type"],
            target_weight=float(row["target_weight"]),
            current_weight=float(row["current_weight"]),
            recommended_amount=recommended_amount,
            status=signal.status if signal else "GREEN",
            pause_buy=signal.pause_buy if signal else False,
            manual_review=signal.manual_review if signal else False,
            reasons=signal.reasons if signal else [],
            manual_pause_buy=signal.manual_pause_buy if signal else False,
            manual_force_review=signal.manual_force_review if signal else False,
            thesis_broken=signal.thesis_broken if signal else False,
            final_priority_level=signal.final_priority_level if signal else 6,
            final_reason_codes=signal.final_reason_codes if signal else [],
            final_human_readable_action=signal.final_human_readable_action if signal else "正常",
            logic_note=signal.logic_note if signal else "",
        )
