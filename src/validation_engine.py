"""数据验收与回测一致性检查。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.calendar_utils import first_trading_day_each_month, last_trading_day_each_week
from src.utils.logger import get_logger
from src.utils.runtime_models import ExtendedBacktestResult, MarketDataBundle


class ValidationEngine:
    """负责输出 data validation 与 backtest consistency 报告。"""

    UNFILLED_CATEGORIES = [
        "缺少数据",
        "非交易日",
        "资金不足整手",
        "红线暂停",
        "标的在当期不可用",
        "其他",
    ]

    def __init__(self, configs: dict[str, dict[str, Any]], project_root: str | Path) -> None:
        self.configs = configs
        self.project_root = Path(project_root)
        self.logger = get_logger(self.__class__.__name__, configs["app"]["runtime"]["log_level"])

    def validate_data(
        self,
        data_bundle: MarketDataBundle,
        target_table: pd.DataFrame,
        start_date: str,
        end_date: str,
    ) -> dict[str, Any]:
        """执行数据验收并落盘。"""

        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)
        calendar = [item for item in data_bundle.calendar if start_ts <= pd.Timestamp(item) <= end_ts]
        total_calendar_days = len(calendar)

        summary_rows: list[dict[str, Any]] = []
        diagnostics_payload: list[dict[str, Any]] = []
        coverage_gaps: list[dict[str, Any]] = []

        for _, item in target_table.iterrows():
            symbol = item["symbol"]
            asset_type = item["asset_type"]
            history = data_bundle.histories.get(symbol, pd.DataFrame()).copy()
            history = history.loc[(history["date"] >= start_ts) & (history["date"] <= end_ts)].copy() if not history.empty else history
            diagnostic_row = self._diagnostic_row(data_bundle.diagnostics, symbol, asset_type)
            summary, details = self._build_data_quality_rows(
                symbol=symbol,
                asset_type=asset_type,
                history=history,
                calendar=calendar,
                total_calendar_days=total_calendar_days,
                diagnostic_row=diagnostic_row,
                start_ts=start_ts,
                end_ts=end_ts,
            )
            summary_rows.append(summary)
            diagnostics_payload.append(details)
            if summary["coverage_start_ok"] is False:
                coverage_gaps.append(
                    {
                        "symbol": symbol,
                        "asset_type": asset_type,
                        "missing_start_period": summary["missing_start_period"],
                        "current_handling": "标的在该时段不可用时，回测保留现金，直到出现可交易数据。",
                    }
                )

        alignment_table = self._build_alignment_table(data_bundle.histories, target_table, calendar)
        summary_df = pd.DataFrame(summary_rows)
        diagnostics_json = {
            "metadata": {
                "data_mode": data_bundle.metadata.get("data_mode"),
                "provider": data_bundle.metadata.get("provider"),
                "source_api": data_bundle.metadata.get("source_api"),
                "adjustment_mode": data_bundle.metadata.get("adjustment_mode"),
                "latest_data_date": data_bundle.metadata.get("latest_data_date"),
                "data_updated_at": data_bundle.metadata.get("data_updated_at"),
                "start_date": start_date,
                "end_date": end_date,
                "calendar_days": total_calendar_days,
            },
            "symbol_diagnostics": diagnostics_payload,
            "alignment": alignment_table.to_dict(orient="records"),
            "coverage_gaps": coverage_gaps,
            "adjustment_note": {
                "mode": data_bundle.metadata.get("adjustment_mode"),
                "adj_close_definition": "adj_close 当前等于所选复权模式下的 close。",
                "cache_isolation": "缓存按复权模式隔离保存，不同复权模式不能直接横向对比。",
            },
        }

        report_md = self._render_data_validation_markdown(summary_df, alignment_table, coverage_gaps, diagnostics_json)
        output_dir = self.project_root / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        md_path = output_dir / "data_validation_report.md"
        csv_path = output_dir / "data_validation_summary.csv"
        json_path = output_dir / "data_validation_diagnostics.json"
        summary_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        json_path.write_text(json.dumps(diagnostics_json, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        md_path.write_text(report_md, encoding="utf-8")

        self.logger.info("数据验收报告已输出: %s", md_path)
        return {
            "summary": summary_df,
            "alignment": alignment_table,
            "paths": {"markdown": md_path, "csv": csv_path, "json": json_path},
        }

    def validate_backtest(
        self,
        backtest_result: ExtendedBacktestResult,
        data_bundle: MarketDataBundle,
        target_table: pd.DataFrame,
    ) -> dict[str, Any]:
        """执行回测一致性检查并落盘。"""

        start_date = self.configs["backtest"]["backtest"]["start_date"]
        end_date = self.configs["backtest"]["backtest"]["end_date"]
        calendar = [
            item
            for item in data_bundle.calendar
            if pd.Timestamp(start_date) <= pd.Timestamp(item) <= pd.Timestamp(end_date)
        ]
        expected_monthly = first_trading_day_each_month(calendar)
        expected_weekly = last_trading_day_each_week(calendar)
        actual_monthly = list(pd.to_datetime(backtest_result.monthly_records["date"]).dt.normalize()) if not backtest_result.monthly_records.empty else []
        if not backtest_result.risk_records.empty and "check_type" in backtest_result.risk_records.columns:
            actual_weekly = list(
                pd.to_datetime(
                    backtest_result.risk_records.loc[
                        backtest_result.risk_records["check_type"] == "weekly_risk_check",
                        "date",
                    ]
                )
                .dt.normalize()
                .drop_duplicates()
            )
        else:
            actual_weekly = [pd.Timestamp(item).normalize() for item in backtest_result.metadata.get("actual_weekly_risk_days", [])]

        monthly_check = self._build_monthly_execution_check(expected_monthly, actual_monthly)
        weekly_check = self._build_weekly_execution_check(expected_weekly, actual_weekly)
        allocation_check = self._build_allocation_check(backtest_result)
        redline_stats = self._build_redline_stats(backtest_result)
        unfilled_summary = self._build_unfilled_summary(backtest_result, data_bundle)
        weight_deviation = self._build_weight_deviation(backtest_result, data_bundle, target_table)
        config_summary = self._build_backtest_config_summary(data_bundle)

        summary_rows = []
        summary_rows.extend(self._section_rows("monthly_execution", monthly_check))
        summary_rows.extend(self._section_rows("weekly_execution", weekly_check))
        summary_rows.extend(self._section_rows("allocation", allocation_check))
        summary_rows.extend(self._section_rows("redline", redline_stats))
        summary_rows.extend(self._section_rows("unfilled", unfilled_summary))
        summary_rows.extend(self._section_rows("weight_deviation", weight_deviation))

        summary_df = pd.DataFrame(summary_rows)
        report_md = self._render_backtest_validation_markdown(
            monthly_check=monthly_check,
            weekly_check=weekly_check,
            allocation_check=allocation_check,
            redline_stats=redline_stats,
            unfilled_summary=unfilled_summary,
            weight_deviation=weight_deviation,
            config_summary=config_summary,
        )

        output_dir = self.project_root / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        md_path = output_dir / "backtest_validation_report.md"
        csv_path = output_dir / "backtest_validation_summary.csv"
        summary_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        md_path.write_text(report_md, encoding="utf-8")

        self.logger.info("回测一致性报告已输出: %s", md_path)
        return {
            "monthly_check": monthly_check,
            "weekly_check": weekly_check,
            "allocation_check": allocation_check,
            "redline_stats": redline_stats,
            "unfilled_summary": unfilled_summary,
            "weight_deviation": weight_deviation,
            "config_summary": config_summary,
            "paths": {"markdown": md_path, "csv": csv_path},
        }

    def _build_data_quality_rows(
        self,
        symbol: str,
        asset_type: str,
        history: pd.DataFrame,
        calendar: list[pd.Timestamp],
        total_calendar_days: int,
        diagnostic_row: pd.Series,
        start_ts: pd.Timestamp,
        end_ts: pd.Timestamp,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        coverage_start = pd.Timestamp(calendar[0]).normalize() if calendar else start_ts
        provider = diagnostic_row.get("provider", "")
        source_api = diagnostic_row.get("source_api", "")
        adjustment_mode = diagnostic_row.get("adjustment_mode", "")
        latest_update = diagnostic_row.get("latest_update")
        cache_hit = bool(diagnostic_row.get("cache_hit"))
        fallback_used = bool(diagnostic_row.get("fallback_used"))

        if history.empty:
            summary = {
                "symbol": symbol,
                "asset_type": asset_type,
                "provider": provider,
                "source_api": source_api,
                "adjustment_mode": adjustment_mode,
                "first_available_date": None,
                "last_available_date": None,
                "total_samples": 0,
                "coverage_ratio": 0.0,
                "missing_rows": total_calendar_days,
                "duplicate_dates": 0,
                "non_increasing_dates": True,
                "price_missing_rows": 0,
                "volume_missing_rows": 0,
                "amount_missing_rows": 0,
                "latest_cache_update": latest_update,
                "data_access_path": "cache_fallback" if fallback_used else "empty",
                "coverage_start_ok": False,
                "missing_start_period": f"{coverage_start.strftime('%Y-%m-%d')} ~ {end_ts.strftime('%Y-%m-%d')}",
                "cache_hit": cache_hit,
            }
            details = {
                "symbol": symbol,
                "asset_type": asset_type,
                "issues": ["empty_history"],
            }
            return summary, details

        frame = history.copy()
        frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
        dates = frame["date"]
        unique_dates = pd.DatetimeIndex(sorted(dates.unique()))
        calendar_index = pd.DatetimeIndex(calendar)
        in_range_available = calendar_index.intersection(unique_dates)

        ohlc = frame[["open", "high", "low", "close"]].apply(pd.to_numeric, errors="coerce")
        volume = pd.to_numeric(frame.get("volume"), errors="coerce") if "volume" in frame.columns else pd.Series(dtype=float)
        amount = pd.to_numeric(frame.get("amount"), errors="coerce") if "amount" in frame.columns else pd.Series(dtype=float)

        price_missing_rows = int(ohlc.isna().any(axis=1).sum())
        volume_missing_rows = int(volume.isna().sum()) if not volume.empty else len(frame)
        amount_missing_rows = int(amount.isna().sum()) if not amount.empty else len(frame)
        high_low_anomalies = int((ohlc["high"] < ohlc["low"]).sum())
        close_range_anomalies = int(((ohlc["close"] > ohlc["high"]) | (ohlc["close"] < ohlc["low"])).sum())
        negative_volume = int((volume < 0).sum()) if not volume.empty else 0
        negative_amount = int((amount < 0).sum()) if not amount.empty else 0

        first_date = pd.Timestamp(unique_dates.min()).strftime("%Y-%m-%d")
        last_date = pd.Timestamp(unique_dates.max()).strftime("%Y-%m-%d")
        coverage_start_ok = pd.Timestamp(unique_dates.min()) <= coverage_start
        missing_start_period = ""
        if not coverage_start_ok:
            missing_start_period = f"{coverage_start.strftime('%Y-%m-%d')} ~ {(pd.Timestamp(unique_dates.min()) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')}"

        summary = {
            "symbol": symbol,
            "asset_type": asset_type,
            "provider": provider,
            "source_api": source_api,
            "adjustment_mode": adjustment_mode,
            "first_available_date": first_date,
            "last_available_date": last_date,
            "total_samples": len(frame),
            "coverage_ratio": round(len(in_range_available) / total_calendar_days, 4) if total_calendar_days else 0.0,
            "missing_rows": total_calendar_days - len(in_range_available),
            "duplicate_dates": int(dates.duplicated().sum()),
            "non_increasing_dates": not bool(dates.is_monotonic_increasing),
            "price_missing_rows": price_missing_rows,
            "volume_missing_rows": volume_missing_rows,
            "amount_missing_rows": amount_missing_rows,
            "latest_cache_update": latest_update,
            "data_access_path": "cache_fallback" if fallback_used else "provider_refresh_or_cache_hit",
            "coverage_start_ok": coverage_start_ok,
            "missing_start_period": missing_start_period,
            "cache_hit": cache_hit,
        }
        details = {
            "symbol": symbol,
            "asset_type": asset_type,
            "date_sorted": bool(dates.is_monotonic_increasing),
            "duplicate_dates": int(dates.duplicated().sum()),
            "ohlc_numeric": bool(ohlc.notna().all().all()),
            "high_below_low_rows": high_low_anomalies,
            "close_out_of_range_rows": close_range_anomalies,
            "price_missing_rows": price_missing_rows,
            "negative_or_missing_volume_rows": int((volume.isna() | (volume < 0)).sum()) if not volume.empty else len(frame),
            "negative_or_missing_amount_rows": int((amount.isna() | (amount < 0)).sum()) if not amount.empty else len(frame),
            "negative_volume_rows": negative_volume,
            "negative_amount_rows": negative_amount,
            "raw_columns": diagnostic_row.get("raw_columns", ""),
            "standardized_columns": diagnostic_row.get("standardized_columns", ""),
            "note": diagnostic_row.get("note", ""),
        }
        return summary, details

    def _build_alignment_table(
        self,
        histories: dict[str, pd.DataFrame],
        target_table: pd.DataFrame,
        calendar: list[pd.Timestamp],
    ) -> pd.DataFrame:
        calendar_index = pd.DatetimeIndex(calendar)
        rows = []
        for _, item in target_table.iterrows():
            history = histories.get(item["symbol"], pd.DataFrame())
            dates = pd.DatetimeIndex([]) if history.empty else pd.DatetimeIndex(pd.to_datetime(history["date"]).dt.normalize())
            aligned = calendar_index.intersection(dates)
            rows.append(
                {
                    "symbol": item["symbol"],
                    "asset_type": item["asset_type"],
                    "aligned_days": len(aligned),
                    "calendar_days": len(calendar_index),
                    "alignment_ratio": round(len(aligned) / len(calendar_index), 4) if len(calendar_index) else 0.0,
                }
            )
        return pd.DataFrame(rows)

    def _build_monthly_execution_check(
        self,
        expected_monthly: list[pd.Timestamp],
        actual_monthly: list[pd.Timestamp],
    ) -> pd.DataFrame:
        actual_map = {pd.Timestamp(item).to_period("M"): pd.Timestamp(item) for item in actual_monthly}
        rows = []
        for expected in expected_monthly:
            period = expected.to_period("M")
            actual = actual_map.get(period)
            rows.append(
                {
                    "month": str(period),
                    "theoretical_trade_day": expected.strftime("%Y-%m-%d"),
                    "actual_trade_day": actual.strftime("%Y-%m-%d") if actual is not None else "",
                    "matched": bool(actual == expected),
                    "reason": "" if actual == expected else "实际执行日与理论首个交易日不一致",
                }
            )
        return pd.DataFrame(rows)

    def _build_weekly_execution_check(
        self,
        expected_weekly: list[pd.Timestamp],
        actual_weekly: list[pd.Timestamp],
    ) -> pd.DataFrame:
        actual_set = {pd.Timestamp(item).normalize() for item in actual_weekly}
        rows = []
        for expected in expected_weekly:
            rows.append(
                {
                    "week": str(expected.to_period("W-FRI")),
                    "theoretical_risk_day": expected.strftime("%Y-%m-%d"),
                    "actual_risk_day": expected.strftime("%Y-%m-%d") if expected in actual_set else "",
                    "matched": expected in actual_set,
                    "reason": "" if expected in actual_set else "缺少周度巡检记录",
                }
            )
        return pd.DataFrame(rows)

    def _build_allocation_check(self, backtest_result: ExtendedBacktestResult) -> pd.DataFrame:
        monthly_budget = float(self.configs["backtest"]["backtest"]["monthly_budget"])
        etf_target = monthly_budget * float(self.configs["portfolio"]["asset_allocation"]["etf_total_weight"])
        stock_target = monthly_budget * float(self.configs["portfolio"]["asset_allocation"]["stock_total_weight"])
        if backtest_result.trades.empty:
            return pd.DataFrame()

        trades = backtest_result.trades.copy()
        trades["month"] = pd.to_datetime(trades["date"]).dt.to_period("M").astype(str)
        rows = []
        for month, month_trades in trades.groupby("month"):
            unfilled = backtest_result.unfilled_orders.copy()
            if not unfilled.empty:
                unfilled["month"] = pd.to_datetime(unfilled["date"]).dt.to_period("M").astype(str)
                month_unfilled = unfilled.loc[unfilled["month"] == month]
                reasons = ",".join(sorted(month_unfilled["reason"].dropna().astype(str).unique()))
            else:
                reasons = ""
            etf_actual = float(month_trades.loc[month_trades["asset_type"] == "etf", "total_cash_out"].sum())
            stock_actual = float(month_trades.loc[month_trades["asset_type"] == "stock", "total_cash_out"].sum())
            rows.append(
                {
                    "month": month,
                    "etf_target_budget": etf_target,
                    "etf_actual_budget": etf_actual,
                    "etf_deviation": etf_actual - etf_target,
                    "stock_target_budget": stock_target,
                    "stock_actual_budget": stock_actual,
                    "stock_deviation": stock_actual - stock_target,
                    "deviation_reasons": reasons,
                }
            )
        return pd.DataFrame(rows)

    def _build_redline_stats(self, backtest_result: ExtendedBacktestResult) -> pd.DataFrame:
        if backtest_result.risk_records.empty:
            return pd.DataFrame()

        rows = []
        trades = backtest_result.trades.copy()
        trades["date"] = pd.to_datetime(trades["date"])
        unfilled = backtest_result.unfilled_orders.copy()
        if not unfilled.empty:
            unfilled["date"] = pd.to_datetime(unfilled["date"])

        for symbol, frame in backtest_result.risk_records.groupby("symbol"):
            yellow = frame.loc[frame["status"] == "YELLOW"]
            red = frame.loc[frame["status"] == "RED"]
            triggers = frame.loc[frame["status"].isin(["YELLOW", "RED"])].copy()
            first_trigger = pd.to_datetime(triggers["date"]).min() if not triggers.empty else pd.NaT
            violating_trades = trades.loc[(trades["symbol"] == symbol) & (trades["date"] >= first_trigger) & (trades["status"].isin(["YELLOW", "RED"]))] if pd.notna(first_trigger) else pd.DataFrame()
            paused = unfilled.loc[(unfilled["symbol"] == symbol) & (unfilled["date"] >= first_trigger) & (unfilled["reason"] == "paused_by_risk_rule")] if pd.notna(first_trigger) and not unfilled.empty else pd.DataFrame()
            action = "人工复核/正常观察"
            if not paused.empty:
                action = "暂停买入"
            if not violating_trades.empty:
                action = "发现违规继续自动新增"
            rows.append(
                {
                    "symbol": symbol,
                    "yellow_count": len(yellow),
                    "red_count": len(red),
                    "first_trigger_date": first_trigger.strftime("%Y-%m-%d") if pd.notna(first_trigger) else "",
                    "action_after_trigger": action,
                    "auto_add_violation": not violating_trades.empty,
                }
            )
        return pd.DataFrame(rows)

    def _build_unfilled_summary(
        self,
        backtest_result: ExtendedBacktestResult,
        data_bundle: MarketDataBundle,
    ) -> pd.DataFrame:
        symbol_first_dates = {}
        for symbol, history in data_bundle.histories.items():
            if history.empty:
                continue
            symbol_first_dates[symbol] = pd.Timestamp(history["date"].min())

        rows = []
        if not backtest_result.unfilled_orders.empty:
            unfilled = backtest_result.unfilled_orders.copy()
            unfilled["date"] = pd.to_datetime(unfilled["date"])
            for _, row in unfilled.iterrows():
                reason = str(row["reason"])
                category = self._classify_unfilled_reason(
                    reason=reason,
                    trade_date=pd.Timestamp(row["date"]),
                    symbol=str(row["symbol"]),
                    symbol_first_dates=symbol_first_dates,
                )
                rows.append(
                    {
                        "category": category,
                        "unfilled_amount": float(row.get("recommended_amount", 0.0)),
                    }
                )
        if rows:
            summary = pd.DataFrame(rows).groupby("category", as_index=False).agg(
                count=("category", "size"),
                unfilled_amount=("unfilled_amount", "sum"),
            )
        else:
            summary = pd.DataFrame(columns=["category", "count", "unfilled_amount"])
        existing_categories = set(summary["category"].tolist()) if not summary.empty else set()
        for category in self.UNFILLED_CATEGORIES:
            if category not in existing_categories:
                summary = pd.concat(
                    [
                        summary,
                        pd.DataFrame([{"category": category, "count": 0, "unfilled_amount": 0.0}]),
                    ],
                    ignore_index=True,
                )
        summary["cash_handling"] = "保留现金"
        return summary.sort_values("category").reset_index(drop=True)

    def _build_weight_deviation(
        self,
        backtest_result: ExtendedBacktestResult,
        data_bundle: MarketDataBundle,
        target_table: pd.DataFrame,
    ) -> pd.DataFrame:
        snapshots = backtest_result.portfolio_snapshots.copy()
        if snapshots.empty:
            return pd.DataFrame()

        risk_records = backtest_result.risk_records.copy()
        if not risk_records.empty:
            risk_records["date"] = pd.to_datetime(risk_records["date"])
        first_dates = {
            symbol: pd.Timestamp(history["date"].min()) if not history.empty else pd.NaT
            for symbol, history in data_bundle.histories.items()
        }

        rows = []
        for _, row in snapshots.iterrows():
            symbol = row["symbol"]
            date = pd.Timestamp(row["date"])
            explanation = "正常偏离"
            if pd.notna(first_dates.get(symbol)) and date < first_dates[symbol]:
                explanation = "起点数据缺失，系统保留现金"
            if not risk_records.empty:
                status_rows = risk_records.loc[(risk_records["symbol"] == symbol) & (risk_records["date"] == date)]
                if not status_rows.empty and status_rows["status"].isin(["YELLOW", "RED"]).any():
                    explanation = "红线暂停或人工复核导致偏离"
            rows.append(
                {
                    "date": pd.Timestamp(date).strftime("%Y-%m-%d"),
                    "symbol": symbol,
                    "asset_type": row["asset_type"],
                    "current_weight": row["current_weight"],
                    "target_weight": row["target_weight"],
                    "deviation": row["current_weight"] - row["target_weight"],
                    "explanation": explanation,
                    "stock_limit_exceeded": (
                        row["asset_type"] == "stock" and float(row["current_weight"]) > float(row["target_weight"])
                    ),
                }
            )
        return pd.DataFrame(rows)

    def _build_backtest_config_summary(self, data_bundle: MarketDataBundle) -> dict[str, Any]:
        return {
            "start_date": self.configs["backtest"]["backtest"]["start_date"],
            "end_date": self.configs["backtest"]["backtest"]["end_date"],
            "adjustment_mode": data_bundle.metadata.get("adjustment_mode"),
            "etf_slippage": self.configs["backtest"]["transaction_cost"]["etf"]["slippage"],
            "stock_slippage": self.configs["backtest"]["transaction_cost"]["stock"]["slippage"],
            "etf_buy_commission": self.configs["backtest"]["transaction_cost"]["etf"]["buy_commission"],
            "stock_buy_commission": self.configs["backtest"]["transaction_cost"]["stock"]["buy_commission"],
            "stock_sell_stamp_tax": self.configs["backtest"]["transaction_cost"]["stock"]["sell_stamp_tax"],
            "lot_size": self.configs["backtest"]["trading_rules"]["min_trade_lot"],
            "trade_frequency": self.configs["app"]["schedule"]["monthly_invest_day_rule"],
            "risk_frequency": self.configs["app"]["schedule"]["weekly_risk_check_rule"],
            "data_mode": data_bundle.metadata.get("data_mode"),
            "provider": data_bundle.metadata.get("provider"),
            "source_api": data_bundle.metadata.get("source_api"),
        }

    def _render_data_validation_markdown(
        self,
        summary_df: pd.DataFrame,
        alignment_table: pd.DataFrame,
        coverage_gaps: list[dict[str, Any]],
        diagnostics_json: dict[str, Any],
    ) -> str:
        lines = [
            "# 数据验收报告",
            "",
            "## 数据模式",
            f"- 模式: {diagnostics_json['metadata']['data_mode']}",
            f"- provider: {diagnostics_json['metadata']['provider']}",
            f"- source_api: {diagnostics_json['metadata']['source_api']}",
            f"- adjustment_mode: {diagnostics_json['metadata']['adjustment_mode']}",
            f"- latest_data_date: {diagnostics_json['metadata']['latest_data_date']}",
            f"- data_updated_at: {diagnostics_json['metadata']['data_updated_at']}",
            "",
            "## 标的级摘要",
            self._frame_to_text(summary_df),
            "",
            "## 日期对齐程度",
            self._frame_to_text(alignment_table),
            "",
            "## 覆盖性检查",
            self._frame_to_text(pd.DataFrame(coverage_gaps)) if coverage_gaps else "全部标的覆盖到回测区间起点。",
            "",
            "## 复权说明",
            f"- 当前复权模式: {diagnostics_json['adjustment_note']['mode']}",
            f"- adj_close 定义: {diagnostics_json['adjustment_note']['adj_close_definition']}",
            f"- 缓存隔离: {diagnostics_json['adjustment_note']['cache_isolation']}",
            "",
            "## 重要限制",
            "- 当前交易日历根据真实行情日期推导，不是交易所官方日历。",
            "- 若标的在回测起点前无数据，系统当前处理为保留现金，直到出现可交易数据。",
        ]
        return "\n".join(lines)

    def _render_backtest_validation_markdown(
        self,
        monthly_check: pd.DataFrame,
        weekly_check: pd.DataFrame,
        allocation_check: pd.DataFrame,
        redline_stats: pd.DataFrame,
        unfilled_summary: pd.DataFrame,
        weight_deviation: pd.DataFrame,
        config_summary: dict[str, Any],
    ) -> str:
        lines = [
            "# 回测一致性检查报告",
            "",
            "## 回测配置摘要",
            self._dict_to_text(config_summary),
            "",
            "## 月度执行日检查",
            self._frame_to_text(monthly_check),
            "",
            "## 周度巡检日检查",
            self._frame_to_text(weekly_check),
            "",
            "## 资金分配检查",
            self._frame_to_text(allocation_check),
            "",
            "## 红线触发统计",
            self._frame_to_text(redline_stats),
            "",
            "## 未成交统计",
            self._frame_to_text(unfilled_summary),
            "",
            "## 权重偏离检查",
            self._frame_to_text(weight_deviation),
            "",
            "## 重要限制",
            "- 当前回测更适合长期定投研究与风险提醒，不等于真实成交还原。",
            "- 自动卖出仍保持禁用，本报告只检查是否出现违规自动新增。",
        ]
        return "\n".join(lines)

    @staticmethod
    def _diagnostic_row(diagnostics: pd.DataFrame, symbol: str, asset_type: str) -> pd.Series:
        if diagnostics.empty:
            return pd.Series(dtype=object)
        rows = diagnostics.loc[(diagnostics["symbol"] == symbol) & (diagnostics["asset_type"] == asset_type)]
        return rows.iloc[0] if not rows.empty else pd.Series(dtype=object)

    @staticmethod
    def _classify_unfilled_reason(
        reason: str,
        trade_date: pd.Timestamp,
        symbol: str,
        symbol_first_dates: dict[str, pd.Timestamp],
    ) -> str:
        if reason == "paused_by_risk_rule":
            return "红线暂停"
        if reason == "below_min_trade_lot":
            return "资金不足整手"
        if reason == "non_trading_day":
            return "非交易日"
        if reason == "insufficient_cash_after_rounding":
            return "其他"
        if reason == "missing_market_data_on_trade_day":
            first_date = symbol_first_dates.get(symbol)
            if first_date is not None and trade_date < first_date:
                return "标的在当期不可用"
            return "缺少数据"
        if reason == "invalid_close_price":
            return "缺少数据"
        if reason == "recommended_amount_zero":
            return "其他"
        return "其他"

    @staticmethod
    def _section_rows(section: str, frame: pd.DataFrame) -> list[dict[str, Any]]:
        if frame.empty:
            return [{"section": section, "item": "empty", "value": ""}]
        rows = []
        for _, row in frame.iterrows():
            payload = {"section": section}
            payload.update({key: value for key, value in row.to_dict().items()})
            rows.append(payload)
        return rows

    @staticmethod
    def _frame_to_text(frame: pd.DataFrame) -> str:
        if frame.empty:
            return "无"
        return "```text\n" + frame.to_csv(index=False) + "```"

    @staticmethod
    def _dict_to_text(data: dict[str, Any]) -> str:
        return "\n".join([f"- {key}: {value}" for key, value in data.items()]) if data else "无"
