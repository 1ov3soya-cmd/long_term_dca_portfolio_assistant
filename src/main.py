"""项目主入口。"""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.agent_research.monthly_research_service import MonthlyResearchService
from src.agent_research.research_memo_generator import ResearchMemoGenerator
from src.agent_research.research_snapshot_writer import ResearchSnapshotWriter
from src.agent_research.tradingagents_bridge import TradingAgentsBridge
from src.backtest_engine import MVPBacktestEngine
from src.data_loader import MarketDataLoader
from src.frontend_snapshot_builder import FrontendSnapshotBuilder
from src.manual_risk_acceptance import ManualRiskAcceptanceHelper
from src.manual_risk_manager import ManualRiskFlagManager
from src.portfolio import PortfolioState, build_target_table
from src.report_generator import ReportGenerator
from src.run_compare_engine import RunCompareEngine
from src.robustness_engine import RobustnessEngine
from src.run_archive_service import RunArchiver
from src.signal_engine import SignalEngine
from src.sensitivity_engine import SensitivityEngine
from src.utils.logger import get_logger
from src.validation_engine import ValidationEngine


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数。"""

    parser = argparse.ArgumentParser(description="长期定投组合助手")
    parser.add_argument(
        "command",
        choices=[
            "update-data",
            "suggest",
            "backtest",
            "demo",
            "validate-data",
            "validate-backtest",
            "sensitivity-test",
            "summarize-robustness",
            "validate-manual-risk-flags",
            "compare-runs",
            "run-agent-research",
            "run-monthly-research",
            "build-frontend-snapshot",
        ],
        help="执行命令",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help="可选：覆盖配置中的截止日期，格式 YYYY-MM-DD",
    )
    parser.add_argument(
        "--manual-risk-file",
        default=None,
        help="可选：运行时覆盖人工逻辑红线文件，避免直接修改正式配置",
    )
    parser.add_argument(
        "--symbol",
        default=None,
        help="run-agent-research 专用：指定股票池内的股票代码，例如 600519",
    )
    parser.add_argument(
        "--run-a",
        default=None,
        help="compare-runs 专用：第一个 run_id 或 run_path",
    )
    parser.add_argument(
        "--run-b",
        default=None,
        help="compare-runs 专用：第二个 run_id 或 run_path",
    )
    parser.add_argument(
        "--latest",
        default=None,
        help="compare-runs 可选：比较某类命令最近两次运行，例如 backtest",
    )
    parser.add_argument(
        "--suggest-run",
        default=None,
        help="run-monthly-research 可选：显式指定 source suggest run_id",
    )
    parser.add_argument(
        "--brief",
        action="store_true",
        help="compare-runs 可选：仅输出关键差异摘要",
    )
    return parser


def apply_manual_risk_file_override(configs: dict[str, dict], manual_risk_file: str | None) -> dict[str, dict]:
    """在运行时覆盖人工逻辑红线文件，不改动正式配置文件。"""

    if not manual_risk_file:
        return configs
    configs.setdefault("universe", {}).setdefault("manual_flags", {})["logic_risk_flag_file"] = manual_risk_file
    return configs


def _write_manual_flag_validation_report(project_root: Path, result: dict) -> dict[str, Path]:
    """落盘人工逻辑红线校验报告。"""

    out_dir = project_root / "reports" / "manual"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "manual_risk_flags_validation.csv"
    json_path = out_dir / "manual_risk_flags_validation.json"
    md_path = out_dir / "manual_risk_flags_validation.md"

    issues = result["issues"] if not result["issues"].empty else result["issues"].reindex(columns=["symbol", "level", "message"])
    flags = result["flags"] if not result["flags"].empty else result["flags"].reindex(columns=["symbol", "asset_type", "effective_from", "manual_pause_buy", "manual_force_review", "thesis_broken"])
    issues.to_csv(csv_path, index=False, encoding="utf-8-sig")
    json_path.write_text(
        json.dumps(
            {
                "valid": result["valid"],
                "issues": issues.to_dict(orient="records"),
                "flags": flags.to_dict(orient="records"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    lines = [
        "# 人工逻辑红线校验报告",
        "",
        f"- valid: {result['valid']}",
        f"- flag_count: {len(flags)}",
        f"- issue_count: {len(issues)}",
        "",
        "## 当前人工逻辑红线状态",
        "```text",
        flags.to_csv(index=False).strip() if not flags.empty else "无人工逻辑红线记录",
        "```",
        "",
        "## 校验问题",
        "```text",
        issues.to_csv(index=False).strip() if not issues.empty else "无校验问题",
        "```",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"markdown": md_path, "csv": csv_path, "json": json_path}


def _to_jsonable_args(args: argparse.Namespace) -> dict[str, Any]:
    """将 CLI 参数转换为可归档结构。"""

    return {
        "command": args.command,
        "end_date": args.end_date,
        "manual_risk_file": args.manual_risk_file,
        "symbol": getattr(args, "symbol", None),
        "run_a": getattr(args, "run_a", None),
        "run_b": getattr(args, "run_b", None),
        "latest": getattr(args, "latest", None),
        "suggest_run": getattr(args, "suggest_run", None),
        "brief": bool(getattr(args, "brief", False)),
        "all_args": vars(args),
    }


def _runtime_meta_from_configs(configs: dict[str, dict[str, Any]], end_date: str | None) -> dict[str, Any]:
    """从配置层构建初始运行元信息。"""

    return {
        "end_date": end_date,
        "data_mode": "",
        "provider_name": configs.get("app", {}).get("runtime", {}).get("data_provider", ""),
        "adj_mode": configs.get("app", {}).get("efinance", {}).get("adjustment_mode", ""),
        "manual_risk_file": configs.get("universe", {}).get("manual_flags", {}).get("logic_risk_flag_file", ""),
    }


def _count_true(frame: pd.DataFrame, column: str) -> int:
    """统计布尔列中 True 的数量。"""

    if frame.empty or column not in frame.columns:
        return 0
    return int(frame[column].fillna(False).astype(bool).sum())


def _safe_last(frame: pd.DataFrame, column: str) -> float:
    """安全读取最后一行数值列。"""

    if frame.empty or column not in frame.columns:
        return 0.0
    return float(frame[column].iloc[-1])


def _build_suggest_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """提取 suggest 命令的关键摘要。"""

    recommendation = payload["recommendation"]
    frame = recommendation.to_frame()
    return {
        "total_budget": float(recommendation.total_budget),
        "etf_budget": float(recommendation.etf_budget),
        "stock_budget": float(recommendation.stock_budget),
        "symbols_to_buy_count": int((frame["recommended_amount"] > 0).sum())
        if not frame.empty and "recommended_amount" in frame.columns
        else 0,
        "paused_symbols_count": _count_true(frame, "pause_buy"),
        "force_review_symbols_count": _count_true(frame, "manual_force_review"),
        "thesis_broken_symbols_count": _count_true(frame, "thesis_broken"),
    }


def _build_backtest_summary(result: Any) -> dict[str, Any]:
    """提取 backtest 命令的关键摘要。"""

    trades = result.trades.copy()
    unfilled = result.unfilled_orders.copy()
    risks = result.risk_records.copy()
    total_invested_cash = (
        float(trades["total_cash_out"].sum())
        if not trades.empty and "total_cash_out" in trades.columns
        else 0.0
    )
    return {
        "cumulative_return": float(result.metrics.get("cumulative_return", 0.0)),
        "annualized_return": float(result.metrics.get("annualized_return", 0.0)),
        "max_drawdown": float(result.metrics.get("max_drawdown", 0.0)),
        "total_invested_cash": total_invested_cash,
        "total_uninvested_cash": _safe_last(result.equity_curve, "cash"),
        "unfilled_count": int(len(unfilled)),
        "total_yellow_triggers": int((risks["status"] == "YELLOW").sum())
        if not risks.empty and "status" in risks.columns
        else 0,
        "total_red_triggers": int((risks["status"] == "RED").sum())
        if not risks.empty and "status" in risks.columns
        else 0,
    }


def _build_validate_data_summary(result: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """提取 validate-data 命令的关键摘要与告警。"""

    summary = result["summary"].copy()
    warnings: list[str] = []
    missing_symbols = (
        int((summary["price_missing_rows"] > 0).sum())
        if not summary.empty and "price_missing_rows" in summary.columns
        else 0
    )
    duplicate_symbols = (
        int((summary["duplicate_dates"] > 0).sum())
        if not summary.empty and "duplicate_dates" in summary.columns
        else 0
    )
    short_history_symbols = (
        int((~summary["coverage_start_ok"]).sum())
        if not summary.empty and "coverage_start_ok" in summary.columns
        else 0
    )
    if missing_symbols:
        warnings.append(f"共有 {missing_symbols} 个标的存在价格缺失行。")
    if duplicate_symbols:
        warnings.append(f"共有 {duplicate_symbols} 个标的存在重复日期。")
    if short_history_symbols:
        warnings.append(f"共有 {short_history_symbols} 个标的未覆盖回测起点。")
    return (
        {
            "symbols_checked": int(len(summary)),
            "symbols_with_missing_data": missing_symbols,
            "symbols_with_duplicate_dates": duplicate_symbols,
            "symbols_with_short_history": short_history_symbols,
            "validation_status": "pass_with_warnings" if warnings else "pass",
        },
        warnings,
    )


def _build_validate_backtest_summary(result: dict[str, Any]) -> dict[str, Any]:
    """提取 validate-backtest 命令的关键摘要。"""

    monthly = result["monthly_check"]
    weekly = result["weekly_check"]
    redline = result["redline_stats"].copy()
    unfilled = result["unfilled_summary"].copy()
    return {
        "monthly_execution_matched": bool(monthly.get("all_matched", False)),
        "weekly_execution_matched": bool(weekly.get("all_matched", False)),
        "auto_add_violation_count": int(
            redline["auto_add_violation"].fillna(False).astype(bool).sum()
        )
        if not redline.empty and "auto_add_violation" in redline.columns
        else 0,
        "unfilled_category_count": int(len(unfilled)),
    }


def _build_sensitivity_summary(result: dict[str, Any]) -> tuple[dict[str, Any], str, list[str]]:
    """提取 sensitivity-test 命令的关键摘要，并判断归档状态。"""

    summary = result["summary"].copy()
    diff = result["baseline_diff"].copy()
    success_count = (
        int((summary["status"] == "success").sum())
        if not summary.empty and "status" in summary.columns
        else 0
    )
    failed_count = (
        int((summary["status"] == "failed").sum())
        if not summary.empty and "status" in summary.columns
        else 0
    )
    warnings: list[str] = []
    if failed_count:
        warnings.append(f"参数敏感性测试共有 {failed_count} 个参数组失败，已按 partial 归档。")

    most_sensitive_parameter = ""
    if not diff.empty:
        sensitivity_candidates = {
            "adjustment_mode": float(diff["annualized_return_diff"].abs().max())
            if "annualized_return_diff" in diff.columns
            else 0.0,
            "etf_redline": float(diff["total_red_triggers_diff"].abs().max())
            if "total_red_triggers_diff" in diff.columns
            else 0.0,
            "stock_redline": float(diff["max_drawdown_diff"].abs().max())
            if "max_drawdown_diff" in diff.columns
            else 0.0,
            "monthly_buy_rule": float(diff["invested_ratio_diff"].abs().max())
            if "invested_ratio_diff" in diff.columns
            else 0.0,
        }
        most_sensitive_parameter = max(sensitivity_candidates, key=sensitivity_candidates.get)

    status = "partial" if success_count > 0 and failed_count > 0 else "success"
    if success_count == 0 and failed_count > 0:
        status = "failed"
    return (
        {
            "groups_total": int(len(summary)),
            "groups_success": success_count,
            "groups_failed": failed_count,
            "most_sensitive_parameter": most_sensitive_parameter,
            "baseline_label": "baseline",
        },
        status,
        warnings,
    )


def _build_robustness_summary(result: dict[str, Any]) -> tuple[dict[str, Any], str, list[str]]:
    """提取 summarize-robustness 命令的关键摘要。"""

    payload = result.get("payload", {})
    recommendations = payload.get("default_parameter_recommendations", {})
    context = payload.get("summary_context", {})
    failed_group_count = int(context.get("failed_group_count", 0))
    warnings: list[str] = []
    if not payload:
        warnings.append("稳健性摘要返回结构未包含 payload，已仅按输出路径归档。")
    if failed_group_count:
        warnings.append(f"稳健性结论基于部分敏感性测试结果，失败组数量: {failed_group_count}。")
    status = "partial" if failed_group_count > 0 else "success"
    return (
        {
            "baseline_assessment": payload.get("baseline_assessment", {}).get("label", ""),
            "keep_forward_default": recommendations.get("adjustment_mode", {}).get("label", ""),
            "keep_first_trading_day_default": recommendations.get("monthly_buy_rule", {}).get("label", ""),
            "etf_risk_rule_recommendation": recommendations.get("etf_redline", {}).get("label", ""),
            "stock_risk_rule_recommendation": recommendations.get("stock_redline", {}).get("label", ""),
        },
        status,
        warnings,
    )


def _build_manual_flag_summary(
    result: dict[str, Any],
    preview: pd.DataFrame,
    end_date: str,
) -> dict[str, Any]:
    """提取 validate-manual-risk-flags 命令的关键摘要。"""

    end_ts = pd.Timestamp(end_date)
    effective_count = 0
    if not preview.empty and "effective_from" in preview.columns:
        effective_count = int(
            pd.to_datetime(preview["effective_from"], errors="coerce")
            .le(end_ts)
            .fillna(False)
            .sum()
        )
    return {
        "symbols_flagged": int(len(result["flags"])),
        "pause_buy_count": _count_true(preview, "manual_pause_buy"),
        "force_review_count": _count_true(preview, "manual_force_review"),
        "thesis_broken_count": _count_true(preview, "thesis_broken"),
        "effective_in_range_count": effective_count,
    }


def _build_compare_run_summary(result: dict[str, Any]) -> dict[str, Any]:
    """提取 compare-runs 命令的关键摘要。"""

    summary = result["compare_summary"]
    return {
        "comparable_level": result["compare_manifest"]["comparable_level"],
        "compare_status": result["compare_manifest"]["compare_status"],
        "manual_risk_changed": bool(summary.get("manual_risk_changed", False)),
        "adj_mode_changed": bool(summary.get("adj_mode_changed", False)),
        "data_mode_changed": bool(summary.get("data_mode_changed", False)),
        "top_attention_points_count": int(len(summary.get("top_attention_points", []))),
    }


def _build_agent_research_summary(result: dict[str, Any]) -> dict[str, Any]:
    """提取 run-agent-research 命令的关键摘要。"""

    research = result["research"]
    return {
        "symbol": research.symbol,
        "analysis_date": research.analysis_date,
        "final_research_label": research.final_research_label,
        "suggest_manual_pause_buy": bool(research.suggest_manual_pause_buy),
        "suggest_force_review": bool(research.suggest_force_review),
        "suggest_thesis_broken": bool(research.suggest_thesis_broken),
        "confidence": float(research.confidence),
        "source": research.source,
    }


def _build_monthly_research_summary(result: dict[str, Any]) -> dict[str, Any]:
    """提取 run-monthly-research 命令的关键摘要。"""

    summary = result["summary"]
    return {
        "batch_id": summary.get("batch_id", ""),
        "source_suggest_run": summary.get("source_suggest_run", ""),
        "total_targets": int(summary.get("total_targets", 0)),
        "processed_targets": int(summary.get("processed_targets", 0)),
        "pause_candidate_count": int(summary.get("pause_candidate_count", 0)),
        "force_review_candidate_count": int(summary.get("force_review_candidate_count", 0)),
        "thesis_broken_candidate_count": int(summary.get("thesis_broken_candidate_count", 0)),
        "average_confidence": float(summary.get("average_confidence", 0.0)),
        "top_attention_symbols": list(summary.get("top_attention_symbols", [])),
    }


def run_cli(args: argparse.Namespace, project_root: Path | None = None) -> None:
    """执行单次 CLI 运行，并自动写出归档快照。"""

    project_root = project_root or Path(__file__).resolve().parents[1]
    logger = get_logger("main")
    loader = MarketDataLoader(project_root)
    configs = apply_manual_risk_file_override(deepcopy(loader.configs), args.manual_risk_file)
    archiver = RunArchiver(configs, project_root)
    run_context = archiver.start_run(args.command)
    cli_args = _to_jsonable_args(args)
    effective_snapshot: dict[str, Any] = {}

    output_artifacts: dict[str, Any] = {}
    key_summary: dict[str, Any] = {}
    notes: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []
    status = "success"
    runtime_meta = _runtime_meta_from_configs(configs, args.end_date)

    try:
        start_date = configs["backtest"]["backtest"]["start_date"]
        configured_end_date = args.end_date or configs["backtest"]["backtest"]["end_date"]
        configs["backtest"]["backtest"]["end_date"] = configured_end_date
        effective_snapshot = archiver.build_effective_config_snapshot()
        runtime_meta["end_date"] = configured_end_date
        runtime_meta["manual_risk_file"] = configs["universe"]["manual_flags"]["logic_risk_flag_file"]

        if args.command == "build-frontend-snapshot":
            builder = FrontendSnapshotBuilder(project_root=project_root, configs=configs)
            result = builder.build(end_date=configured_end_date)
            key_summary = {
                "snapshot_version": "1.0",
                "generated_at": result["generated_at"],
                "warnings_count": len(result["warnings"]),
                "snapshot_files_count": len(result["paths"]),
            }
            output_artifacts = {"frontend_snapshot": result["paths"]}
            runtime_meta["data_mode"] = "static_snapshot"
            runtime_meta["provider_name"] = "frontend_snapshot_builder"
            notes.extend(
                [
                    "该命令只聚合既有归档为前端静态快照，不重跑策略、不改配置、不生成交易执行。",
                    "生成结果位于 frontend/public/data，可随 frontend build 一起部署为静态网站。",
                ]
            )
            warnings.extend(result["warnings"])
            logger.info("前端静态快照已输出: %s", result["data_dir"])
            return

        if args.command == "compare-runs":
            compare_engine = RunCompareEngine(
                project_root=project_root,
                log_level=configs["app"]["runtime"]["log_level"],
            )
            result = compare_engine.compare_runs(
                run_a=args.run_a,
                run_b=args.run_b,
                latest_command=args.latest,
                brief=bool(args.brief),
            )
            key_summary = _build_compare_run_summary(result)
            output_artifacts = result["paths"]
            notes.append("run compare 仅比较已有归档结果，不会重跑回测或改动主策略逻辑。")
            logger.info("运行结果对比报告已输出: %s", result["paths"]["compare_report"])
            return

        if args.command == "run-agent-research":
            if not args.symbol:
                raise ValueError("run-agent-research 需要传入 --symbol，例如 600519。")

            bridge = TradingAgentsBridge(project_root=project_root, configs=configs)
            research = bridge.run_symbol_research(
                symbol=args.symbol,
                analysis_date=configured_end_date,
            )
            memo_generator = ResearchMemoGenerator()
            writer = ResearchSnapshotWriter(project_root)
            memo_markdown = memo_generator.render(research)
            paths = writer.write(
                research,
                memo_markdown,
                source_run_id=run_context["run_id"] if run_context else "",
            )

            key_summary = _build_agent_research_summary({"research": research})
            output_artifacts = {"agent_research": paths}
            runtime_meta["data_mode"] = "research_only"
            runtime_meta["provider_name"] = research.source
            notes.extend(
                [
                    "TradingAgents PoC 当前为研究增强层，不直接输出交易执行动作。",
                    "本次研究结果不会自动改写正式 manual risk flags，需要人工确认后再采纳。",
                    "第一版仅分析股票增强仓，不分析 ETF 主底仓。",
                ]
            )
            logger.info("Agent research JSON 已输出: %s", paths["json"])
            logger.info("Agent research memo 已输出: %s", paths["markdown"])
            return

        if args.command == "run-monthly-research":
            service = MonthlyResearchService(project_root=project_root, configs=configs)
            result = service.run(
                end_date=configured_end_date,
                source_research_run_id=run_context["run_id"] if run_context else "",
                suggest_run_id=getattr(args, "suggest_run", None),
            )

            key_summary = _build_monthly_research_summary(result)
            output_artifacts = {"monthly_research": result["paths"]}
            runtime_meta["data_mode"] = "research_only"
            runtime_meta["provider_name"] = "monthly_research_debate"
            notes.extend(
                [
                    "Monthly research debate 只围绕某次月度建议清单生成研究增强摘要。",
                    "本批次输出不会自动改写 manual risk flags，也不会自动执行交易。",
                    "股票增强仓使用 TradingAgents PoC；ETF 底仓使用中性占位研究摘要。",
                ]
            )
            logger.info("Monthly research summary 已输出: %s", result["paths"]["monthly_research_summary"])
            logger.info("Monthly research items 已输出: %s", result["paths"]["debate_items"])
            logger.info("Monthly research report 已输出: %s", result["paths"]["monthly_research_report"])
            return

        target_table = build_target_table(configs["portfolio"])
        report_generator = ReportGenerator(project_root)
        validation_engine = ValidationEngine(configs, project_root)
        sensitivity_engine = SensitivityEngine(configs, project_root)
        robustness_engine = RobustnessEngine(configs, project_root)
        acceptance_helper = ManualRiskAcceptanceHelper(configs, project_root)

        if args.command == "sensitivity-test":
            result = sensitivity_engine.run(end_date=configured_end_date)
            key_summary, status, sensitivity_warnings = _build_sensitivity_summary(result)
            warnings.extend(sensitivity_warnings)
            output_artifacts = result["paths"]
            if not result["summary"].empty:
                runtime_meta["data_mode"] = str(result["summary"].iloc[0].get("data_mode", ""))
                runtime_meta["provider_name"] = str(result["summary"].iloc[0].get("provider", runtime_meta["provider_name"]))
                runtime_meta["adj_mode"] = str(result["summary"].iloc[0].get("adjustment_mode", runtime_meta["adj_mode"]))
            notes.append("本次未重跑策略逻辑，仅复用现有低频回测器进行参数扰动测试。")
            logger.info("参数敏感性测试汇总已输出: %s", result["paths"]["report"])
            return

        if args.command == "summarize-robustness":
            result = robustness_engine.summarize(end_date=configured_end_date)
            key_summary, status, robustness_warnings = _build_robustness_summary(result)
            warnings.extend(robustness_warnings)
            output_artifacts = result["paths"]
            baseline_cfg = result.get("payload", {}).get("baseline_configuration", {})
            runtime_meta["data_mode"] = str(baseline_cfg.get("data_mode", ""))
            runtime_meta["provider_name"] = str(baseline_cfg.get("provider", runtime_meta["provider_name"]))
            runtime_meta["adj_mode"] = str(baseline_cfg.get("adjustment_mode", runtime_meta["adj_mode"]))
            notes.append("稳健性总结基于 sensitivity-test 既有输出生成。")
            logger.info("稳健性摘要已输出: %s", result["paths"]["summary_markdown"])
            logger.info("默认参数建议已输出: %s", result["paths"]["recommendation_markdown"])
            return

        if args.command == "validate-manual-risk-flags":
            manual_risk_file = configs["universe"]["manual_flags"]["logic_risk_flag_file"]
            manager = ManualRiskFlagManager(
                project_root / manual_risk_file,
                project_root / configs["universe"]["manual_flags"]["thesis_flag_file"],
            )
            result = manager.validate(target_table)
            paths = _write_manual_flag_validation_report(project_root, result)
            acceptance_paths = acceptance_helper.write_acceptance_artifacts(
                validation_result=result,
                target_table=target_table,
                manual_risk_file=manual_risk_file,
                end_date=configured_end_date,
            )
            preview = acceptance_helper.build_preview_table(target_table, manual_risk_file, configured_end_date)
            key_summary = _build_manual_flag_summary(result, preview, configured_end_date)
            output_artifacts = {
                "validation_report": paths,
                "acceptance_artifacts": acceptance_paths,
            }
            if not bool(result["valid"]):
                warnings.append("人工逻辑红线配置存在校验问题，请先处理后再进入正式建议或回测。")
                status = "partial"
            logger.info("人工逻辑红线校验报告已输出: %s", paths["markdown"])
            logger.info("人工逻辑红线验收报告已输出: %s", acceptance_paths["report_markdown"])
            logger.info("人工逻辑红线验收清单已输出: %s", acceptance_paths["checklist_markdown"])
            return

        mode = "demo" if args.command == "demo" else "real"
        bundle = loader.load_market_data_bundle(
            start_date=start_date,
            end_date=configured_end_date,
            mode=mode,
        )
        histories = bundle.histories
        runtime_meta.update(
            {
                "data_mode": bundle.metadata.get("data_mode", mode),
                "provider_name": bundle.metadata.get("provider", runtime_meta["provider_name"]),
                "adj_mode": bundle.metadata.get("adjustment_mode", runtime_meta["adj_mode"]),
            }
        )

        holdings_path = project_root / configs["universe"]["manual_flags"]["holdings_file"]
        portfolio = PortfolioState.from_csv(holdings_path)

        if args.command in {"update-data", "demo"}:
            logger.info(
                "数据更新完成，模式=%s，标的数=%s，最新数据日期=%s",
                bundle.metadata.get("data_mode"),
                len(histories),
                bundle.metadata.get("latest_data_date"),
            )
            key_summary = {
                "symbols_loaded": int(len(histories)),
                "latest_data_date": bundle.metadata.get("latest_data_date", ""),
                "data_mode": bundle.metadata.get("data_mode", mode),
            }
            notes.append("该命令以数据更新为主，不生成回测或稳健性分析结果。")
            if args.command == "update-data":
                return

        if args.command == "validate-data":
            result = validation_engine.validate_data(
                data_bundle=bundle,
                target_table=target_table,
                start_date=start_date,
                end_date=configured_end_date,
            )
            key_summary, validation_warnings = _build_validate_data_summary(result)
            warnings.extend(validation_warnings)
            output_artifacts = result["paths"]
            logger.info("数据验收报告已输出: %s", result["paths"]["markdown"])
            return

        if args.command in {"suggest", "demo"}:
            signal_engine = SignalEngine(configs, project_root)
            payload = signal_engine.generate_monthly_recommendation(
                as_of_date=bundle.metadata.get("as_of_date", configured_end_date),
                histories=histories,
                portfolio_state=portfolio,
                target_table=target_table,
            )
            monthly_paths = report_generator.save_monthly_report(
                recommendation=payload["recommendation"],
                current_table=payload["current_table"],
                risk_table=payload["risk_table"],
                data_bundle=bundle,
                config_summary=bundle.metadata.get("config_summary", {}),
                portfolio_cash=portfolio.cash,
            )
            key_summary = _build_suggest_summary(payload)
            output_artifacts = {"monthly_report": monthly_paths}
            logger.info("月度建议报告已输出: %s", monthly_paths["markdown"])
            if args.command == "suggest":
                return

        if args.command in {"backtest", "demo", "validate-backtest"}:
            backtest_engine = MVPBacktestEngine(configs, project_root)
            result = backtest_engine.run(histories, target_table, data_bundle=bundle)
            backtest_paths = report_generator.save_backtest_report(
                result,
                data_bundle=bundle,
                config_summary=bundle.metadata.get("config_summary", {}),
            )
            key_summary = _build_backtest_summary(result)
            output_artifacts = {"backtest_report": backtest_paths}
            logger.info("回测报告已输出: %s", backtest_paths["markdown"])

            if args.command == "validate-backtest":
                validation_paths = validation_engine.validate_backtest(
                    backtest_result=result,
                    data_bundle=bundle,
                    target_table=target_table,
                )
                key_summary = _build_validate_backtest_summary(validation_paths)
                output_artifacts["backtest_validation"] = validation_paths["paths"]
                logger.info("回测一致性报告已输出: %s", validation_paths["paths"]["markdown"])

    except Exception as exc:  # noqa: BLE001
        status = "failed"
        errors.append(str(exc))
        logger.exception("命令执行失败: %s", args.command)
        raise
    finally:
        archiver.finalize(
            run_context=run_context,
            cli_args=cli_args,
            effective_config_snapshot=effective_snapshot,
            output_artifacts=output_artifacts,
            key_summary=key_summary,
            notes=notes,
            status=status,
            runtime_meta=runtime_meta,
            warnings=warnings,
            errors=errors,
        )


def main() -> None:
    """程序入口。"""

    run_cli(build_parser().parse_args())


if __name__ == "__main__":
    main()
