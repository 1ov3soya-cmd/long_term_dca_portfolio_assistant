import json
import shutil
import sys
import uuid
from copy import deepcopy
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest_engine import MVPBacktestEngine
from src.main import apply_manual_risk_file_override
from src.manual_risk_acceptance import ManualRiskAcceptanceHelper
from src.manual_risk_manager import ManualRiskFlagManager
from src.portfolio import PortfolioState, build_target_table
from src.signal_engine import SignalEngine
from src.utils.schemas import Holding


TMP_ROOT = PROJECT_ROOT / ".pytest_tmp"
TMP_ROOT.mkdir(parents=True, exist_ok=True)


def _temp_root() -> Path:
    root = TMP_ROOT / f"manual_acceptance_{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_manual_file(root: Path, payload: dict, relative_path: str = "config/manual_risk_flags_acceptance_sample.yaml") -> str:
    file_path = root / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_lines = ["manual_risk_flags:"]
    notice = payload["manual_risk_flags"].get("notice", "")
    yaml_lines.append(f"  notice: {json.dumps(notice, ensure_ascii=False)}")
    yaml_lines.append("  symbols:")
    for symbol, row in payload["manual_risk_flags"]["symbols"].items():
        yaml_lines.append(f'    "{symbol}":')
        for key, value in row.items():
            if isinstance(value, bool):
                rendered = str(value).lower()
            else:
                rendered = json.dumps(value, ensure_ascii=False)
            yaml_lines.append(f"      {key}: {rendered}")
    file_path.write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")
    file_path.with_suffix(".json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return relative_path


def _make_configs() -> dict:
    return {
        "app": {
            "runtime": {"log_level": "INFO", "cache_format": "csv", "data_provider": "efinance", "max_retry": 1, "retry_sleep_seconds": 0.0},
            "schedule": {"monthly_invest_day_rule": "first_trading_day", "weekly_risk_check_rule": "last_trading_day_of_week"},
        },
        "portfolio": {
            "portfolio": {"monthly_budget": 10000.0},
            "asset_allocation": {"etf_total_weight": 0.8, "stock_total_weight": 0.2},
            "etf_pool": [{"symbol": "515180", "name": "ETF_A", "target_weight": 0.8}],
            "stock_pool": [
                {"symbol": "600519", "name": "STOCK_A", "target_weight": 0.1},
                {"symbol": "000858", "name": "STOCK_B", "target_weight": 0.1},
            ],
        },
        "risk": {
            "risk": {"moving_average_window": 3},
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
            "universe": {"benchmark_symbol": "515180"},
            "manual_flags": {
                "logic_risk_flag_file": "config/manual_risk_flags.yaml",
                "thesis_flag_file": "data/manual/thesis_flags.csv",
                "holdings_file": "data/manual/holdings.csv",
            },
        },
    }


def _base_payload() -> dict:
    return {
        "manual_risk_flags": {
            "notice": "此文件仅用于验收，不构成投资建议，不应直接覆盖正式生产配置。",
            "symbols": {
                "600519": {
                    "asset_type": "stock",
                    "effective_from": "2025-01-01",
                    "manual_pause_buy": True,
                    "manual_force_review": False,
                    "thesis_broken": False,
                    "note": "用于验收暂停新增逻辑",
                    "updated_at": "2026-04-01",
                    "updated_by": "acceptance_sample",
                },
                "515180": {
                    "asset_type": "etf",
                    "effective_from": "2025-06-01",
                    "manual_pause_buy": False,
                    "manual_force_review": True,
                    "thesis_broken": False,
                    "note": "用于验收强制复核逻辑",
                    "updated_at": "2026-04-01",
                    "updated_by": "acceptance_sample",
                },
                "000858": {
                    "asset_type": "stock",
                    "effective_from": "2025-03-01",
                    "manual_pause_buy": False,
                    "manual_force_review": False,
                    "thesis_broken": True,
                    "note": "用于验收逻辑失效处理",
                    "updated_at": "2026-04-01",
                    "updated_by": "acceptance_sample",
                },
            },
        }
    }


def _write_support_files(root: Path) -> None:
    (root / "data" / "manual").mkdir(parents=True, exist_ok=True)
    (root / "data" / "manual" / "thesis_flags.csv").write_text("symbol,thesis_broken,reason,last_update\n", encoding="utf-8")
    (root / "data" / "manual" / "holdings.csv").write_text("symbol,asset_type,quantity,avg_cost,last_update\n", encoding="utf-8")


def _histories() -> dict[str, pd.DataFrame]:
    dates = pd.bdate_range("2025-01-01", "2025-12-31")
    return {
        "515180": pd.DataFrame({"date": dates, "close": [10 + idx * 0.01 for idx in range(len(dates))]}),
        "600519": pd.DataFrame({"date": dates, "close": [100 + idx * 0.10 for idx in range(len(dates))]}),
        "000858": pd.DataFrame({"date": dates, "close": [80 + idx * 0.08 for idx in range(len(dates))]}),
    }


def test_acceptance_sample_file_loads_fixed() -> None:
    sample_path = PROJECT_ROOT / "config" / "manual_risk_flags_acceptance_sample.yaml"
    manager = ManualRiskFlagManager(sample_path, PROJECT_ROOT / "data" / "manual" / "thesis_flags.csv")
    flags = manager.load_all_flags()
    assert {"600519", "515180", "000858"}.issubset(set(flags.keys()))


def test_manual_pause_acceptance_sample_blocks_buy_fixed() -> None:
    root = _temp_root()
    try:
        _write_support_files(root)
        relative_path = _write_manual_file(root, _base_payload())
        configs = apply_manual_risk_file_override(_make_configs(), relative_path)
        target_table = build_target_table(configs["portfolio"])
        engine = SignalEngine(configs, root)
        payload = engine.generate_monthly_recommendation("2025-12-31", _histories(), PortfolioState(), target_table)
        suggestion = payload["recommendation"].to_frame().loc[lambda df: df["symbol"] == "600519"].iloc[0]
        assert bool(suggestion["pause_buy"]) is True
        assert bool(suggestion["manual_pause_buy"]) is True
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_manual_force_review_acceptance_sample_enters_review_fixed() -> None:
    root = _temp_root()
    try:
        _write_support_files(root)
        relative_path = _write_manual_file(root, _base_payload())
        configs = apply_manual_risk_file_override(_make_configs(), relative_path)
        target_table = build_target_table(configs["portfolio"])
        engine = SignalEngine(configs, root)
        payload = engine.generate_monthly_recommendation("2025-12-31", _histories(), PortfolioState(), target_table)
        suggestion = payload["recommendation"].to_frame().loc[lambda df: df["symbol"] == "515180"].iloc[0]
        assert bool(suggestion["manual_force_review"]) is True
        assert bool(suggestion["manual_review"]) is True
        assert bool(suggestion["pause_buy"]) is True
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_thesis_broken_acceptance_sample_stops_buy_without_sell_fixed() -> None:
    root = _temp_root()
    try:
        _write_support_files(root)
        relative_path = _write_manual_file(root, _base_payload())
        configs = apply_manual_risk_file_override(_make_configs(), relative_path)
        target_table = build_target_table(configs["portfolio"])
        engine = MVPBacktestEngine(configs, root)
        result = engine.run(_histories(), target_table)
        broken_rows = result.recommendation_records.copy()
        broken_rows["date"] = pd.to_datetime(broken_rows["date"])
        broken_rows = broken_rows.loc[
            (broken_rows["symbol"] == "000858") & (broken_rows["date"] >= pd.Timestamp("2025-03-01"))
        ]
        assert not broken_rows.empty
        assert bool(broken_rows["thesis_broken"].all()) is True
        assert bool((broken_rows["recommended_amount"] == 0).all()) is True
        assert "SELL" not in set(result.trades.get("action", pd.Series(dtype=str)).tolist())
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_effective_from_changes_behavior_fixed() -> None:
    root = _temp_root()
    try:
        _write_support_files(root)
        payload = _base_payload()
        payload["manual_risk_flags"]["symbols"]["600519"]["effective_from"] = "2025-07-01"
        relative_path = _write_manual_file(root, payload)
        configs = apply_manual_risk_file_override(_make_configs(), relative_path)
        target_table = build_target_table(configs["portfolio"])
        engine = SignalEngine(configs, root)
        histories = _histories()
        before = engine.generate_monthly_recommendation("2025-06-30", histories, PortfolioState(), target_table)
        after = engine.generate_monthly_recommendation("2025-07-31", histories, PortfolioState(), target_table)
        before_row = before["recommendation"].to_frame().loc[lambda df: df["symbol"] == "600519"].iloc[0]
        after_row = after["recommendation"].to_frame().loc[lambda df: df["symbol"] == "600519"].iloc[0]
        assert bool(before_row["manual_pause_buy"]) is False
        assert bool(after_row["manual_pause_buy"]) is True
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_manual_risk_file_override_does_not_pollute_default_config_fixed() -> None:
    original = _make_configs()
    copied = deepcopy(original)
    override = "config/manual_risk_flags_acceptance_sample.yaml"
    updated = apply_manual_risk_file_override(copied, override)
    assert updated["universe"]["manual_flags"]["logic_risk_flag_file"] == override
    assert original["universe"]["manual_flags"]["logic_risk_flag_file"] == "config/manual_risk_flags.yaml"


def test_acceptance_artifacts_generate_fixed() -> None:
    root = _temp_root()
    try:
        _write_support_files(root)
        relative_path = _write_manual_file(root, _base_payload())
        configs = apply_manual_risk_file_override(_make_configs(), relative_path)
        helper = ManualRiskAcceptanceHelper(configs, root)
        target_table = build_target_table(configs["portfolio"])
        manager = ManualRiskFlagManager(root / relative_path, root / "data" / "manual" / "thesis_flags.csv")
        result = manager.validate(target_table)
        paths = helper.write_acceptance_artifacts(result, target_table, relative_path, "2025-12-31")
        assert paths["report_markdown"].exists()
        assert paths["report_json"].exists()
        assert paths["checklist_markdown"].exists()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_validate_manual_flags_on_acceptance_sample_fixed() -> None:
    root = _temp_root()
    try:
        _write_support_files(root)
        relative_path = _write_manual_file(root, _base_payload())
        configs = apply_manual_risk_file_override(_make_configs(), relative_path)
        manager = ManualRiskFlagManager(root / relative_path, root / "data" / "manual" / "thesis_flags.csv")
        result = manager.validate(build_target_table(configs["portfolio"]))
        assert bool(result["valid"]) is True
        assert len(result["flags"]) == 3
    finally:
        shutil.rmtree(root, ignore_errors=True)
