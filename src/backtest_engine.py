"""低频 MVP 回测器。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.indicators import annualized_return, annualized_volatility, max_drawdown
from src.portfolio import PortfolioState
from src.signal_engine import SignalEngine
from src.utils.calendar_utils import (
    first_trading_day_each_month,
    last_trading_day_each_month,
    last_trading_day_each_week,
)
from src.utils.exceptions import BacktestError
from src.utils.logger import get_logger
from src.utils.runtime_models import ExtendedBacktestResult, MarketDataBundle
from src.utils.schemas import AllocationSuggestion


class MVPBacktestEngine:
    """面向长期定投场景的 MVP 回测器。

    设计边界：
    - 只模拟月度定投与周度风险巡检。
    - 不新增自动卖出，不把红线规则改造成高频止损。
    - 所有卖出相关逻辑继续保持禁用，避免偏离“长期定投 + 人工复核”定位。
    """

    def __init__(self, configs: dict[str, dict[str, Any]], project_root: str | Path) -> None:
        self.configs = configs
        self.project_root = Path(project_root)
        self.logger = get_logger(self.__class__.__name__, configs["app"]["runtime"]["log_level"])
        self.signal_engine = SignalEngine(configs, project_root)

    def run(
        self,
        histories: dict[str, pd.DataFrame],
        target_table: pd.DataFrame,
        data_bundle: MarketDataBundle | None = None,
    ) -> ExtendedBacktestResult:
        """运行低频定投回测。"""

        backtest_cfg = self.configs["backtest"]["backtest"]
        benchmark_symbol = self.configs["universe"]["universe"]["benchmark_symbol"]
        benchmark = histories.get(benchmark_symbol)
        if benchmark is None or benchmark.empty:
            raise BacktestError(f"基准标的缺少历史数据: {benchmark_symbol}")

        start_date = pd.Timestamp(backtest_cfg["start_date"])
        end_date = pd.Timestamp(backtest_cfg["end_date"])
        if data_bundle is not None and data_bundle.calendar:
            calendar = [
                pd.Timestamp(item).normalize()
                for item in data_bundle.calendar
                if start_date <= pd.Timestamp(item) <= end_date
            ]
        else:
            calendar = (
                benchmark.loc[
                    (benchmark["date"] >= start_date) & (benchmark["date"] <= end_date),
                    "date",
                ]
                .drop_duplicates()
                .sort_values()
                .dt.normalize()
                .tolist()
            )
        if not calendar:
            raise BacktestError("回测日历为空，请检查历史行情与回测区间。")

        monthly_rule = backtest_cfg.get(
            "execution_rule",
            self.configs.get("app", {}).get("schedule", {}).get("monthly_invest_day_rule", "first_trading_day"),
        )
        if monthly_rule == "last_trading_day":
            invest_dates = set(last_trading_day_each_month(calendar))
        else:
            invest_dates = set(first_trading_day_each_month(calendar))
        weekly_risk_dates = set(last_trading_day_each_week(calendar))

        portfolio = PortfolioState(cash=float(backtest_cfg["initial_cash"]))
        total_contribution = float(backtest_cfg["initial_cash"])

        equity_rows: list[dict[str, Any]] = []
        trade_rows: list[dict[str, Any]] = []
        monthly_rows: list[dict[str, Any]] = []
        risk_rows: list[dict[str, Any]] = []
        unfilled_rows: list[dict[str, Any]] = []
        recommendation_rows: list[dict[str, Any]] = []
        snapshot_rows: list[dict[str, Any]] = []

        for trade_date in calendar:
            current_prices = self._prices_for_valuation(histories, trade_date)

            if trade_date in invest_dates:
                monthly_budget = float(backtest_cfg["monthly_budget"])
                portfolio.add_cash(monthly_budget)
                total_contribution += monthly_budget

                signal_payload = self.signal_engine.generate_monthly_recommendation(
                    as_of_date=trade_date,
                    histories=histories,
                    portfolio_state=portfolio,
                    target_table=target_table,
                    equity_curve=pd.DataFrame(equity_rows),
                )
                recommendation = signal_payload["recommendation"]
                risk_table = signal_payload["risk_table"]

                for suggestion in recommendation.suggestions:
                    recommendation_rows.append(
                        {
                            "date": trade_date,
                            "month": trade_date.strftime("%Y-%m"),
                            **suggestion.to_dict(),
                        }
                    )

                invested_amount = 0.0
                today_unfilled = 0
                for suggestion in recommendation.suggestions:
                    trade, unfilled = self._execute_buy_if_possible(
                        trade_date=trade_date,
                        suggestion=suggestion,
                        portfolio=portfolio,
                        histories=histories,
                    )
                    if trade is not None:
                        trade_rows.append(trade)
                        invested_amount += float(trade["total_cash_out"])
                    if unfilled is not None:
                        unfilled_rows.append(unfilled)
                        today_unfilled += 1

                monthly_rows.append(
                    {
                        "date": trade_date,
                        "month": trade_date.strftime("%Y-%m"),
                        "theoretical_trade_day": trade_date.strftime("%Y-%m-%d"),
                        "actual_trade_day": trade_date.strftime("%Y-%m-%d"),
                        "monthly_budget": monthly_budget,
                        "invested_amount": invested_amount,
                        "cash_after_trade": portfolio.cash,
                        "manual_review_count": len(recommendation.manual_review_items),
                        "unfilled_count": today_unfilled,
                    }
                )
                snapshot_rows.extend(
                    self._build_snapshot_rows(
                        trade_date=trade_date,
                        portfolio=portfolio,
                        histories=histories,
                        target_table=target_table,
                    )
                )
                for _, row in risk_table.iterrows():
                    risk_record = row.to_dict()
                    risk_record["date"] = trade_date
                    risk_record["check_type"] = "monthly_invest_review"
                    risk_rows.append(risk_record)

            elif trade_date in weekly_risk_dates:
                risk_payload = self.signal_engine.generate_monthly_recommendation(
                    as_of_date=trade_date,
                    histories=histories,
                    portfolio_state=portfolio,
                    target_table=target_table,
                    equity_curve=pd.DataFrame(equity_rows),
                )
                for _, row in risk_payload["risk_table"].iterrows():
                    risk_record = row.to_dict()
                    risk_record["date"] = trade_date
                    risk_record["check_type"] = "weekly_risk_check"
                    risk_rows.append(risk_record)

            total_value = portfolio.total_value(current_prices)
            unit_nav = total_value / total_contribution if total_contribution > 0 else 1.0
            equity_rows.append(
                {
                    "date": trade_date,
                    "cash": portfolio.cash,
                    "portfolio_value": total_value,
                    "cumulative_contribution": total_contribution,
                    "unit_nav": unit_nav,
                }
            )

        equity_curve = pd.DataFrame(equity_rows)
        equity_curve["drawdown"] = (
            (equity_curve["unit_nav"].cummax() - equity_curve["unit_nav"])
            / equity_curve["unit_nav"].cummax()
        )

        risk_records = pd.DataFrame(risk_rows)
        monthly_records = pd.DataFrame(monthly_rows)
        weekly_actual: list[str] = []
        if not risk_records.empty and "check_type" in risk_records.columns:
            weekly_actual = (
                pd.to_datetime(
                    risk_records.loc[risk_records["check_type"] == "weekly_risk_check", "date"]
                )
                .dt.strftime("%Y-%m-%d")
                .drop_duplicates()
                .tolist()
            )

        metrics = self._build_metrics(equity_curve)
        metadata = {
            "data_mode": data_bundle.metadata.get("data_mode") if data_bundle else "unknown",
            "provider": data_bundle.metadata.get("provider") if data_bundle else "unknown",
            "source_api": data_bundle.metadata.get("source_api") if data_bundle else "unknown",
            "adjustment_mode": data_bundle.metadata.get("adjustment_mode") if data_bundle else "unknown",
            "execution_rule": monthly_rule,
            "latest_data_date": data_bundle.metadata.get("latest_data_date") if data_bundle else None,
            "actual_monthly_trade_days": monthly_records["actual_trade_day"].tolist() if not monthly_records.empty else [],
            "actual_weekly_risk_days": weekly_actual,
        }
        return ExtendedBacktestResult(
            equity_curve=equity_curve,
            trades=pd.DataFrame(trade_rows),
            monthly_records=monthly_records,
            risk_records=risk_records,
            metrics=metrics,
            unfilled_orders=pd.DataFrame(unfilled_rows),
            recommendation_records=pd.DataFrame(recommendation_rows),
            portfolio_snapshots=pd.DataFrame(snapshot_rows),
            metadata=metadata,
        )

    def _prices_for_valuation(
        self,
        histories: dict[str, pd.DataFrame],
        trade_date: pd.Timestamp,
    ) -> dict[str, float]:
        """按日期提取估值价格。"""

        prices: dict[str, float] = {}
        for symbol, frame in histories.items():
            sliced = frame.loc[frame["date"] <= trade_date]
            prices[symbol] = float(sliced["close"].iloc[-1]) if not sliced.empty else 0.0
        return prices

    def _execute_buy_if_possible(
        self,
        trade_date: pd.Timestamp,
        suggestion: AllocationSuggestion,
        portfolio: PortfolioState,
        histories: dict[str, pd.DataFrame],
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """在允许条件下执行买入。

        说明：
        - 本阶段只允许买入，不实现自动卖出。
        - 触发 YELLOW / RED 时默认暂停新增，并记录未成交原因。
        """

        base_unfilled = {
            "date": trade_date,
            "symbol": suggestion.symbol,
            "asset_type": suggestion.asset_type,
            "recommended_amount": suggestion.recommended_amount,
            "status": suggestion.status,
            "final_human_readable_action": suggestion.final_human_readable_action,
            "final_reason_codes": ",".join(suggestion.final_reason_codes),
            "logic_note": suggestion.logic_note,
        }
        if suggestion.recommended_amount <= 0:
            return None, {**base_unfilled, "reason": "recommended_amount_zero"}
        if suggestion.pause_buy:
            return None, {**base_unfilled, "reason": "paused_by_risk_rule", "reason_detail": suggestion.final_human_readable_action}

        frame = histories.get(suggestion.symbol, pd.DataFrame())
        row = frame.loc[frame["date"] == trade_date]
        if row.empty:
            return None, {**base_unfilled, "reason": "missing_market_data_on_trade_day"}

        close_price = float(row["close"].iloc[0])
        if close_price <= 0:
            return None, {**base_unfilled, "reason": "invalid_close_price"}

        cost_cfg = self.configs["backtest"]["transaction_cost"][suggestion.asset_type]
        lot_size = int(self.configs["backtest"]["trading_rules"]["min_trade_lot"])
        slippage = float(cost_cfg["slippage"])
        commission_rate = float(cost_cfg["buy_commission"])
        effective_unit_cash = close_price * (1 + slippage + commission_rate)

        quantity = int(suggestion.recommended_amount / effective_unit_cash)
        quantity = (quantity // lot_size) * lot_size
        if quantity < lot_size:
            return None, {**base_unfilled, "reason": "below_min_trade_lot"}

        commission = close_price * quantity * commission_rate
        slippage_cost = close_price * quantity * slippage
        total_cash_out = close_price * quantity + commission + slippage_cost

        while quantity >= lot_size and total_cash_out > portfolio.cash:
            quantity -= lot_size
            commission = close_price * quantity * commission_rate
            slippage_cost = close_price * quantity * slippage
            total_cash_out = close_price * quantity + commission + slippage_cost

        if quantity < lot_size or total_cash_out > portfolio.cash:
            return None, {**base_unfilled, "reason": "insufficient_cash_after_rounding"}

        portfolio.apply_buy(
            symbol=suggestion.symbol,
            asset_type=suggestion.asset_type,
            quantity=quantity,
            total_cash_out=total_cash_out,
        )
        return {
            "date": trade_date,
            "symbol": suggestion.symbol,
            "asset_type": suggestion.asset_type,
            "action": "BUY",
            "price": close_price,
            "quantity": quantity,
            "trade_value": close_price * quantity,
            "commission": commission,
            "slippage_cost": slippage_cost,
            "total_cash_out": total_cash_out,
            "status": suggestion.status,
            "final_human_readable_action": suggestion.final_human_readable_action,
            "final_reason_codes": ",".join(suggestion.final_reason_codes),
            "logic_note": suggestion.logic_note,
            "note": "低频定投买入",
        }, None

    def _build_snapshot_rows(
        self,
        trade_date: pd.Timestamp,
        portfolio: PortfolioState,
        histories: dict[str, pd.DataFrame],
        target_table: pd.DataFrame,
    ) -> list[dict[str, Any]]:
        """记录月度执行日后的组合快照。"""

        latest_prices = self._prices_for_valuation(histories, trade_date)
        current_table = portfolio.to_frame(latest_prices, target_table)
        total_value = portfolio.total_value(latest_prices)
        snapshot_rows: list[dict[str, Any]] = []
        for _, row in current_table.iterrows():
            snapshot_rows.append(
                {
                    "date": trade_date,
                    "symbol": row["symbol"],
                    "asset_type": row["asset_type"],
                    "market_value": float(row.get("market_value", 0.0)),
                    "current_weight": float(row.get("current_weight", 0.0)),
                    "target_weight": float(row.get("target_weight", 0.0)),
                    "weight_gap": float(row.get("weight_gap", 0.0)),
                    "total_value": total_value,
                    "cash": portfolio.cash,
                }
            )
        return snapshot_rows

    @staticmethod
    def _build_metrics(equity_curve: pd.DataFrame) -> dict[str, float]:
        """计算核心绩效指标。"""

        nav_series = equity_curve["unit_nav"]
        return {
            "ending_value": float(equity_curve["portfolio_value"].iloc[-1]),
            "total_contribution": float(equity_curve["cumulative_contribution"].iloc[-1]),
            "final_unit_nav": float(nav_series.iloc[-1]),
            "total_return": float(nav_series.iloc[-1] - 1),
            "annualized_return": annualized_return(nav_series),
            "annualized_volatility": annualized_volatility(nav_series),
            "max_drawdown": max_drawdown(nav_series),
        }
