from copy import deepcopy
from pathlib import Path
import shutil
import sys
from unittest.mock import patch
import uuid

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest_engine import MVPBacktestEngine
from src.data_loader import MarketDataLoader
from src.portfolio import build_target_table
from src.sensitivity_engine import SensitivityEngine


TMP_ROOT = PROJECT_ROOT / ".pytest_tmp"
TMP_ROOT.mkdir(parents=True, exist_ok=True)


def _make_configs() -> dict:
    return {
        "app": {
            "runtime": {"log_level": "INFO", "cache_format": "csv", "data_provider": "efinance", "max_retry": 1, "retry_sleep_seconds": 0.0},
            "efinance": {"adjustment_mode": "forward", "preferred_history_api": "stock"},
            "schedule": {"monthly_invest_day_rule": "first_trading_day", "weekly_risk_check_rule": "last_trading_day_of_week"},
            "paths": {"cache_data_dir": "data/cache"},
        },
        "portfolio": {
            "portfolio": {"monthly_budget": 10000.0},
            "asset_allocation": {"etf_total_weight": 0.8, "stock_total_weight": 0.2},
            "etf_pool": [
                {"symbol": "510300", "name": "ETF_A", "target_weight": 0.3},
                {"symbol": "510500", "name": "ETF_B", "target_weight": 0.2},
                {"symbol": "515180", "name": "ETF_C", "target_weight": 0.2},
                {"symbol": "518880", "name": "ETF_D", "target_weight": 0.1},
            ],
            "stock_pool": [
                {"symbol": "600519", "name": "STOCK_A", "target_weight": 0.04},
                {"symbol": "000858", "name": "STOCK_B", "target_weight": 0.04},
                {"symbol": "600036", "name": "STOCK_C", "target_weight": 0.04},
                {"symbol": "000333", "name": "STOCK_D", "target_weight": 0.04},
                {"symbol": "601318", "name": "STOCK_E", "target_weight": 0.04},
            ],
        },
        "risk": {
            "risk": {"moving_average_window": 5},
            "etf": {"yellow_drawdown_from_high": 0.15, "red_drawdown_from_high": 0.25, "weakness_days": 3},
            "stock": {"yellow_drawdown_from_cost": 0.12, "red_drawdown_from_cost": 0.20},
            "portfolio": {"red_max_drawdown": 0.20},
        },
        "backtest": {
            "backtest": {
                "start_date": "2024-01-01",
                "end_date": "2024-03-31",
                "initial_cash": 0.0,
                "monthly_budget": 10000.0,
                "execution_rule": "first_trading_day",
                "risk_check_rule": "last_trading_day_of_week",
            },
            "transaction_cost": {
                "etf": {"buy_commission": 0.0003, "sell_commission": 0.0003, "sell_stamp_tax": 0.0, "slippage": 0.001},
                "stock": {"buy_commission": 0.0003, "sell_commission": 0.0003, "sell_stamp_tax": 0.001, "slippage": 0.002},
            },
            "trading_rules": {"min_trade_lot": 100},
        },
        "universe": {
            "universe": {"benchmark_symbol": "510300"},
            "manual_flags": {"thesis_flag_file": "data/manual/thesis_flags.csv"},
        },
        "sensitivity": {
            "sensitivity": {
                "data_mode": "real",
                "baseline": {
                    "name": "baseline",
                    "description": "默认基准参数组",
                    "overrides": {
                        "app": {"efinance": {"adjustment_mode": "forward"}, "schedule": {"monthly_invest_day_rule": "first_trading_day"}},
                        "risk": {"etf": {"yellow_drawdown_from_high": 0.15, "red_drawdown_from_high": 0.25}, "stock": {"yellow_drawdown_from_cost": 0.12, "red_drawdown_from_cost": 0.20}},
                        "backtest": {"backtest": {"execution_rule": "first_trading_day"}},
                    },
                },
                "scenarios": [
                    {"name": "adj_none", "description": "不复权", "overrides": {"app": {"efinance": {"adjustment_mode": "none"}}}},
                    {"name": "monthly_buy_last_trading_day", "description": "月末买入", "overrides": {"backtest": {"backtest": {"execution_rule": "last_trading_day"}}, "app": {"schedule": {"monthly_invest_day_rule": "last_trading_day"}}}},
                ],
            }
        },
    }


def test_baseline_and_single_factor_groups_constructed_correctly_fixed() -> None:
    engine = SensitivityEngine(_make_configs(), PROJECT_ROOT)
    groups = engine._build_scenarios()
    assert groups[0]["name"] == "baseline"
    assert {group["name"] for group in groups} == {"baseline", "adj_none", "monthly_buy_last_trading_day"}


