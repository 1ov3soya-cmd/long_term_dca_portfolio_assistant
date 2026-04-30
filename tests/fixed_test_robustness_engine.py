from pathlib import Path
import shutil
import sys
from unittest.mock import patch
import uuid

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.robustness_engine import RobustnessEngine


TMP_ROOT = PROJECT_ROOT / ".pytest_tmp"
TMP_ROOT.mkdir(parents=True, exist_ok=True)


def _make_configs() -> dict:
    return {
        "app": {"runtime": {"log_level": "INFO"}},
        "robustness": {
            "robustness": {
                "baseline_name": "baseline",
                "inputs": {
                    "summary_csv": "reports/sensitivity_summary.csv",
                    "baseline_diff_csv": "reports/sensitivity_baseline_diff.csv",
                    "details_json": "reports/sensitivity_details.json",
                },
                "outputs": {
                    "summary_markdown": "reports/robustness_summary.md",
                    "recommendation_markdown": "reports/default_parameter_recommendation.md",
                    "summary_json": "reports/robustness_summary.json",
                    "key_findings_csv": "reports/robustness_key_findings.csv",
                },
            }
        },
    }


def _write_inputs(root: Path, include_adj_none_failure: bool = True) -> None:
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    summary = pd.DataFrame(
        [
            {
                "group_name": "baseline",
                "description": "默认基准参数组",
                "status": "success",
                "error": "",
                "data_mode": "real",
                "provider": "efinance",
                "source_api": "stock.get_quote_history",
                "backtest_start_date": "2019-01-01",
                "backtest_end_date": "2025-12-31",
                "adjustment_mode": "forward",
                "monthly_buy_rule": "first_trading_day",
                "etf_yellow": 0.15,
                "etf_red": 0.25,
                "stock_yellow": 0.12,
                "stock_red": 0.20,
                "annualized_return": 0.0532,
                "max_drawdown": 0.2048,
                "invested_ratio": 0.7677,
                "total_uninvested_cash": 195091.60,
                "unfilled_amount": 168177.21,
                "total_red_triggers": 326,
                "effective_config_json": '{"adjustment_mode":"forward","execution_rule":"first_trading_day"}',
            },
            {
                "group_name": "etf_redline_tighter",
                "description": "收紧 ETF 红线",
                "status": "success",
                "error": "",
                "data_mode": "real",
                "provider": "efinance",
                "source_api": "stock.get_quote_history",
                "backtest_start_date": "2019-01-01",
                "backtest_end_date": "2025-12-31",
                "adjustment_mode": "forward",
                "monthly_buy_rule": "first_trading_day",
                "etf_yellow": 0.12,
                "etf_red": 0.20,
                "stock_yellow": 0.12,
                "stock_red": 0.20,
                "annualized_return": 0.0482,
                "max_drawdown": 0.1941,
                "invested_ratio": 0.7127,
                "total_uninvested_cash": 241290.18,
                "unfilled_amount": 168993.28,
                "total_red_triggers": 398,
                "effective_config_json": "{}",
            },
            {
                "group_name": "monthly_buy_last_trading_day",
                "description": "月末买入",
                "status": "success",
                "error": "",
                "data_mode": "real",
                "provider": "efinance",
                "source_api": "stock.get_quote_history",
                "backtest_start_date": "2019-01-01",
                "backtest_end_date": "2025-12-31",
                "adjustment_mode": "forward",
                "monthly_buy_rule": "last_trading_day",
                "etf_yellow": 0.15,
                "etf_red": 0.25,
                "stock_yellow": 0.12,
                "stock_red": 0.20,
                "annualized_return": 0.0520,
                "max_drawdown": 0.2052,
                "invested_ratio": 0.7682,
                "total_uninvested_cash": 194708.10,
                "unfilled_amount": 168639.05,
                "total_red_triggers": 302,
                "effective_config_json": "{}",
            },
            {
                "group_name": "stock_redline_tighter",
                "description": "收紧股票红线",
                "status": "success",
                "error": "",
                "data_mode": "real",
                "provider": "efinance",
                "source_api": "stock.get_quote_history",
                "backtest_start_date": "2019-01-01",
                "backtest_end_date": "2025-12-31",
                "adjustment_mode": "forward",
                "monthly_buy_rule": "first_trading_day",
                "etf_yellow": 0.15,
                "etf_red": 0.25,
                "stock_yellow": 0.10,
                "stock_red": 0.18,
                "annualized_return": 0.0532,
                "max_drawdown": 0.2048,
                "invested_ratio": 0.7677,
                "total_uninvested_cash": 195091.60,
                "unfilled_amount": 168177.21,
                "total_red_triggers": 326,
                "effective_config_json": "{}",
            },
        ]
    )
    if include_adj_none_failure:
        summary = pd.concat(
            [
                summary,
                pd.DataFrame(
                    [
                        {
                            "group_name": "adj_none",
                            "description": "切换到不复权",
                            "status": "failed",
                            "error": "provider error",
                            "data_mode": "real",
                            "provider": "",
                            "source_api": "",
                            "backtest_start_date": "2019-01-01",
                            "backtest_end_date": "2025-12-31",
                            "adjustment_mode": "",
                            "monthly_buy_rule": "",
                            "etf_yellow": "",
                            "etf_red": "",
                            "stock_yellow": "",
                            "stock_red": "",
                            "annualized_return": "",
                            "max_drawdown": "",
                            "invested_ratio": "",
                            "total_uninvested_cash": "",
                            "unfilled_amount": "",
                            "total_red_triggers": "",
                            "effective_config_json": "{}",
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
    summary.to_csv(reports / "sensitivity_summary.csv", index=False, encoding="utf-8-sig")

    diff = pd.DataFrame(
        [
            {
                "group_name": "baseline",
                "annualized_return_diff": 0.0,
                "max_drawdown_diff": 0.0,
                "invested_ratio_diff": 0.0,
                "total_uninvested_cash_diff": 0.0,
                "unfilled_amount_diff": 0.0,
                "total_red_triggers_diff": 0.0,
            },
            {
                "group_name": "etf_redline_tighter",
                "annualized_return_diff": -0.0050,
                "max_drawdown_diff": -0.0107,
                "invested_ratio_diff": -0.0550,
                "total_uninvested_cash_diff": 46198.58,
                "unfilled_amount_diff": 46198.58,
                "total_red_triggers_diff": 72.0,
            },
            {
                "group_name": "monthly_buy_last_trading_day",
                "annualized_return_diff": -0.0012,
                "max_drawdown_diff": 0.0004,
                "invested_ratio_diff": 0.0004,
                "total_uninvested_cash_diff": -383.50,
                "unfilled_amount_diff": 461.84,
                "total_red_triggers_diff": -24.0,
            },
            {
                "group_name": "stock_redline_tighter",
                "annualized_return_diff": 0.0,
                "max_drawdown_diff": 0.0,
                "invested_ratio_diff": 0.0,
                "total_uninvested_cash_diff": 0.0,
                "unfilled_amount_diff": 0.0,
                "total_red_triggers_diff": 0.0,
            },
        ]
    )
    diff.to_csv(reports / "sensitivity_baseline_diff.csv", index=False, encoding="utf-8-sig")
    (reports / "sensitivity_details.json").write_text('{"baseline":{"status":"success"}}', encoding="utf-8")


def _temp_root() -> Path:
    root = TMP_ROOT / f"robustness_{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_robustness_summary_generation_fixed() -> None:
    root = _temp_root()
    try:
        _write_inputs(root)
        engine = RobustnessEngine(_make_configs(), root)
        result = engine.summarize()
        assert Path(result["paths"]["summary_markdown"]).exists()
        assert Path(result["paths"]["recommendation_markdown"]).exists()
        assert result["payload"]["baseline_assessment"]["label"] in {"相对稳健", "中性可用", "对部分参数较敏感"}
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_default_parameter_recommendation_generation_fixed() -> None:
    root = _temp_root()
    try:
        _write_inputs(root)
        engine = RobustnessEngine(_make_configs(), root)
        payload = engine.summarize()["payload"]
        assert payload["default_parameter_recommendations"]["adjustment_mode"]["recommended_value"] == "forward"
        assert "baseline_default" in payload["default_parameter_recommendations"]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_high_sensitive_and_robust_family_classification_fixed() -> None:
    root = _temp_root()
    try:
        _write_inputs(root)
        engine = RobustnessEngine(_make_configs(), root)
        payload = engine.summarize()["payload"]
        high_sensitive = {item["family"] for item in payload["parameter_classification"]["high_sensitive"]}
        robust = {item["family"] for item in payload["parameter_classification"]["robust"]}
        assert "etf_redline" in high_sensitive
        assert "stock_redline" in robust
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_failed_group_does_not_break_report_generation_fixed() -> None:
    root = _temp_root()
    try:
        _write_inputs(root, include_adj_none_failure=True)
        engine = RobustnessEngine(_make_configs(), root)
        payload = engine.summarize()["payload"]
        assert payload["summary_context"]["failed_group_count"] == 1
        assert payload["summary_context"]["failed_groups"][0]["group_name"] == "adj_none"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_missing_input_files_raise_clear_error_fixed() -> None:
    root = _temp_root()
    try:
        engine = RobustnessEngine(_make_configs(), root)
        with pytest.raises(Exception) as exc_info:
            engine.summarize()
        assert "sensitivity-test" in str(exc_info.value)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_summary_report_contains_baseline_judgement_fixed() -> None:
    root = _temp_root()
    try:
        _write_inputs(root)
        engine = RobustnessEngine(_make_configs(), root)
        result = engine.summarize()
        text = Path(result["paths"]["summary_markdown"]).read_text(encoding="utf-8")
        assert "baseline 是否处于多数扰动结果的中间区域" in text
        assert "结论标签" in text
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_cli_summarize_robustness_dispatch_fixed() -> None:
    import src.main

    with patch("src.main.RobustnessEngine") as engine_cls:
        instance = engine_cls.return_value
        instance.summarize.return_value = {
            "paths": {
                "summary_markdown": Path("reports/robustness_summary.md"),
                "recommendation_markdown": Path("reports/default_parameter_recommendation.md"),
            }
        }
        with patch.object(sys, "argv", ["main", "summarize-robustness", "--end-date", "2025-12-31"]):
            src.main.main()
        instance.summarize.assert_called_once()
