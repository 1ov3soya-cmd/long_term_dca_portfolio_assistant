"""风险监控模块。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.indicators import current_drawdown_from_high, drawdown_from_high, moving_average
from src.manual_risk_manager import ManualRiskFlagManager
from src.portfolio import PortfolioState
from src.risk_decision import RiskDecisionMerger
from src.utils.dates import clamp_history
from src.utils.schemas import RiskSignal


class RiskMonitor:
    """ETF / 股票 / 组合三级风险监控。"""

    def __init__(
        self,
        risk_config: dict[str, Any],
        manual_flag_path: str | Path | None = None,
        thesis_flag_path: str | Path | None = None,
    ) -> None:
        self.risk_config = risk_config
        self.manual_flag_manager = ManualRiskFlagManager(manual_flag_path, thesis_flag_path)
        self.decision_merger = RiskDecisionMerger(risk_config)

    def evaluate_assets(
        self,
        histories: dict[str, pd.DataFrame],
        portfolio_state: PortfolioState,
        target_table: pd.DataFrame,
        as_of_date: str | pd.Timestamp,
    ) -> dict[str, RiskSignal]:
        """评估所有标的的最终风险状态。"""

        active_flags = self.manual_flag_manager.load_active_flags(as_of_date)
        result: dict[str, RiskSignal] = {}

        for _, row in target_table.iterrows():
            symbol = row["symbol"]
            asset_type = row["asset_type"]
            history = histories.get(symbol, pd.DataFrame())
            sliced = clamp_history(history, as_of_date) if not history.empty else pd.DataFrame()
            holding = portfolio_state.get_holding(symbol)

            if sliced.empty:
                price_signal = RiskSignal(
                    symbol=symbol,
                    asset_type=asset_type,
                    status="RED",
                    reasons=["缺少可用行情，需人工复核"],
                    pause_buy=True,
                    manual_review=True,
                )
            elif asset_type == "etf":
                price_signal = self._evaluate_etf(symbol, sliced)
            else:
                avg_cost = holding.avg_cost if holding else 0.0
                price_signal = self._evaluate_stock(symbol, sliced, avg_cost)

            result[symbol] = self.decision_merger.merge(price_signal, active_flags.get(symbol))
        return result

    def evaluate_portfolio(self, equity_curve: pd.DataFrame) -> RiskSignal:
        """评估组合层风险。"""

        if equity_curve.empty or "unit_nav" not in equity_curve.columns:
            return RiskSignal(
                symbol="PORTFOLIO",
                asset_type="portfolio",
                status="GREEN",
                reasons=["组合净值序列为空，暂不触发组合红线"],
                final_human_readable_action="正常",
            )

        current_dd = float(drawdown_from_high(equity_curve["unit_nav"]).iloc[-1])
        threshold = float(self.risk_config["portfolio"]["red_max_drawdown"])
        if current_dd >= threshold:
            return RiskSignal(
                symbol="PORTFOLIO",
                asset_type="portfolio",
                status="RED",
                reasons=[f"组合当前回撤 {current_dd:.2%} 超过阈值 {threshold:.2%}"],
                pause_buy=False,
                manual_review=True,
                metric_value=current_dd,
                price_status="RED",
                price_reasons=[f"组合当前回撤 {current_dd:.2%} 超过阈值 {threshold:.2%}"],
                final_force_review=True,
                final_priority_level=4,
                final_reason_codes=["portfolio_red"],
                final_human_readable_action="组合层强制人工复核",
            )

        return RiskSignal(
            symbol="PORTFOLIO",
            asset_type="portfolio",
            status="GREEN",
            reasons=[f"组合当前回撤 {current_dd:.2%} 未超过阈值"],
            metric_value=current_dd,
            price_status="GREEN",
            price_reasons=[f"组合当前回撤 {current_dd:.2%} 未超过阈值"],
            final_priority_level=6,
            final_reason_codes=["green"],
            final_human_readable_action="正常",
        )

    def validate_manual_flags(self, target_table: pd.DataFrame) -> dict[str, Any]:
        """校验人工逻辑红线配置。"""

        return self.manual_flag_manager.validate(target_table)

    def _evaluate_etf(self, symbol: str, history: pd.DataFrame) -> RiskSignal:
        series = history["close"].astype(float)
        dd = current_drawdown_from_high(series)
        risk_root = self.risk_config["risk"]
        etf_cfg = self.risk_config["etf"]
        ma_window = int(risk_root["moving_average_window"])
        weakness_days = int(etf_cfg["weakness_days"])
        ma_line = moving_average(series, ma_window)
        weakness = False
        if len(series) >= weakness_days:
            weakness = bool((series.tail(weakness_days) < ma_line.tail(weakness_days)).all())

        if dd >= float(etf_cfg["red_drawdown_from_high"]):
            reasons = [f"相对参考高点回撤 {dd:.2%}，超过 RED 阈值"]
            return RiskSignal(
                symbol=symbol,
                asset_type="etf",
                status="RED",
                reasons=reasons,
                pause_buy=True,
                manual_review=True,
                metric_value=dd,
                price_status="RED",
                price_reasons=reasons,
                final_priority_level=4,
                final_reason_codes=["price_red"],
                final_human_readable_action="价格 RED，强制人工复核",
            )

        if dd >= float(etf_cfg["yellow_drawdown_from_high"]) or weakness:
            reasons = [f"相对参考高点回撤 {dd:.2%}，进入 YELLOW 区域"]
            if weakness:
                reasons.append("跌破长期均线且持续弱势")
            return RiskSignal(
                symbol=symbol,
                asset_type="etf",
                status="YELLOW",
                reasons=reasons,
                pause_buy=True,
                manual_review=True,
                metric_value=dd,
                price_status="YELLOW",
                price_reasons=reasons,
                final_priority_level=5,
                final_reason_codes=["price_yellow"],
                final_human_readable_action="价格 YELLOW，暂停新增并人工复核",
            )

        reasons = ["ETF 风险状态正常"]
        return RiskSignal(
            symbol=symbol,
            asset_type="etf",
            status="GREEN",
            reasons=reasons,
            pause_buy=False,
            manual_review=False,
            metric_value=dd,
            price_status="GREEN",
            price_reasons=reasons,
            final_priority_level=6,
            final_reason_codes=["green"],
            final_human_readable_action="正常",
        )

    def _evaluate_stock(self, symbol: str, history: pd.DataFrame, avg_cost: float) -> RiskSignal:
        latest_close = float(history["close"].iloc[-1])
        stock_cfg = self.risk_config["stock"]

        if avg_cost <= 0:
            reasons = ["尚无持仓成本，允许按计划定投"]
            return RiskSignal(
                symbol=symbol,
                asset_type="stock",
                status="GREEN",
                reasons=reasons,
                price_status="GREEN",
                price_reasons=reasons,
                final_priority_level=6,
                final_reason_codes=["green"],
                final_human_readable_action="正常",
            )

        drawdown = max((avg_cost - latest_close) / avg_cost, 0.0)
        if drawdown >= float(stock_cfg["red_drawdown_from_cost"]):
            reasons = [f"相对成本回撤 {drawdown:.2%}，超过 RED 阈值"]
            return RiskSignal(
                symbol=symbol,
                asset_type="stock",
                status="RED",
                reasons=reasons,
                pause_buy=True,
                manual_review=True,
                metric_value=drawdown,
                price_status="RED",
                price_reasons=reasons,
                final_priority_level=4,
                final_reason_codes=["price_red"],
                final_human_readable_action="价格 RED，强制人工复核",
            )

        if drawdown >= float(stock_cfg["yellow_drawdown_from_cost"]):
            reasons = [f"相对成本回撤 {drawdown:.2%}，进入 YELLOW 区域"]
            return RiskSignal(
                symbol=symbol,
                asset_type="stock",
                status="YELLOW",
                reasons=reasons,
                pause_buy=True,
                manual_review=True,
                metric_value=drawdown,
                price_status="YELLOW",
                price_reasons=reasons,
                final_priority_level=5,
                final_reason_codes=["price_yellow"],
                final_human_readable_action="价格 YELLOW，暂停新增并人工复核",
            )

        reasons = ["股票风险状态正常"]
        return RiskSignal(
            symbol=symbol,
            asset_type="stock",
            status="GREEN",
            reasons=reasons,
            price_status="GREEN",
            price_reasons=reasons,
            final_priority_level=6,
            final_reason_codes=["green"],
            final_human_readable_action="正常",
        )