def test_baseline_diff_calculation_fixed() -> None:
    engine = SensitivityEngine(_make_configs(), PROJECT_ROOT)
    summary = pd.DataFrame(
        [
            {"group_name": "baseline", "status": "success", "annualized_return": 0.10, "max_drawdown": 0.20, "annualized_volatility": 0.15, "cumulative_return": 0.30, "sharpe_like_ratio": 0.67, "total_invested_cash": 100000.0, "total_uninvested_cash": 5000.0, "invested_ratio": 0.95, "total_trade_count": 10, "unfilled_count": 1, "unfilled_amount": 500.0, "total_yellow_triggers": 3, "total_red_triggers": 1, "avg_monthly_risk_flags": 1.0, "average_etf_weight": 0.75, "average_stock_weight": 0.18, "average_cash_weight": 0.07, "average_weight_deviation": 0.02, "max_weight_deviation": 0.06, "count_months_with_cash_drag": 2, "count_months_with_paused_buys": 1},
            {"group_name": "adj_none", "status": "success", "annualized_return": 0.08, "max_drawdown": 0.22, "annualized_volatility": 0.14, "cumulative_return": 0.25, "sharpe_like_ratio": 0.57, "total_invested_cash": 98000.0, "total_uninvested_cash": 7000.0, "invested_ratio": 0.93, "total_trade_count": 9, "unfilled_count": 2, "unfilled_amount": 1500.0, "total_yellow_triggers": 5, "total_red_triggers": 2, "avg_monthly_risk_flags": 1.5, "average_etf_weight": 0.73, "average_stock_weight": 0.17, "average_cash_weight": 0.10, "average_weight_deviation": 0.03, "max_weight_deviation": 0.08, "count_months_with_cash_drag": 3, "count_months_with_paused_buys": 2},
        ]
    )
    diff = engine._build_baseline_diff(summary)
    row = diff.loc[diff["group_name"] == "adj_none"].iloc[0]
    assert round(float(row["annualized_return_diff"]), 4) == -0.02
    assert round(float(row["total_uninvested_cash_diff"]), 4) == 2000.0


