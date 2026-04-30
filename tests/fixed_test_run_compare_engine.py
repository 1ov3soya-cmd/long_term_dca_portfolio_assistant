import json
import shutil
import sys
import uuid
from argparse import Namespace
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import src.main as main_module
from src.run_compare_engine import RunCompareEngine


TMP_ROOT = PROJECT_ROOT / ".pytest_tmp"
TMP_ROOT.mkdir(parents=True, exist_ok=True)


def _temp_root() -> Path:
    root = TMP_ROOT / f"run_compare_{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _make_configs() -> dict:
    return {
        "app": {
            "runtime": {"log_level": "INFO", "data_provider": "fake_provider"},
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
        "risk": {"risk": {"moving_average_window": 5}, "etf": {}, "stock": {}, "portfolio": {}, "manual_logic": {}},
        "backtest": {
            "backtest": {"start_date": "2025-01-01", "end_date": "2025-12-31"},
            "transaction_cost": {"etf": {"slippage": 0.001}, "stock": {"slippage": 0.002}},
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
        "sensitivity": {"sensitivity": {"baseline": {"name": "baseline", "description": "基线", "overrides": {}}, "scenarios": []}},
        "robustness": {"robustness": {"baseline_name": "baseline", "inputs": {}, "outputs": {}}},
        "archive": {"archive": {"archive_enabled": True, "archive_root_dir": "reports/runs", "archive_copy_reports": False, "archive_include_manual_risk_snapshot": True, "update_latest_index": True}},
    }


def _write_archived_run(
    root: Path,
    run_id: str,
    command_name: str = "backtest",
    manifest_overrides: dict | None = None,
    cli_args_overrides: dict | None = None,
    config_overrides: dict | None = None,
    summary_overrides: dict | None = None,
    output_overrides: dict | None = None,
    notes_text: str | None = None,
    omit_files: set[str] | None = None,
) -> Path:
    omit_files = omit_files or set()
    run_dir = root / "reports" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "run_id": run_id,
        "command_name": command_name,
        "started_at": "2026-04-02 10:00:00",
        "finished_at": "2026-04-02 10:00:10",
        "duration_seconds": 10.0,
        "status": "success",
        "end_date": "2025-12-31",
        "data_mode": "real",
        "provider_name": "efinance",
        "adj_mode": "forward",
        "manual_risk_file": "config/manual_risk_flags.yaml",
        "warnings_count": 0,
        "errors_count": 0,
    }
    manifest.update(manifest_overrides or {})

    cli_args = {
        "command": command_name,
        "end_date": "2025-12-31",
        "manual_risk_file": "config/manual_risk_flags.yaml",
        "all_args": {"command": command_name, "end_date": "2025-12-31", "manual_risk_file": "config/manual_risk_flags.yaml"},
    }
    if cli_args_overrides:
        cli_args.update(cli_args_overrides)
        cli_args["all_args"].update(cli_args_overrides.get("all_args", {}))

    config_snapshot = {
        "app": {"efinance": {"adjustment_mode": "forward"}, "schedule": {"monthly_invest_day_rule": "first_trading_day"}},
        "portfolio": {"asset_allocation": {"etf_total_weight": 0.8, "stock_total_weight": 0.2}},
        "risk": {"etf": {"yellow_drawdown_from_high": 0.15, "red_drawdown_from_high": 0.25}},
        "backtest": {"backtest": {"execution_rule": "first_trading_day"}},
        "manual_risk_file_path": str(root / "config" / "manual_risk_flags.yaml"),
        "manual_risk_flags_snapshot": {"manual_risk_flags": {"symbols": {"600519": {"manual_pause_buy": False}}}},
    }
    if config_overrides:
        config_snapshot.update(config_overrides)

    output_artifacts = {
        "original_outputs": {"markdown": str(run_dir / "report.md")},
        "copied_outputs": {},
    }
    if output_overrides:
        output_artifacts.update(output_overrides)

    key_summary = {
        "annualized_return": 0.08,
        "max_drawdown": 0.12,
        "total_uninvested_cash": 1000.0,
        "total_red_triggers": 2,
        "paused_symbols_count": 1,
    }
    key_summary.update(summary_overrides or {})

    notes = notes_text or "\n".join(
        [
            "# 运行说明",
            "",
            "## 关键告警",
            "- 当前无关键告警。",
            "",
            "## 失败或限制",
            "- 当前无失败信息。",
            "",
            "## 额外说明",
            "- 默认说明。",
            "",
        ]
    )

    file_map = {
        "run_manifest": ("run_manifest.json", manifest),
        "cli_args": ("cli_args.json", cli_args),
        "config_snapshot": ("effective_config_snapshot.json", config_snapshot),
        "output_artifacts": ("output_artifacts.json", output_artifacts),
        "key_summary": ("key_summary.json", key_summary),
    }
    for key, (filename, payload) in file_map.items():
        if key in omit_files:
            continue
        (run_dir / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if "notes" not in omit_files:
        (run_dir / "notes.md").write_text(notes, encoding="utf-8")
    return run_dir


class _FakeLoader:
    def __init__(self, project_root: Path) -> None:
        self.configs = _make_configs()


def test_compare_two_run_manifests_fixed() -> None:
    root = _temp_root()
    try:
        _write_archived_run(root, "20260402_100000_backtest_a")
        _write_archived_run(root, "20260403_100000_backtest_b")
        engine = RunCompareEngine(root)
        result = engine.compare_runs("20260402_100000_backtest_a", "20260403_100000_backtest_b")

        assert result["compare_manifest"]["command_match"] is True
        assert result["paths"]["compare_manifest"].exists()
        assert result["paths"]["compare_report"].exists()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_compare_detects_cli_config_and_manual_risk_changes_fixed() -> None:
    root = _temp_root()
    try:
        _write_archived_run(root, "run_a")
        _write_archived_run(
            root,
            "run_b",
            cli_args_overrides={"manual_risk_file": "config/manual_risk_flags_acceptance_sample.yaml", "all_args": {"manual_risk_file": "config/manual_risk_flags_acceptance_sample.yaml"}},
            config_overrides={
                "app": {"efinance": {"adjustment_mode": "none"}, "schedule": {"monthly_invest_day_rule": "last_trading_day"}},
                "manual_risk_file_path": str(root / "config" / "manual_risk_flags_acceptance_sample.yaml"),
                "manual_risk_flags_snapshot": {"manual_risk_flags": {"symbols": {"600519": {"manual_pause_buy": True}}}},
            },
        )
        engine = RunCompareEngine(root)
        result = engine.compare_runs("run_a", "run_b")

        summary = result["compare_summary"]
        config_diff = json.loads(result["paths"]["config_diff"].read_text(encoding="utf-8"))

        assert summary["manual_risk_changed"] is True
        assert summary["adj_mode_changed"] is True
        assert any(item["path"].startswith("app.efinance.adjustment_mode") for item in config_diff["config_snapshot_diff"]["changed_values"])
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_compare_key_summary_numeric_diff_and_report_fixed() -> None:
    root = _temp_root()
    try:
        _write_archived_run(root, "run_a", summary_overrides={"annualized_return": 0.08, "max_drawdown": 0.12})
        _write_archived_run(root, "run_b", summary_overrides={"annualized_return": 0.10, "max_drawdown": 0.09})
        engine = RunCompareEngine(root)
        result = engine.compare_runs("run_a", "run_b")

        summary_diff = result["paths"]["summary_diff"].read_text(encoding="utf-8")
        report_text = result["paths"]["compare_report"].read_text(encoding="utf-8")

        assert "annualized_return" in summary_diff
        assert "0.02" in summary_diff or "0.020000000000000004" in summary_diff
        assert "最值得关注的差异摘要" in report_text
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_compare_missing_files_and_low_comparability_fixed(monkeypatch: pytest.MonkeyPatch) -> None:
    root = _temp_root()
    try:
        _write_archived_run(root, "run_a", command_name="backtest")
        _write_archived_run(
            root,
            "run_b",
            command_name="suggest",
            omit_files={"key_summary"},
        )
        engine = RunCompareEngine(root)
        result = engine.compare_runs("run_a", "run_b")

        assert result["compare_manifest"]["compare_status"] == "partial"
        assert result["compare_manifest"]["comparable_level"] == "low"

        monkeypatch.setattr(main_module, "MarketDataLoader", _FakeLoader)
        args = Namespace(
            command="compare-runs",
            end_date=None,
            manual_risk_file=None,
            run_a="run_a",
            run_b="run_b",
            latest=None,
            brief=False,
        )
        main_module.run_cli(args, project_root=root)
        compare_archive_root = root / "reports" / "run_compare"
        assert any(compare_archive_root.iterdir())
    finally:
        shutil.rmtree(root, ignore_errors=True)
