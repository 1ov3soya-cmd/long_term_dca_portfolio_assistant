"""参数敏感性测试与对比报告。"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.backtest_engine import MVPBacktestEngine
from src.data_loader import MarketDataLoader
from src.portfolio import build_target_table
from src.utils.logger import get_logger
from src.utils.runtime_models import ExtendedBacktestResult, MarketDataBundle


class SensitivityEngine:
    """执行单因子参数敏感性测试。"""

    NUMERIC_DIFF_COLUMNS = [
        "cumulative_return",
        "annualized_return",
        "max_drawdown",
        "annualized_volatility",
        "sharpe_like_ratio",
        "total_invested_cash",
        "total_uninvested_cash",
        "invested_ratio",
        "total_trade_count",
        "unfilled_count",
        "unfilled_amount",
        "total_yellow_triggers",
        "total_red_triggers",
        "avg_monthly_risk_flags",
        "average_etf_weight",
        "average_stock_weight",
        "average_cash_weight",
        "average_weight_deviation",
        "max_weight_deviation",
        "count_months_with_cash_drag",
        "count_months_with_paused_buys",
    ]

    def __init__(self, configs: dict[str, dict[str, Any]], project_root: str | Path) -> None:
        self.configs = configs
        self.project_root = Path(project_root)
        self.logger = get_logger(self.__class__.__name__, configs["app"]["runtime"]["log_level"])
        self.bundle_cache: dict[str, MarketDataBundle] = {}

    def run(self, end_date: str | None = None) -> dict[str, Any]:
        """运行敏感性测试，并输出汇总文件。"""

        scenarios = self._build_scenarios()
        results: list[dict[str, Any]] = []
        details: dict[str, Any] = {}

        base_configs = deepcopy(self.configs)
        if end_date:
            base_configs["backtest"]["backtest"]["end_date"] = end_date

        for scenario in scenarios:
            scenario_name = str(scenario["name"])
            self.logger.info("开始运行参数组: %s", scenario_name)
            try:
                scenario_configs = self._build_effective_configs(base_configs, scenario)
                result = self._run_single_scenario(scenario_name, scenario, scenario_configs)
                results.append(result["summary"])
                details[scenario_name] = result["details"]
            except Exception as exc:  # noqa: BLE001
                self.logger.exception("参数组运行失败: %s", scenario_name)
                failed_summary = self._build_failed_summary(scenario, base_configs, str(exc))
                results.append(failed_summary)
                details[scenario_name] = {
                    "group_name": scenario_name,
                    "description": scenario.get("description", ""),
                    "status": "failed",
                    "error": str(exc),
                }

        summary_df = pd.DataFrame(results)
        baseline_diff_df = self._build_baseline_diff(summary_df)
        rankings_df = self._build_rankings(summary_df)
        report_md = self._render_report(summary_df, baseline_diff_df)

        reports_dir = self.project_root / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        summary_path = reports_dir / "sensitivity_summary.csv"
        diff_path = reports_dir / "sensitivity_baseline_diff.csv"
        rankings_path = reports_dir / "sensitivity_rankings.csv"
        details_path = reports_dir / "sensitivity_details.json"
        report_path = reports_dir / "sensitivity_report.md"

        summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")
        baseline_diff_df.to_csv(diff_path, index=False, encoding="utf-8-sig")
        rankings_df.to_csv(rankings_path, index=False, encoding="utf-8-sig")
        details_path.write_text(json.dumps(details, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        report_path.write_text(report_md, encoding="utf-8")

        return {
            "summary": summary_df,
            "baseline_diff": baseline_diff_df,
            "rankings": rankings_df,
            "details": details,
            "paths": {
                "summary": summary_path,
                "baseline_diff": diff_path,
                "rankings": rankings_path,
                "details": details_path,
                "report": report_path,
            },
        }

    def _build_scenarios(self) -> list[dict[str, Any]]:
        sensitivity_cfg = self.configs["sensitivity"]["sensitivity"]
        baseline = deepcopy(sensitivity_cfg["baseline"])
        scenarios = [{"name": baseline["name"], "description": baseline["description"], "overrides": baseline["overrides"]}]
        scenarios.extend(deepcopy(sensitivity_cfg["scenarios"]))
        return scenarios

    def _build_effective_configs(
        self,
        base_configs: dict[str, dict[str, Any]],
        scenario: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        baseline_overrides = deepcopy(self.configs["sensitivity"]["sensitivity"]["baseline"]["overrides"])
        effective = deepcopy(base_configs)
        self._deep_merge(effective, baseline_overrides)
        self._deep_merge(effective, scenario.get("overrides", {}))
        return effective

    def _run_single_scenario(
        self,
        scenario_name: str,
        scenario: dict[str, Any],
        scenario_configs: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        adjustment_mode = scenario_configs["app"]["efinance"]["adjustment_mode"]
        if adjustment_mode not in self.bundle_cache:
            loader = MarketDataLoader(self.project_root, configs=scenario_configs)
            bundle = loader.load_market_data_bundle(
                start_date=scenario_configs["backtest"]["backtest"]["start_date"],
                end_date=scenario_configs["backtest"]["backtest"]["end_date"],
                mode=self.configs["sensitivity"]["sensitivity"].get("data_mode", "real"),
            )
            self.bundle_cache[adjustment_mode] = bundle
        bundle = self.bundle_cache[adjustment_mode]

        target_table = build_target_table(scenario_configs["portfolio"])
        engine = MVPBacktestEngine(scenario_configs, self.project_root)
        backtest_result = engine.run(bundle.histories, target_table, data_bundle=bundle)

        summary = self._build_summary_row(
            scenario_name=scenario_name,
            scenario=scenario,
            configs=scenario_configs,
            bundle=bundle,
            result=backtest_result,
        )
        details = {
            "group_name": scenario_name,
            "description": scenario.get("description", ""),
            "status": "success",
            "effective_config": summary["effective_config_json"],
            "metrics": {key: summary[key] for key in summary.keys() if key not in {"group_name", "description", "status", "error", "effective_config_json", "detail_path"}},
        }

        group_dir = self.project_root / "reports" / "sensitivity_groups"
        group_dir.mkdir(parents=True, exist_ok=True)
        group_path = group_dir / f"{scenario_name}.json"
        details["output_file_path"] = str(group_path)
        group_path.write_text(json.dumps(details, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        summary["detail_path"] = str(group_path)
        return {"summary": summary, "details": details}

    def _build_summary_row(
        self,
        scenario_name: str,
        scenario: dict[str, Any],
        configs: dict[str, dict[str, Any]],
        bundle: MarketDataBundle,
        result: ExtendedBacktestResult,
    ) -> dict[str, Any]:
        trades = result.trades.copy()
        unfilled = result.unfilled_orders.copy()
        risk_records = result.risk_records.copy()
        snapshots = result.portfolio_snapshots.copy()
        monthly_records = result.monthly_records.copy()

        total_contribution = float(result.equity_curve["cumulative_contribution"].iloc[-1]) if not result.equity_curve.empty else 0.0
        total_invested_cash = float(trades["total_cash_out"].sum()) if not trades.empty and "total_cash_out" in trades.columns else 0.0
        total_uninvested_cash = float(result.equity_curve["cash"].iloc[-1]) if not result.equity_curve.empty and "cash" in result.equity_curve.columns else 0.0
        annualized_return = float(result.metrics.get("annualized_return", 0.0))
        annualized_volatility = float(result.metrics.get("annualized_volatility", 0.0))
        sharpe_like_ratio = annualized_return / annualized_volatility if annualized_volatility > 0 else 0.0
        win_month_ratio = self._win_month_ratio(result.equity_curve)
        avg_monthly_risk_flags = self._avg_monthly_risk_flags(risk_records)
        average_etf_weight, average_stock_weight, average_cash_weight = self._average_asset_weights(snapshots)
        average_weight_deviation, max_weight_deviation = self._weight_deviation_stats(snapshots)
        earliest_impact = self._earliest_symbol_unavailable_impact(bundle)
        paused_months = (
            pd.to_datetime(unfilled.loc[unfilled["reason"] == "paused_by_risk_rule", "date"]).dt.to_period("M").nunique()
            if not unfilled.empty and "reason" in unfilled.columns
            else 0
        )

        config_snapshot = {
            "data_mode": bundle.metadata.get("data_mode"),
            "backtest_range": {
                "start_date": configs["backtest"]["backtest"]["start_date"],
                "end_date": configs["backtest"]["backtest"]["end_date"],
            },
            "provider": bundle.metadata.get("provider"),
            "source_api": bundle.metadata.get("source_api"),
            "adjustment_mode": configs["app"]["efinance"]["adjustment_mode"],
            "transaction_cost": configs["backtest"]["transaction_cost"],
            "execution_rule": configs["backtest"]["backtest"]["execution_rule"],
            "risk_check_rule": configs["backtest"]["backtest"]["risk_check_rule"],
            "risk_thresholds": {
                "etf_yellow": configs["risk"]["etf"]["yellow_drawdown_from_high"],
                "etf_red": configs["risk"]["etf"]["red_drawdown_from_high"],
                "stock_yellow": configs["risk"]["stock"]["yellow_drawdown_from_cost"],
                "stock_red": configs["risk"]["stock"]["red_drawdown_from_cost"],
            },
        }

        return {
            "group_name": scenario_name,
            "description": scenario.get("description", ""),
            "status": "success",
            "error": "",
            "data_mode": bundle.metadata.get("data_mode"),
            "provider": bundle.metadata.get("provider"),
            "source_api": bundle.metadata.get("source_api"),
            "backtest_start_date": configs["backtest"]["backtest"]["start_date"],
            "backtest_end_date": configs["backtest"]["backtest"]["end_date"],
            "adjustment_mode": configs["app"]["efinance"]["adjustment_mode"],
            "monthly_buy_rule": configs["backtest"]["backtest"]["execution_rule"],
            "etf_yellow": configs["risk"]["etf"]["yellow_drawdown_from_high"],
            "etf_red": configs["risk"]["etf"]["red_drawdown_from_high"],
            "stock_yellow": configs["risk"]["stock"]["yellow_drawdown_from_cost"],
            "stock_red": configs["risk"]["stock"]["red_drawdown_from_cost"],
            "etf_slippage": configs["backtest"]["transaction_cost"]["etf"]["slippage"],
            "stock_slippage": configs["backtest"]["transaction_cost"]["stock"]["slippage"],
            "cumulative_return": float(result.metrics.get("total_return", 0.0)),
            "annualized_return": annualized_return,
            "max_drawdown": float(result.metrics.get("max_drawdown", 0.0)),
            "annualized_volatility": annualized_volatility,
            "sharpe_like_ratio": sharpe_like_ratio,
            "win_month_ratio": win_month_ratio,
            "total_invested_cash": total_invested_cash,
            "total_uninvested_cash": total_uninvested_cash,
            "invested_ratio": (total_invested_cash / total_contribution) if total_contribution > 0 else 0.0,
            "total_trade_count": int(len(trades)),
            "unfilled_count": int(len(unfilled)),
            "unfilled_amount": float(unfilled["recommended_amount"].sum()) if not unfilled.empty else 0.0,
            "total_yellow_triggers": int((risk_records["status"] == "YELLOW").sum()) if not risk_records.empty else 0,
            "total_red_triggers": int((risk_records["status"] == "RED").sum()) if not risk_records.empty else 0,
            "symbols_with_red": ",".join(sorted(risk_records.loc[risk_records["status"] == "RED", "symbol"].astype(str).unique())) if not risk_records.empty else "",
            "avg_monthly_risk_flags": avg_monthly_risk_flags,
            "average_etf_weight": average_etf_weight,
            "average_stock_weight": average_stock_weight,
            "average_cash_weight": average_cash_weight,
            "average_weight_deviation": average_weight_deviation,
            "max_weight_deviation": max_weight_deviation,
            "earliest_symbol_unavailable_impact": earliest_impact,
            "count_months_with_cash_drag": int((monthly_records["cash_after_trade"] > 0).sum()) if not monthly_records.empty else 0,
            "count_months_with_paused_buys": int(paused_months),
            "effective_config_json": json.dumps(config_snapshot, ensure_ascii=False),
            "detail_path": "",
        }

    @classmethod
    def _build_failed_summary(
        cls,
        scenario: dict[str, Any],
        base_configs: dict[str, dict[str, Any]],
        error: str,
    ) -> dict[str, Any]:
        return {
            "group_name": scenario["name"],
            "description": scenario.get("description", ""),
            "status": "failed",
            "error": error,
            "data_mode": "real",
            "provider": "",
            "source_api": "",
            "backtest_start_date": base_configs["backtest"]["backtest"]["start_date"],
            "backtest_end_date": base_configs["backtest"]["backtest"]["end_date"],
            "adjustment_mode": "",
            "monthly_buy_rule": "",
            "etf_yellow": None,
            "etf_red": None,
            "stock_yellow": None,
            "stock_red": None,
            "etf_slippage": None,
            "stock_slippage": None,
            "cumulative_return": None,
            "annualized_return": None,
            "max_drawdown": None,
            "annualized_volatility": None,
            "sharpe_like_ratio": None,
            "win_month_ratio": None,
            "total_invested_cash": None,
            "total_uninvested_cash": None,
            "invested_ratio": None,
            "total_trade_count": None,
            "unfilled_count": None,
            "unfilled_amount": None,
            "total_yellow_triggers": None,
            "total_red_triggers": None,
            "symbols_with_red": "",
            "avg_monthly_risk_flags": None,
            "average_etf_weight": None,
            "average_stock_weight": None,
            "average_cash_weight": None,
            "average_weight_deviation": None,
            "max_weight_deviation": None,
            "earliest_symbol_unavailable_impact": "",
            "count_months_with_cash_drag": None,
            "count_months_with_paused_buys": None,
            "effective_config_json": json.dumps(scenario.get("overrides", {}), ensure_ascii=False),
            "detail_path": "",
        }

    def _build_baseline_diff(self, summary_df: pd.DataFrame) -> pd.DataFrame:
        if summary_df.empty:
            return pd.DataFrame()
        baseline_name = self.configs["sensitivity"]["sensitivity"]["baseline"]["name"]
        baseline_rows = summary_df.loc[(summary_df["group_name"] == baseline_name) & (summary_df["status"] == "success")]
        if baseline_rows.empty:
            return pd.DataFrame()
        baseline = baseline_rows.iloc[0]
        rows: list[dict[str, Any]] = []
        for _, row in summary_df.iterrows():
            if row["status"] != "success":
                continue
            payload = {"group_name": row["group_name"]}
            for column in self.NUMERIC_DIFF_COLUMNS:
                payload[f"{column}_diff"] = float(row[column] - baseline[column]) if pd.notna(row[column]) and pd.notna(baseline[column]) else None
            rows.append(payload)
        return pd.DataFrame(rows)

    def _build_rankings(self, summary_df: pd.DataFrame) -> pd.DataFrame:
        success = summary_df.loc[summary_df["status"] == "success"].copy()
        if success.empty:
            return pd.DataFrame()
        success["return_rank"] = success["annualized_return"].rank(ascending=False, method="min")
        success["drawdown_rank"] = success["max_drawdown"].rank(ascending=True, method="min")
        success["cash_drag_rank"] = success["total_uninvested_cash"].rank(ascending=True, method="min")
        return success.sort_values(["return_rank", "drawdown_rank", "cash_drag_rank"])

    def _render_report(self, summary_df: pd.DataFrame, diff_df: pd.DataFrame) -> str:
        baseline_name = self.configs["sensitivity"]["sensitivity"]["baseline"]["name"]
        baseline_row = summary_df.loc[summary_df["group_name"] == baseline_name].iloc[0] if not summary_df.empty else pd.Series(dtype=object)
        success = summary_df.loc[summary_df["status"] == "success"].copy()
        failed = summary_df.loc[summary_df["status"] == "failed"].copy()

        lines = [
            "# 参数敏感性测试报告",
            "",
            "## 测试目的说明",
            "- 本轮不是寻优，而是稳健性检查。",
            "- 当前系统定位仍然是长期定投研究工具，不是短线择时或自动交易系统。",
            "",
            "## Baseline 配置摘要",
            self._dict_to_text(
                {
                    "group_name": baseline_row.get("group_name", ""),
                    "adjustment_mode": baseline_row.get("adjustment_mode", ""),
                    "etf_yellow": baseline_row.get("etf_yellow", ""),
                    "etf_red": baseline_row.get("etf_red", ""),
                    "stock_yellow": baseline_row.get("stock_yellow", ""),
                    "stock_red": baseline_row.get("stock_red", ""),
                    "monthly_buy_rule": baseline_row.get("monthly_buy_rule", ""),
                }
            ),
            "",
            "## 参数组列表",
            self._frame_to_text(summary_df[["group_name", "description", "adjustment_mode", "monthly_buy_rule", "status", "error"]]),
            "",
            "## 关键指标总表",
            self._frame_to_text(
                summary_df[
                    [
                        "group_name",
                        "annualized_return",
                        "max_drawdown",
                        "invested_ratio",
                        "total_red_triggers",
                        "unfilled_amount",
                        "average_weight_deviation",
                        "status",
                    ]
                ]
            ),
            "",
            "## 与 Baseline 的差异分析",
            self._dict_to_text(self._analyze_sensitivity(success, diff_df)),
            "",
            "## 结论与建议",
            self._render_conclusion(success, baseline_row),
            "",
            "## 失败组",
            self._frame_to_text(failed[["group_name", "description", "error"]]) if not failed.empty else "无失败组。",
            "",
            "## 限制说明",
            "- 结果受真实数据可用性影响。",
            "- 某些标的历史起点较晚，会影响资金利用率和现金拖累。",
            "- 当前仍是 MVP 级市场摩擦建模，不等于真实成交还原。",
            "- 当前未启用自动卖出，红线主要用于提醒、暂停新增和人工复核。",
        ]
        return "\n".join(lines)

    def _analyze_sensitivity(self, success_df: pd.DataFrame, diff_df: pd.DataFrame) -> dict[str, Any]:
        if success_df.empty or diff_df.empty:
            return {"note": "暂无可分析结果"}

        def _top(metric: str, ascending: bool = False) -> str:
            ranked = diff_df.dropna(subset=[metric]).copy()
            if ranked.empty:
                return ""
            ranked["abs_metric"] = ranked[metric].abs()
            row = ranked.sort_values("abs_metric", ascending=ascending).iloc[-1]
            return f"{row['group_name']} ({metric}={row[metric]:.6f})"

        stable_candidates = diff_df.copy()
        if stable_candidates.empty:
            low_impact = ""
        else:
            stable_candidates["stability_score"] = (
                stable_candidates["annualized_return_diff"].abs().fillna(0)
                + stable_candidates["max_drawdown_diff"].abs().fillna(0)
                + stable_candidates["unfilled_amount_diff"].abs().fillna(0) / 100000
            )
            low_impact = str(stable_candidates.sort_values("stability_score").iloc[0]["group_name"])

        return {
            "收益最敏感参数组": _top("annualized_return_diff"),
            "最大回撤最敏感参数组": _top("max_drawdown_diff"),
            "红线触发最敏感参数组": _top("total_red_triggers_diff"),
            "现金拖累最敏感参数组": _top("total_uninvested_cash_diff"),
            "影响较小的参数组": low_impact,
        }

    @staticmethod
    def _render_conclusion(success_df: pd.DataFrame, baseline_row: pd.Series) -> str:
        if success_df.empty:
            return "可用结果为空，无法形成结论。"
        baseline_return = float(baseline_row.get("annualized_return", 0.0))
        baseline_drawdown = float(baseline_row.get("max_drawdown", 0.0))
        keep_forward = "建议保留 forward 作为默认复权模式。"
        if "adj_none" in success_df["group_name"].tolist():
            adj_none = success_df.loc[success_df["group_name"] == "adj_none"].iloc[0]
            if float(adj_none["max_drawdown"]) < baseline_drawdown and float(adj_none["annualized_return"]) >= baseline_return:
                keep_forward = "不复权结果也值得继续观察，但当前不建议直接替换 forward 默认值。"
        return "\n".join(
            [
                f"- baseline 年化收益 {baseline_return:.4f}，最大回撤 {baseline_drawdown:.4f}。",
                f"- {keep_forward}",
                f"- 基准月度买入规则当前为 {baseline_row.get('monthly_buy_rule', '')}，如无明显收益/回撤优势，不建议轻易改成其他规则。",
                "- 红线阈值若明显增加现金拖累或红线次数，说明参数可能过紧；若回撤显著放大，则说明参数可能过松。",
            ]
        )

    @staticmethod
    def _win_month_ratio(equity_curve: pd.DataFrame) -> float:
        if equity_curve.empty:
            return 0.0
        frame = equity_curve.copy()
        frame["date"] = pd.to_datetime(frame["date"])
        monthly_nav = frame.groupby(frame["date"].dt.to_period("M"))["unit_nav"].last().pct_change().dropna()
        if monthly_nav.empty:
            return 0.0
        return float((monthly_nav > 0).mean())

    @staticmethod
    def _avg_monthly_risk_flags(risk_records: pd.DataFrame) -> float:
        if risk_records.empty:
            return 0.0
        flagged = risk_records.loc[risk_records["status"].isin(["YELLOW", "RED"])].copy()
        if flagged.empty:
            return 0.0
        flagged["month"] = pd.to_datetime(flagged["date"]).dt.to_period("M").astype(str)
        return float(flagged.groupby("month").size().mean())

    @staticmethod
    def _average_asset_weights(snapshots: pd.DataFrame) -> tuple[float, float, float]:
        if snapshots.empty:
            return 0.0, 0.0, 0.0
        grouped = snapshots.groupby(["date", "asset_type"], as_index=False)["current_weight"].sum()
        pivot = grouped.pivot(index="date", columns="asset_type", values="current_weight").fillna(0.0)
        cash_weight = (snapshots.groupby("date").first()["cash"] / snapshots.groupby("date").first()["total_value"]).fillna(0.0)
        return (
            float(pivot.get("etf", pd.Series(dtype=float)).mean()) if "etf" in pivot else 0.0,
            float(pivot.get("stock", pd.Series(dtype=float)).mean()) if "stock" in pivot else 0.0,
            float(cash_weight.mean()) if not cash_weight.empty else 0.0,
        )

    @staticmethod
    def _weight_deviation_stats(snapshots: pd.DataFrame) -> tuple[float, float]:
        if snapshots.empty:
            return 0.0, 0.0
        deviation = snapshots["weight_gap"].astype(float).abs()
        return float(deviation.mean()), float(deviation.max())

    @staticmethod
    def _earliest_symbol_unavailable_impact(bundle: MarketDataBundle) -> str:
        diagnostics = bundle.diagnostics.copy()
        if diagnostics.empty or "start_date" not in diagnostics.columns or not bundle.calendar:
            return ""
        first_trade_day = pd.Timestamp(bundle.calendar[0]).strftime("%Y-%m-%d")
        impacted = diagnostics.loc[diagnostics["start_date"].astype(str) > first_trade_day]
        if impacted.empty:
            return ""
        row = impacted.sort_values("start_date").iloc[0]
        return f"{row['symbol']}:{row['start_date']}"

    @staticmethod
    def _deep_merge(target: dict[str, Any], override: dict[str, Any]) -> None:
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                SensitivityEngine._deep_merge(target[key], value)
            else:
                target[key] = value

    @staticmethod
    def _frame_to_text(frame: pd.DataFrame) -> str:
        if frame.empty:
            return "无"
        return "```text\n" + frame.to_csv(index=False) + "```"

    @staticmethod
    def _dict_to_text(data: dict[str, Any]) -> str:
        if not data:
            return "无"
        return "\n".join([f"- {key}: {value}" for key, value in data.items()])
