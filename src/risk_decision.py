"""价格红线与人工逻辑红线的统一合并层。"""

from __future__ import annotations

from typing import Any

from src.manual_risk_manager import ManualRiskFlag
from src.utils.schemas import RiskSignal


class RiskDecisionMerger:
    """输出统一的最终风险动作建议。"""

    def __init__(self, risk_config: dict[str, Any]) -> None:
        self.manual_logic = risk_config.get("manual_logic", {})
        self.priority_levels = self.manual_logic.get(
            "priority_levels",
            {
                "thesis_broken": 1,
                "manual_force_review": 2,
                "manual_pause_buy": 3,
                "price_red": 4,
                "price_yellow": 5,
                "green": 6,
            },
        )
        self.actions = self.manual_logic.get(
            "actions",
            {
                "thesis_broken": "停止新增，最高优先级人工处理",
                "manual_force_review": "暂停新增，强制人工复核",
                "manual_pause_buy": "暂停新增，等待人工解除",
                "price_red": "价格 RED，强制人工复核",
                "price_yellow": "价格 YELLOW，暂停新增并人工复核",
                "green": "正常",
            },
        )

    def merge(self, price_signal: RiskSignal, manual_flag: ManualRiskFlag | None) -> RiskSignal:
        """合并价格与人工逻辑红线。"""

        manual_pause_buy = bool(manual_flag.manual_pause_buy) if manual_flag else False
        manual_force_review = bool(manual_flag.manual_force_review) if manual_flag else False
        thesis_broken = bool(manual_flag.thesis_broken) if manual_flag else False
        logic_note = manual_flag.note if manual_flag else ""
        logic_reasons: list[str] = []
        reason_codes: list[str] = []

        if thesis_broken:
            logic_reasons.append("人工标记 thesis_broken=true")
            reason_codes.append("thesis_broken")
        if manual_force_review:
            logic_reasons.append("人工标记 manual_force_review=true")
            reason_codes.append("manual_force_review")
        if manual_pause_buy:
            logic_reasons.append("人工标记 manual_pause_buy=true")
            reason_codes.append("manual_pause_buy")
        if price_signal.status == "RED":
            reason_codes.append("price_red")
        elif price_signal.status == "YELLOW":
            reason_codes.append("price_yellow")
        if not reason_codes:
            reason_codes.append("green")

        primary_code = min(reason_codes, key=lambda code: self.priority_levels.get(code, 999))
        final_pause_buy = bool(price_signal.pause_buy)
        final_force_review = bool(price_signal.manual_review)
        final_status = price_signal.status

        if thesis_broken:
            final_status = "RED"
            final_pause_buy = bool(self.manual_logic.get("thesis_broken_pause_buy", True))
            final_force_review = bool(self.manual_logic.get("thesis_broken_force_review", True))
        elif manual_force_review:
            final_status = "RED"
            final_force_review = True
            if bool(self.manual_logic.get("manual_force_review_pause_buy", True)):
                final_pause_buy = True
        elif manual_pause_buy:
            final_pause_buy = True
            if final_status == "GREEN":
                final_status = "YELLOW"

        merged_reasons = logic_reasons + list(price_signal.reasons)
        return RiskSignal(
            symbol=price_signal.symbol,
            asset_type=price_signal.asset_type,
            status=final_status,
            reasons=merged_reasons,
            pause_buy=final_pause_buy,
            manual_review=final_force_review,
            metric_value=price_signal.metric_value,
            price_status=price_signal.status,
            price_reasons=list(price_signal.reasons),
            manual_pause_buy=manual_pause_buy,
            manual_force_review=manual_force_review,
            thesis_broken=thesis_broken,
            logic_reasons=logic_reasons,
            final_pause_buy=final_pause_buy,
            final_force_review=final_force_review,
            final_priority_level=int(self.priority_levels.get(primary_code, 999)),
            final_reason_codes=sorted(reason_codes, key=lambda code: self.priority_levels.get(code, 999)),
            final_human_readable_action=str(self.actions.get(primary_code, "正常")),
            logic_note=logic_note,
            effective_from=manual_flag.effective_from if manual_flag else None,
            updated_at=manual_flag.updated_at if manual_flag else None,
            updated_by=manual_flag.updated_by if manual_flag else None,
        )
