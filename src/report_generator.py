"""报告输出模块。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.runtime_models import ExtendedBacktestResult, MarketDataBundle
from src.utils.schemas import MonthlyRecommendation


class ReportGenerator:
    """生成 CSV 与 Markdown 报告。"""

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)

    def save_monthly_report(
        self,
        recommendation: MonthlyRecommendation,
        current_table: pd.DataFrame,
        risk_table: pd.DataFrame,
        data_bundle: MarketDataBundle,
        config_summary: dict[str, object],
        portfolio_cash: float = 0.0,
    ) -> dict[str, Path]:
        """输出月度建议报告。"""

        date_str = recommendation.as_of_date.strftime("%Y%m%d")
        out_dir = self.project_root / "reports" / "monthly"
        out_dir.mkdir(parents=True, exist_ok=True)

        suggestion_csv = out_dir / f"monthly_suggestion_{date_str}.csv"
        holdings_csv = out_dir / f"current_holdings_{date_str}.csv"
        risks_csv = out_dir / f"risk_status_{date_str}.csv"
        diagnostics_csv = out_dir / f"data_diagnostics_{date_str}.csv"
        markdown_path = out_dir / f"monthly_report_{date_str}.md"

        recommendation_frame = recommendation.to_frame()
        blocked_items = self._build_monthly_blocked_items(recommendation_frame, current_table)
        portfolio_summary, allocation_summary = self._build_current_portfolio_views(current_table, portfolio_cash)
        next_priority = self._build_next_priority_table(recommendation_frame)
        risk_summary = self._build_risk_summary(risk_table)
        manual_logic_summary = self._build_manual_logic_summary(risk_table)
        diagnostics_preview = self._build_diagnostics_preview(data_bundle.diagnostics)

        recommendation_frame.to_csv(suggestion_csv, index=False, encoding="utf-8-sig")
        current_table.to_csv(holdings_csv, index=False, encoding="utf-8-sig")
        risk_table.to_csv(risks_csv, index=False, encoding="utf-8-sig")
        data_bundle.diagnostics.to_csv(diagnostics_csv, index=False, encoding="utf-8-sig")
        markdown_path.write_text(
            self._render_monthly_markdown(
                recommendation=recommendation,
                recommendation_frame=recommendation_frame,
                current_table=current_table,
                risk_table=risk_table,
                risk_summary=risk_summary,
                manual_logic_summary=manual_logic_summary,
                blocked_items=blocked_items,
                portfolio_summary=portfolio_summary,
                allocation_summary=allocation_summary,
                next_priority=next_priority,
                diagnostics_preview=diagnostics_preview,
                data_bundle=data_bundle,
                config_summary=config_summary,
            ),
            encoding="utf-8",
        )

        return {
            "suggestion_csv": suggestion_csv,
            "holdings_csv": holdings_csv,
            "risks_csv": risks_csv,
            "diagnostics_csv": diagnostics_csv,
            "markdown": markdown_path,
        }

    def save_backtest_report(
        self,
        result: ExtendedBacktestResult,
        data_bundle: MarketDataBundle,
        config_summary: dict[str, object],
    ) -> dict[str, Path]:
        """输出回测结果报告。"""

        out_dir = self.project_root / "reports" / "backtest"
        out_dir.mkdir(parents=True, exist_ok=True)

        equity_path = out_dir / "equity_curve.csv"
        trades_path = out_dir / "trades.csv"
        monthly_path = out_dir / "monthly_records.csv"
        risks_path = out_dir / "risk_records.csv"
        unfilled_path = out_dir / "unfilled_orders.csv"
        diagnostics_path = out_dir / "data_diagnostics.csv"
        metrics_path = out_dir / "metrics.csv"
        recommendations_path = out_dir / "recommendation_records.csv"
        snapshots_path = out_dir / "portfolio_snapshots.csv"
        markdown_path = out_dir / "backtest_report.md"

        result.equity_curve.to_csv(equity_path, index=False, encoding="utf-8-sig")
        result.trades.to_csv(trades_path, index=False, encoding="utf-8-sig")
        result.monthly_records.to_csv(monthly_path, index=False, encoding="utf-8-sig")
        result.risk_records.to_csv(risks_path, index=False, encoding="utf-8-sig")
        result.unfilled_orders.to_csv(unfilled_path, index=False, encoding="utf-8-sig")
        data_bundle.diagnostics.to_csv(diagnostics_path, index=False, encoding="utf-8-sig")
        pd.DataFrame([result.metrics]).to_csv(metrics_path, index=False, encoding="utf-8-sig")
        result.recommendation_records.to_csv(recommendations_path, index=False, encoding="utf-8-sig")
        result.portfolio_snapshots.to_csv(snapshots_path, index=False, encoding="utf-8-sig")

        availability_summary = self._build_diagnostics_preview(data_bundle.diagnostics)
        unfilled_summary = self._build_unfilled_summary(result.unfilled_orders)
        redline_summary = self._build_backtest_redline_summary(result.risk_records)
        manual_logic_summary = self._build_manual_logic_summary(result.risk_records)
        snapshot_summary, allocation_summary, latest_snapshot = self._build_backtest_snapshot_views(result)
        latest_priority = self._build_backtest_priority_table(result.recommendation_records)
        weight_deviation = self._build_backtest_weight_view(latest_snapshot, result.risk_records)

        markdown_path.write_text(
            self._render_backtest_markdown(
                result=result,
                data_bundle=data_bundle,
                config_summary=config_summary,
                availability_summary=availability_summary,
                unfilled_summary=unfilled_summary,
                redline_summary=redline_summary,
                manual_logic_summary=manual_logic_summary,
                snapshot_summary=snapshot_summary,
                allocation_summary=allocation_summary,
                latest_snapshot=latest_snapshot,
                latest_priority=latest_priority,
                weight_deviation=weight_deviation,
            ),
            encoding="utf-8",
        )

        return {
            "equity_curve": equity_path,
            "trades": trades_path,
            "monthly_records": monthly_path,
            "risk_records": risks_path,
            "unfilled_orders": unfilled_path,
            "diagnostics": diagnostics_path,
            "metrics": metrics_path,
            "recommendations": recommendations_path,
            "snapshots": snapshots_path,
            "markdown": markdown_path,
        }

    @staticmethod
    def _render_monthly_markdown(
        recommendation: MonthlyRecommendation,
        recommendation_frame: pd.DataFrame,
        current_table: pd.DataFrame,
        risk_table: pd.DataFrame,
        risk_summary: pd.DataFrame,
        manual_logic_summary: pd.DataFrame,
        blocked_items: pd.DataFrame,
        portfolio_summary: dict[str, object],
        allocation_summary: pd.DataFrame,
        next_priority: pd.DataFrame,
        diagnostics_preview: pd.DataFrame,
        data_bundle: MarketDataBundle,
        config_summary: dict[str, object],
    ) -> str:
        lines = [
            f"# 月度定投建议报告 - {recommendation.as_of_date:%Y-%m-%d}",
            "",
            "## 数据模式与来源",
            f"- 数据模式: {data_bundle.metadata.get('data_mode')}",
            f"- 数据提供方: {data_bundle.metadata.get('provider')}",
            f"- 历史接口: {data_bundle.metadata.get('source_api', 'n/a')}",
            f"- 当前复权模式: {data_bundle.metadata.get('adjustment_mode')}",
            f"- 最新数据日期: {data_bundle.metadata.get('latest_data_date')}",
            f"- 最近更新时间: {data_bundle.metadata.get('data_updated_at')}",
            f"- 本月实际命中的交易日: {data_bundle.metadata.get('as_of_date', recommendation.as_of_date.strftime('%Y-%m-%d'))}",
            "",
            "## 当前配置参数摘要",
            ReportGenerator._dict_to_text(config_summary),
            "",
            "## 当前组合快照",
            ReportGenerator._dict_to_text(portfolio_summary),
            ReportGenerator._frame_to_text(allocation_summary),
            "",
            "## 当前持仓与目标权重",
            ReportGenerator._frame_to_text(current_table) if not current_table.empty else "无当前持仓数据",
            "",
            "## 本月建议买入",
            ReportGenerator._frame_to_text(recommendation_frame) if not recommendation_frame.empty else "无建议数据",
            "",
            "## 本月暂缓或无法执行项目",
            ReportGenerator._frame_to_text(blocked_items) if not blocked_items.empty else "当前无需要暂缓的项目",
            "",
            "## 当前风险灯号总览",
            ReportGenerator._frame_to_text(risk_summary) if not risk_summary.empty else "当前无风险汇总",
            "",
            "## 人工逻辑红线摘要",
            ReportGenerator._frame_to_text(manual_logic_summary) if not manual_logic_summary.empty else "当前无人工逻辑红线生效记录",
            "",
            "## 风险明细",
            ReportGenerator._frame_to_text(risk_table) if not risk_table.empty else "当前无风险明细",
            "",
            "## 下期优先定投标的建议",
            ReportGenerator._frame_to_text(next_priority) if not next_priority.empty else "当前无新增优先建议",
            "",
            "## 数据质量摘要",
            ReportGenerator._frame_to_text(diagnostics_preview) if not diagnostics_preview.empty else "当前无数据诊断摘要",
            "",
            "## 本月需要人工判断的事项清单",
        ]
        if recommendation.manual_review_items:
            lines.extend([f"- {item}" for item in recommendation.manual_review_items])
        else:
            lines.append("- 当前无必须人工判断事项")
        lines.extend(
            [
                "",
                "## 重要限制说明",
                "- 本报告为建议模式输出，不自动下单。",
                "- YELLOW / RED 默认暂停新增买入，不自动卖出。",
                "- 当前总资产估算包含持仓市值与已记录现金，不代表账户实时净值。",
            ]
        )
        lines.extend([f"- {note}" for note in recommendation.notes])
        return "\n".join(lines)

    @staticmethod
    def _render_backtest_markdown(
        result: ExtendedBacktestResult,
        data_bundle: MarketDataBundle,
        config_summary: dict[str, object],
        availability_summary: pd.DataFrame,
        unfilled_summary: pd.DataFrame,
        redline_summary: pd.DataFrame,
        manual_logic_summary: pd.DataFrame,
        snapshot_summary: dict[str, object],
        allocation_summary: pd.DataFrame,
        latest_snapshot: pd.DataFrame,
        latest_priority: pd.DataFrame,
        weight_deviation: pd.DataFrame,
    ) -> str:
        metrics_text = "\n".join([f"- {key}: {value:.6f}" for key, value in result.metrics.items()])
        lines = [
            "# MVP 回测报告",
            "",
            "## 数据模式与来源说明",
            f"- 数据模式: {data_bundle.metadata.get('data_mode')}",
            f"- 数据提供方: {data_bundle.metadata.get('provider')}",
            f"- 历史接口: {data_bundle.metadata.get('source_api', 'n/a')}",
            f"- 复权模式: {data_bundle.metadata.get('adjustment_mode')}",
            f"- 最新数据日期: {data_bundle.metadata.get('latest_data_date')}",
            f"- 最近更新时间: {data_bundle.metadata.get('data_updated_at')}",
            "",
            "## 回测区间内标的可用性摘要",
            ReportGenerator._frame_to_text(availability_summary) if not availability_summary.empty else "无可用性摘要",
            "",
            "## 回测配置摘要",
            ReportGenerator._dict_to_text(config_summary),
            "",
            "## 绩效指标",
            metrics_text,
            "",
            "## 实际命中的交易日",
            ReportGenerator._dict_to_text(
                {
                    "monthly_trade_days": ",".join(result.metadata.get("actual_monthly_trade_days", [])),
                    "weekly_risk_days": ",".join(result.metadata.get("actual_weekly_risk_days", [])),
                }
            ),
            "",
            "## 未成交统计",
            ReportGenerator._frame_to_text(unfilled_summary) if not unfilled_summary.empty else "无未成交记录",
            "",
            "## 红线触发统计",
            ReportGenerator._frame_to_text(redline_summary) if not redline_summary.empty else "无红线触发统计",
            "",
            "## 人工逻辑红线摘要",
            ReportGenerator._frame_to_text(manual_logic_summary) if not manual_logic_summary.empty else "回测区间内无人工逻辑红线生效记录",
            "",
            "## 组合快照",
            ReportGenerator._dict_to_text(snapshot_summary),
            ReportGenerator._frame_to_text(allocation_summary) if not allocation_summary.empty else "无资产分布数据",
            "",
            "## 当前权重与偏离",
            ReportGenerator._frame_to_text(weight_deviation) if not weight_deviation.empty else "无权重偏离数据",
            "",
            "## 最新持仓快照",
            ReportGenerator._frame_to_text(latest_snapshot) if not latest_snapshot.empty else "无快照数据",
            "",
            "## 下期优先定投标的建议",
            ReportGenerator._frame_to_text(latest_priority) if not latest_priority.empty else "无优先建议",
            "",
            "## 结果限制说明",
            "- 当前回测更适合长期定投研究与风险提醒，不等于真实成交还原。",
            "- 自动卖出仍保持禁用，回测不会主动减仓或退出。",
            "- 交易日历当前根据行情日期推导，未接入交易所官方日历源。",
        ]
        return "\n".join(lines)

    @staticmethod
    def _build_monthly_blocked_items(recommendation_frame: pd.DataFrame, current_table: pd.DataFrame) -> pd.DataFrame:
        if recommendation_frame.empty:
            return pd.DataFrame()
        merged = recommendation_frame.merge(
            current_table[["symbol", "asset_type", "last_price"]],
            on=["symbol", "asset_type"],
            how="left",
        )
        merged["blocked_reason"] = ""
        if "final_human_readable_action" in merged.columns:
            merged.loc[merged["pause_buy"] == True, "blocked_reason"] = merged.loc[merged["pause_buy"] == True, "final_human_readable_action"]
        else:
            merged.loc[merged["pause_buy"] == True, "blocked_reason"] = "?????????"
        merged.loc[merged["recommended_amount"] <= 0, "blocked_reason"] = "本期建议金额为 0"
        merged.loc[merged["last_price"].fillna(0.0) <= 0, "blocked_reason"] = "缺少可用价格"
        blocked = merged.loc[merged["blocked_reason"] != ""].copy()
        return blocked[["symbol", "asset_type", "recommended_amount", "status", "blocked_reason", "reasons"]]

    @staticmethod
    def _build_current_portfolio_views(
        current_table: pd.DataFrame,
        portfolio_cash: float,
    ) -> tuple[dict[str, object], pd.DataFrame]:
        holdings_value = float(current_table["market_value"].sum()) if not current_table.empty else 0.0
        total_asset_estimate = holdings_value + float(portfolio_cash)
        allocation = pd.DataFrame()
        if not current_table.empty:
            allocation = current_table.groupby("asset_type", as_index=False).agg(market_value=("market_value", "sum"))
            allocation["actual_ratio"] = allocation["market_value"] / total_asset_estimate if total_asset_estimate > 0 else 0.0
        summary = {
            "total_asset_estimate": round(total_asset_estimate, 2),
            "holdings_market_value": round(holdings_value, 2),
            "recorded_cash": round(float(portfolio_cash), 2),
        }
        return summary, allocation

    @staticmethod
    def _build_next_priority_table(recommendation_frame: pd.DataFrame) -> pd.DataFrame:
        if recommendation_frame.empty:
            return pd.DataFrame()
        frame = recommendation_frame.loc[
            (recommendation_frame["recommended_amount"] > 0) & (recommendation_frame["pause_buy"] == False)
        ].copy()
        return frame.sort_values(["recommended_amount", "target_weight"], ascending=[False, False]).head(5)

    @staticmethod
    def _build_risk_summary(risk_table: pd.DataFrame) -> pd.DataFrame:
        if risk_table.empty:
            return pd.DataFrame()
        return risk_table.groupby("status", as_index=False).agg(count=("symbol", "size"))

    @staticmethod
    def _build_manual_logic_summary(risk_table: pd.DataFrame) -> pd.DataFrame:
        if risk_table.empty:
            return pd.DataFrame()
        frame = risk_table.copy()
        for column in ["manual_pause_buy", "manual_force_review", "thesis_broken"]:
            if column not in frame.columns:
                frame[column] = False
        frame["manual_pause_buy"] = frame["manual_pause_buy"].astype(bool)
        frame["manual_force_review"] = frame["manual_force_review"].astype(bool)
        frame["thesis_broken"] = frame["thesis_broken"].astype(bool)
        filtered = frame.loc[frame[["manual_pause_buy", "manual_force_review", "thesis_broken"]].any(axis=1)].copy()
        if filtered.empty:
            return pd.DataFrame()
        return filtered[["symbol", "asset_type", "manual_pause_buy", "manual_force_review", "thesis_broken", "final_human_readable_action", "logic_note", "effective_from"]].drop_duplicates()

    @staticmethod
    def _build_diagnostics_preview(diagnostics: pd.DataFrame) -> pd.DataFrame:
        if diagnostics.empty:
            return pd.DataFrame()
        columns = [
            column
            for column in [
                "symbol",
                "asset_type",
                "rows",
                "start_date",
                "end_date",
                "duplicate_dates",
                "missing_required_rows",
                "fallback_used",
                "cache_hit",
                "latest_update",
            ]
            if column in diagnostics.columns
        ]
        return diagnostics[columns].copy()

    @staticmethod
    def _build_unfilled_summary(unfilled_orders: pd.DataFrame) -> pd.DataFrame:
        if unfilled_orders.empty:
            return pd.DataFrame()
        frame = unfilled_orders.copy()
        return frame.groupby("reason", as_index=False).agg(
            count=("symbol", "size"),
            recommended_amount=("recommended_amount", "sum"),
        )

    @staticmethod
    def _build_backtest_redline_summary(risk_records: pd.DataFrame) -> pd.DataFrame:
        if risk_records.empty:
            return pd.DataFrame()
        frame = risk_records.loc[risk_records["status"].isin(["YELLOW", "RED"])].copy()
        if frame.empty:
            return pd.DataFrame()
        frame["date"] = pd.to_datetime(frame["date"])
        summary = frame.groupby(["symbol", "status"], as_index=False).agg(
            trigger_count=("date", "size"),
            first_trigger_date=("date", "min"),
        )
        summary["first_trigger_date"] = summary["first_trigger_date"].dt.strftime("%Y-%m-%d")
        return summary

    @staticmethod
    def _build_backtest_snapshot_views(
        result: ExtendedBacktestResult,
    ) -> tuple[dict[str, object], pd.DataFrame, pd.DataFrame]:
        if result.portfolio_snapshots.empty:
            return {}, pd.DataFrame(), pd.DataFrame()
        snapshots = result.portfolio_snapshots.copy()
        snapshots["date"] = pd.to_datetime(snapshots["date"])
        latest_date = snapshots["date"].max()
        latest_snapshot = snapshots.loc[snapshots["date"] == latest_date].copy()
        total_value = float(latest_snapshot["total_value"].iloc[0]) if not latest_snapshot.empty else 0.0
        allocation = latest_snapshot.groupby("asset_type", as_index=False).agg(market_value=("market_value", "sum"))
        allocation["actual_ratio"] = allocation["market_value"] / total_value if total_value > 0 else 0.0
        summary = {
            "latest_snapshot_date": latest_date.strftime("%Y-%m-%d"),
            "total_asset_estimate": round(total_value, 2),
            "ending_cash": round(float(latest_snapshot["cash"].iloc[0]), 2) if not latest_snapshot.empty else 0.0,
        }
        return summary, allocation, latest_snapshot

    @staticmethod
    def _build_backtest_priority_table(recommendation_records: pd.DataFrame) -> pd.DataFrame:
        if recommendation_records.empty:
            return pd.DataFrame()
        frame = recommendation_records.copy()
        frame["date"] = pd.to_datetime(frame["date"])
        latest_date = frame["date"].max()
        latest = frame.loc[(frame["date"] == latest_date) & (frame["recommended_amount"] > 0) & (frame["pause_buy"] == False)].copy()
        return latest.sort_values("recommended_amount", ascending=False).head(5)

    @staticmethod
    def _build_backtest_weight_view(latest_snapshot: pd.DataFrame, risk_records: pd.DataFrame) -> pd.DataFrame:
        if latest_snapshot.empty:
            return pd.DataFrame()
        view = latest_snapshot[["symbol", "asset_type", "current_weight", "target_weight", "weight_gap"]].copy()
        view["explanation"] = "正常偏离"
        if not risk_records.empty:
            risk_records = risk_records.copy()
            risk_records["date"] = pd.to_datetime(risk_records["date"])
            latest_date = pd.to_datetime(latest_snapshot["date"]).max()
            redline_symbols = risk_records.loc[
                (risk_records["date"] == latest_date) & (risk_records["status"].isin(["YELLOW", "RED"])),
                "symbol",
            ].astype(str)
            view.loc[view["symbol"].isin(redline_symbols), "explanation"] = "红线暂停可能导致偏离"
        return view

    @staticmethod
    def _frame_to_text(frame: pd.DataFrame) -> str:
        return "```text\n" + frame.to_csv(index=False) + "```"

    @staticmethod
    def _dict_to_text(data: dict[str, object]) -> str:
        lines = [f"- {key}: {value}" for key, value in data.items()]
        return "\n".join(lines) if lines else "无"
