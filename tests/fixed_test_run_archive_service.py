import json
import shutil
import sys
import uuid
from argparse import Namespace
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import src.main as main_module
from src.utils.runtime_models import ExtendedBacktestResult, MarketDataBundle
from src.utils.schemas import AllocationSuggestion, MonthlyRecommendation


TMP_ROOT = PROJECT_ROOT / ".pytest_tmp"
TMP_ROOT.mkdir(parents=True, exist_ok=True)


def _temp_root() -> Path:
    root = TMP_ROOT / f"run_archive_{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _make_configs() -> dict:
    return {
        "app": {
            "runtime": {
                "log_level": "INFO",
                "data_provider": "fake_provider",
            },
            "efinance": {"adjustment_mode": "forward"},
            "schedule": {
                "monthly_invest_day_rule": "first_trading_day",
                "weekly_risk_check_rule": "last_trading_day_of_week",
            },
        },
        "portfolio": {
            "portfolio": {"monthly_budget": 10000.0},
            "asset_allocation": {"etf_total_weight": 0.8, "stock_total_weight": 0.2},
            "etf_pool": [{"symbol": "510300", "name": "ETF_A", "target_weight": 0.8}],
            "stock_pool": [{"symbol": "600519", "name": "STOCK_A", "target_weight": 0.2}],
        },
        "risk": {
            "risk": {"moving_average_window": 5},
            "etf": {"yellow_drawdown_from_high": 0.15, "red_drawdown_from_high": 0.25, "weakness_days": 2},
            "stock": {"yellow_drawdown_from_cost": 0.12, "red_drawdown_from_cost": 0.20},
            "portfolio": {"red_max_drawdown": 0.2},
            "manual_logic": {
                "manual_force_review_pause_buy": True,
                "thesis_broken_pause_buy": True,
                "thesis_broken_force_review": True,
                "priority_levels": {
                    "thesis_broken": 1,
                    "manual_force_review": 2,
                    "manual_pause_buy": 3,
                    "price_red": 4,
                    "price_yellow": 5,
                    "green": 6,
                },
                "actions": {
                    "thesis_broken": "停止新增，最高优先级人工处理",
                    "manual_force_review": "暂停新增，强制人工复核",
                    "manual_pause_buy": "暂停新增，等待人工解除",
                    "price_red": "价格 RED，强制人工复核",
                    "price_yellow": "价格 YELLOW，暂停新增并人工复核",
                    "green": "正常",
                },
            },
        },
        "backtest": {
            "backtest": {
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
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
            "manual_flags": {
                "logic_risk_flag_file": "config/manual_risk_flags.yaml",
                "thesis_flag_file": "data/manual/thesis_flags.csv",
                "holdings_file": "data/manual/holdings.csv",
            },
        },
        "sensitivity": {
            "sensitivity": {
                "data_mode": "real",
                "baseline": {"name": "baseline", "description": "基线", "overrides": {}},
                "scenarios": [],
            }
        },
        "robustness": {"robustness": {"baseline_name": "baseline", "inputs": {}, "outputs": {}}},
        "archive": {
            "archive": {
                "archive_enabled": True,
                "archive_root_dir": "reports/runs",
                "archive_copy_reports": False,
                "archive_include_manual_risk_snapshot": True,
                "update_latest_index": True,
            }
        },
    }


def _write_support_files(root: Path) -> None:
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "data" / "manual").mkdir(parents=True, exist_ok=True)
    (root / "config" / "manual_risk_flags.yaml").write_text(
        "\n".join(
            [
                "manual_risk_flags:",
                "  notice: \"test file\"",
                "  symbols:",
                "    \"600519\":",
                "      asset_type: \"stock\"",
                "      effective_from: \"2025-01-01\"",
                "      manual_pause_buy: true",
                "      manual_force_review: false",
                "      thesis_broken: false",
                "      note: \"test\"",
                "      updated_at: \"2026-04-02\"",
                "      updated_by: \"pytest\"",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "config" / "manual_risk_flags.json").write_text(
        json.dumps(
            {
                "manual_risk_flags": {
                    "notice": "test file",
                    "symbols": {
                        "600519": {
                            "asset_type": "stock",
                            "effective_from": "2025-01-01",
                            "manual_pause_buy": True,
                            "manual_force_review": False,
                            "thesis_broken": False,
                            "note": "test",
                            "updated_at": "2026-04-02",
                            "updated_by": "pytest",
                        }
                    },
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (root / "data" / "manual" / "thesis_flags.csv").write_text(
        "symbol,thesis_broken,reason,last_update\n",
        encoding="utf-8",
    )
    (root / "data" / "manual" / "holdings.csv").write_text(
        "symbol,asset_type,quantity,avg_cost,last_update\n",
        encoding="utf-8",
    )


def _fake_bundle() -> MarketDataBundle:
    history = pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-12-01", "2025-12-31"]),
            "open": [10.0, 10.5],
            "high": [10.2, 10.7],
            "low": [9.9, 10.3],
            "close": [10.1, 10.6],
            "volume": [1000, 1200],
            "amount": [10100, 12720],
        }
    )
    diagnostics = pd.DataFrame(
        [
            {
                "symbol": "510300",
                "asset_type": "etf",
                "provider": "fake_provider",
                "source_api": "fake_api",
                "adjustment_mode": "forward",
                "rows": 2,
            }
        ]
    )
    return MarketDataBundle(
        histories={"510300": history, "600519": history.copy()},
        diagnostics=diagnostics,
        calendar=[pd.Timestamp("2025-12-01"), pd.Timestamp("2025-12-31")],
        metadata={
            "data_mode": "real",
            "provider": "fake_provider",
            "source_api": "fake_api",
            "adjustment_mode": "forward",
            "as_of_date": pd.Timestamp("2025-12-31"),
            "latest_data_date": "2025-12-31",
            "config_summary": {"monthly_budget": 10000.0},
        },
    )


def _fake_recommendation() -> dict:
    recommendation = MonthlyRecommendation(
        as_of_date=pd.Timestamp("2025-12-31"),
        total_budget=10000.0,
        etf_budget=8000.0,
        stock_budget=2000.0,
        suggestions=[
            AllocationSuggestion(
                symbol="510300",
                asset_type="etf",
                target_weight=0.8,
                current_weight=0.7,
                recommended_amount=8000.0,
                status="GREEN",
                pause_buy=False,
                manual_review=False,
            ),
            AllocationSuggestion(
                symbol="600519",
                asset_type="stock",
                target_weight=0.2,
                current_weight=0.1,
                recommended_amount=0.0,
                status="YELLOW",
                pause_buy=True,
                manual_review=True,
                manual_pause_buy=True,
                manual_force_review=True,
            ),
        ],
        manual_review_items=["600519: 人工复核"],
    )
    return {
        "recommendation": recommendation,
        "current_table": pd.DataFrame([{"symbol": "510300", "market_value": 10000.0}]),
        "risk_table": pd.DataFrame([{"symbol": "600519", "status": "YELLOW"}]),
    }


def _fake_backtest_result() -> ExtendedBacktestResult:
    return ExtendedBacktestResult(
        equity_curve=pd.DataFrame(
            [
                {
                    "date": pd.Timestamp("2025-12-31"),
                    "cash": 1234.0,
                    "portfolio_value": 11234.0,
                    "cumulative_contribution": 10000.0,
                    "unit_nav": 1.1234,
                }
            ]
        ),
        trades=pd.DataFrame(
            [
                {
                    "date": pd.Timestamp("2025-12-01"),
                    "symbol": "510300",
                    "total_cash_out": 8766.0,
                    "status": "GREEN",
                }
            ]
        ),
        monthly_records=pd.DataFrame([{"date": pd.Timestamp("2025-12-01")}]),
        risk_records=pd.DataFrame(
            [
                {"date": pd.Timestamp("2025-12-01"), "symbol": "600519", "status": "YELLOW"},
                {"date": pd.Timestamp("2025-12-31"), "symbol": "600519", "status": "RED"},
            ]
        ),
        metrics={
            "cumulative_return": 0.1234,
            "annualized_return": 0.08,
            "max_drawdown": 0.12,
        },
        unfilled_orders=pd.DataFrame([{"date": pd.Timestamp("2025-12-01"), "symbol": "600519", "reason": "paused_by_risk_rule"}]),
        recommendation_records=pd.DataFrame([{"date": pd.Timestamp("2025-12-01"), "symbol": "600519"}]),
        portfolio_snapshots=pd.DataFrame([{"date": pd.Timestamp("2025-12-31"), "symbol": "510300"}]),
        metadata={"data_mode": "real", "provider": "fake_provider", "source_api": "fake_api", "adjustment_mode": "forward"},
    )


class _DummyEngine:
    def __init__(self, *_args, **_kwargs) -> None:
        pass


class _FakeLoader:
    def __init__(self, project_root: Path, configs: dict | None = None) -> None:
        self.project_root = Path(project_root)
        self.configs = configs or _make_configs()

    def load_market_data_bundle(self, *args, **kwargs) -> MarketDataBundle:
        return _fake_bundle()


class _FakeReportGenerator:
    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root)

    def save_monthly_report(self, **_kwargs) -> dict[str, Path]:
        out_dir = self.project_root / "reports" / "monthly"
        out_dir.mkdir(parents=True, exist_ok=True)
        markdown = out_dir / "monthly_report_20251231.md"
        csv_path = out_dir / "monthly_suggestion_20251231.csv"
        markdown.write_text("# monthly\n", encoding="utf-8")
        csv_path.write_text("symbol\n510300\n", encoding="utf-8")
        return {"markdown": markdown, "suggestion_csv": csv_path}

    def save_backtest_report(self, *_args, **_kwargs) -> dict[str, Path]:
        out_dir = self.project_root / "reports" / "backtest"
        out_dir.mkdir(parents=True, exist_ok=True)
        markdown = out_dir / "backtest_report.md"
        metrics = out_dir / "metrics.csv"
        markdown.write_text("# backtest\n", encoding="utf-8")
        metrics.write_text("metric,value\nannualized_return,0.08\n", encoding="utf-8")
        return {"markdown": markdown, "metrics": metrics}


class _FakeSignalEngine:
    def __init__(self, *_args, **_kwargs) -> None:
        pass

    def generate_monthly_recommendation(self, **_kwargs) -> dict:
        return _fake_recommendation()


class _FakeBacktestEngine:
    def __init__(self, *_args, **_kwargs) -> None:
        pass

    def run(self, *_args, **_kwargs) -> ExtendedBacktestResult:
        return _fake_backtest_result()


class _FakeSensitivityEngine:
    def __init__(self, _configs: dict, project_root: Path, *_args, **_kwargs) -> None:
        self.project_root = Path(project_root)

    def run(self, **_kwargs) -> dict:
        reports_dir = self.project_root / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        summary_path = reports_dir / "sensitivity_summary.csv"
        diff_path = reports_dir / "sensitivity_baseline_diff.csv"
        details_path = reports_dir / "sensitivity_details.json"
        report_path = reports_dir / "sensitivity_report.md"
        rankings_path = reports_dir / "sensitivity_rankings.csv"
        for path in [summary_path, diff_path, details_path, report_path, rankings_path]:
            path.write_text("ok\n", encoding="utf-8")
        summary = pd.DataFrame(
            [
                {"group_name": "baseline", "status": "success", "data_mode": "real", "provider": "fake_provider", "adjustment_mode": "forward"},
                {"group_name": "etf_tighter", "status": "failed", "data_mode": "real", "provider": "fake_provider", "adjustment_mode": "forward"},
            ]
        )
        baseline_diff = pd.DataFrame(
            [
                {
                    "group_name": "baseline",
                    "annualized_return_diff": 0.0,
                    "max_drawdown_diff": 0.0,
                    "invested_ratio_diff": 0.0,
                    "total_red_triggers_diff": 0.0,
                },
                {
                    "group_name": "etf_tighter",
                    "annualized_return_diff": 0.01,
                    "max_drawdown_diff": 0.02,
                    "invested_ratio_diff": 0.03,
                    "total_red_triggers_diff": 2.0,
                },
            ]
        )
        return {
            "summary": summary,
            "baseline_diff": baseline_diff,
            "rankings": pd.DataFrame(),
            "details": {},
            "paths": {
                "summary": summary_path,
                "baseline_diff": diff_path,
                "rankings": rankings_path,
                "details": details_path,
                "report": report_path,
            },
        }


class _FailingSensitivityEngine(_FakeSensitivityEngine):
    def run(self, **_kwargs) -> dict:
        raise RuntimeError("intentional sensitivity failure")


def _patch_common(monkeypatch: pytest.MonkeyPatch, configs: dict) -> None:
    monkeypatch.setattr(main_module, "MarketDataLoader", lambda project_root: _FakeLoader(project_root, configs=configs))
    monkeypatch.setattr(main_module, "ReportGenerator", _FakeReportGenerator)
    monkeypatch.setattr(main_module, "SignalEngine", _FakeSignalEngine)
    monkeypatch.setattr(main_module, "MVPBacktestEngine", _FakeBacktestEngine)
    monkeypatch.setattr(main_module, "ValidationEngine", _DummyEngine)
    monkeypatch.setattr(main_module, "RobustnessEngine", _DummyEngine)
    monkeypatch.setattr(main_module, "ManualRiskAcceptanceHelper", _DummyEngine)


def _latest_run_dir(root: Path, command_suffix: str | None = None) -> Path:
    runs = sorted(
        [item for item in (root / "reports" / "runs").glob("*") if item.is_dir()],
        key=lambda item: item.name,
    )
    if command_suffix is None:
        return runs[-1]
    return [item for item in runs if item.name.endswith(command_suffix)][-1]


def test_suggest_run_creates_archive_fixed(monkeypatch: pytest.MonkeyPatch) -> None:
    root = _temp_root()
    try:
        _write_support_files(root)
        configs = _make_configs()
        _patch_common(monkeypatch, configs)
        monkeypatch.setattr(main_module, "SensitivityEngine", _DummyEngine)
        args = Namespace(command="suggest", end_date="2025-12-31", manual_risk_file="config/manual_risk_flags.yaml")
        main_module.run_cli(args, project_root=root)

        run_dir = _latest_run_dir(root, "suggest")
        manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
        snapshot = json.loads((run_dir / "effective_config_snapshot.json").read_text(encoding="utf-8"))
        cli_args = json.loads((run_dir / "cli_args.json").read_text(encoding="utf-8"))
        artifacts = json.loads((run_dir / "output_artifacts.json").read_text(encoding="utf-8"))
        latest_index = json.loads((root / "reports" / "runs" / "latest_index.json").read_text(encoding="utf-8"))

        assert manifest["command_name"] == "suggest"
        assert manifest["status"] == "success"
        assert manifest["manual_risk_file"] == "config/manual_risk_flags.yaml"
        assert snapshot["backtest"]["backtest"]["end_date"] == "2025-12-31"
        assert snapshot["manual_risk_file_path"].endswith("config\\manual_risk_flags.yaml")
        assert cli_args["manual_risk_file"] == "config/manual_risk_flags.yaml"
        assert "monthly_report" in artifacts["original_outputs"]
        assert latest_index["suggest"]["run_id"] == manifest["run_id"]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_backtest_run_writes_manifest_fixed(monkeypatch: pytest.MonkeyPatch) -> None:
    root = _temp_root()
    try:
        _write_support_files(root)
        configs = _make_configs()
        _patch_common(monkeypatch, configs)
        monkeypatch.setattr(main_module, "SensitivityEngine", _DummyEngine)
        args = Namespace(command="backtest", end_date="2025-12-31", manual_risk_file=None)
        main_module.run_cli(args, project_root=root)

        run_dir = _latest_run_dir(root, "backtest")
        manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
        artifacts = json.loads((run_dir / "output_artifacts.json").read_text(encoding="utf-8"))
        latest_index = json.loads((root / "reports" / "runs" / "latest_index.json").read_text(encoding="utf-8"))

        assert manifest["command_name"] == "backtest"
        assert manifest["provider_name"] == "fake_provider"
        assert (run_dir / "run_manifest.json").exists()
        assert "backtest_report" in artifacts["original_outputs"]
        assert latest_index["backtest"]["run_id"] == manifest["run_id"]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_failed_run_keeps_minimum_archive_fixed(monkeypatch: pytest.MonkeyPatch) -> None:
    root = _temp_root()
    try:
        _write_support_files(root)
        configs = _make_configs()
        _patch_common(monkeypatch, configs)
        monkeypatch.setattr(main_module, "SensitivityEngine", _FailingSensitivityEngine)
        args = Namespace(command="sensitivity-test", end_date="2025-12-31", manual_risk_file=None)

        with pytest.raises(RuntimeError):
            main_module.run_cli(args, project_root=root)

        run_dir = _latest_run_dir(root, "sensitivity_test")
        manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
        notes = (run_dir / "notes.md").read_text(encoding="utf-8")

        assert manifest["status"] == "failed"
        assert manifest["errors_count"] == 1
        assert (run_dir / "cli_args.json").exists()
        assert "intentional sensitivity failure" in notes
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_partial_status_marked_for_sensitivity_fixed(monkeypatch: pytest.MonkeyPatch) -> None:
    root = _temp_root()
    try:
        _write_support_files(root)
        configs = _make_configs()
        _patch_common(monkeypatch, configs)
        monkeypatch.setattr(main_module, "SensitivityEngine", _FakeSensitivityEngine)
        args = Namespace(command="sensitivity-test", end_date="2025-12-31", manual_risk_file=None)
        main_module.run_cli(args, project_root=root)

        run_dir = _latest_run_dir(root, "sensitivity_test")
        manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
        key_summary = json.loads((run_dir / "key_summary.json").read_text(encoding="utf-8"))

        assert manifest["status"] == "partial"
        assert key_summary["groups_failed"] == 1
        assert key_summary["groups_success"] == 1
    finally:
        shutil.rmtree(root, ignore_errors=True)