def test_failed_group_does_not_interrupt_batch_fixed() -> None:
    temp_root = TMP_ROOT / f"sensitivity_{uuid.uuid4().hex}"
    temp_root.mkdir(parents=True, exist_ok=True)
    try:
        engine = SensitivityEngine(_make_configs(), temp_root)
        with patch.object(engine, "_build_scenarios", return_value=[{"name": "baseline", "description": "ok", "overrides": {}}, {"name": "broken", "description": "fail", "overrides": {}}]):
            with patch.object(engine, "_run_single_scenario", side_effect=[{"summary": {"group_name": "baseline", "description": "ok", "status": "success", "error": "", "data_mode": "real", "provider": "efinance", "source_api": "stock.get_quote_history", "backtest_start_date": "2024-01-01", "backtest_end_date": "2024-03-31", "adjustment_mode": "forward", "monthly_buy_rule": "first_trading_day", "etf_yellow": 0.15, "etf_red": 0.25, "stock_yellow": 0.12, "stock_red": 0.20, "etf_slippage": 0.001, "stock_slippage": 0.002, "cumulative_return": 0.2, "annualized_return": 0.1, "max_drawdown": 0.2, "annualized_volatility": 0.1, "sharpe_like_ratio": 1.0, "win_month_ratio": 0.5, "total_invested_cash": 1.0, "total_uninvested_cash": 1.0, "invested_ratio": 0.5, "total_trade_count": 1, "unfilled_count": 0, "unfilled_amount": 0.0, "total_yellow_triggers": 1, "total_red_triggers": 0, "symbols_with_red": "", "avg_monthly_risk_flags": 1.0, "average_etf_weight": 0.8, "average_stock_weight": 0.2, "average_cash_weight": 0.0, "average_weight_deviation": 0.01, "max_weight_deviation": 0.02, "earliest_symbol_unavailable_impact": "", "count_months_with_cash_drag": 0, "count_months_with_paused_buys": 0, "effective_config_json": "{}", "detail_path": ""}, "details": {"group_name": "baseline"}}, RuntimeError("boom")]):
                output = engine.run()
        assert "baseline" in output["summary"]["group_name"].tolist()
        assert "broken" in output["summary"]["group_name"].tolist()
        broken_row = output["summary"].loc[output["summary"]["group_name"] == "broken"].iloc[0]
        assert broken_row["status"] == "failed"
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_sensitivity_report_contains_baseline_config_fixed() -> None:
    temp_root = TMP_ROOT / f"sensitivity_{uuid.uuid4().hex}"
    temp_root.mkdir(parents=True, exist_ok=True)
    try:
        engine = SensitivityEngine(_make_configs(), temp_root)
        with patch.object(engine, "_build_scenarios", return_value=[{"name": "baseline", "description": "ok", "overrides": {}}]):
            with patch.object(engine, "_run_single_scenario", return_value={"summary": {"group_name": "baseline", "description": "ok", "status": "success", "error": "", "data_mode": "real", "provider": "efinance", "source_api": "stock.get_quote_history", "backtest_start_date": "2024-01-01", "backtest_end_date": "2024-03-31", "adjustment_mode": "forward", "monthly_buy_rule": "first_trading_day", "etf_yellow": 0.15, "etf_red": 0.25, "stock_yellow": 0.12, "stock_red": 0.20, "etf_slippage": 0.001, "stock_slippage": 0.002, "cumulative_return": 0.2, "annualized_return": 0.1, "max_drawdown": 0.2, "annualized_volatility": 0.1, "sharpe_like_ratio": 1.0, "win_month_ratio": 0.5, "total_invested_cash": 1.0, "total_uninvested_cash": 1.0, "invested_ratio": 0.5, "total_trade_count": 1, "unfilled_count": 0, "unfilled_amount": 0.0, "total_yellow_triggers": 1, "total_red_triggers": 0, "symbols_with_red": "", "avg_monthly_risk_flags": 1.0, "average_etf_weight": 0.8, "average_stock_weight": 0.2, "average_cash_weight": 0.0, "average_weight_deviation": 0.01, "max_weight_deviation": 0.02, "earliest_symbol_unavailable_impact": "", "count_months_with_cash_drag": 0, "count_months_with_paused_buys": 0, "effective_config_json": "{}", "detail_path": ""}, "details": {"group_name": "baseline"}}):
                output = engine.run()
        report_text = Path(output["paths"]["report"]).read_text(encoding="utf-8")
        assert "forward" in report_text
        assert "first_trading_day" in report_text
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_monthly_buy_rule_switch_changes_trade_days_fixed() -> None:
    temp_root = TMP_ROOT / f"sensitivity_{uuid.uuid4().hex}"
    try:
        temp_root.mkdir(parents=True, exist_ok=True)
        configs = _make_configs()
        thesis_file = temp_root / "data" / "manual" / "thesis_flags.csv"
        thesis_file.parent.mkdir(parents=True, exist_ok=True)
        thesis_file.write_text("symbol,thesis_broken,reason,last_update\n", encoding="utf-8")
        configs["universe"]["manual_flags"]["thesis_flag_file"] = str(thesis_file.relative_to(temp_root))

        target_table = build_target_table(configs["portfolio"])
        dates = pd.bdate_range("2024-01-01", "2024-02-29")
        histories = {}
        for index, symbol in enumerate(target_table["symbol"].tolist()):
            base = 10 + index
            histories[symbol] = pd.DataFrame(
                {
                    "date": dates,
                    "symbol": symbol,
                    "asset_type": target_table.loc[target_table["symbol"] == symbol, "asset_type"].iloc[0],
                    "close": [base + step * 0.05 for step in range(len(dates))],
                }
            )

        first_engine = MVPBacktestEngine(configs, temp_root)
        first_result = first_engine.run(histories, target_table)

        last_configs = deepcopy(configs)
        last_configs["backtest"]["backtest"]["execution_rule"] = "last_trading_day"
        last_configs["app"]["schedule"]["monthly_invest_day_rule"] = "last_trading_day"
        last_engine = MVPBacktestEngine(last_configs, temp_root)
        last_result = last_engine.run(histories, target_table)

        assert first_result.metadata["actual_monthly_trade_days"] != last_result.metadata["actual_monthly_trade_days"]
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_forward_and_none_adjustment_modes_hit_different_cache_paths_fixed() -> None:
    forward_configs = _make_configs()
    none_configs = _make_configs()
    none_configs["app"]["efinance"]["adjustment_mode"] = "none"

    forward_loader = MarketDataLoader(PROJECT_ROOT, configs=forward_configs)
    none_loader = MarketDataLoader(PROJECT_ROOT, configs=none_configs)

    forward_path = forward_loader.cache.cache_path("510300", "etf", variant=forward_loader._adjustment_mode())
    none_path = none_loader.cache.cache_path("510300", "etf", variant=none_loader._adjustment_mode())
    assert forward_path != none_path
