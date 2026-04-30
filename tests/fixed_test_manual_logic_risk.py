from pathlib import Path
import json
import shutil
import sys
import uuid

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest_engine import MVPBacktestEngine
from src.manual_risk_manager import ManualRiskFlag, ManualRiskFlagManager
from src.portfolio import PortfolioState, build_target_table
from src.risk_decision import RiskDecisionMerger
from src.signal_engine import SignalEngine
from src.utils.schemas import Holding, RiskSignal


TMP_ROOT = PROJECT_ROOT / ".pytest_tmp"
TMP_ROOT.mkdir(parents=True, exist_ok=True)


def _temp_root() -> Path:
    root = TMP_ROOT / f"manual_logic_{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_manual_files(root: Path, manual_payload: dict, thesis_text: str = "symbol,thesis_broken,reason,last_update\n") -> None:
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "data" / "manual").mkdir(parents=True, exist_ok=True)
    yaml_lines = ["manual_risk_flags:", "  symbols:"]
    for symbol, row in manual_payload["manual_risk_flags"]["symbols"].items():
        yaml_lines.append(f'    "{symbol}":')
        for key, value in row.items():
            if isinstance(value, bool):
                text_value = str(value).lower()
            else:
                text_value = json.dumps(value, ensure_ascii=False)
            yaml_lines.append(f"      {key}: {text_value}")
    (root / "config" / "manual_risk_flags.yaml").write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")
    (root / "config" / "manual_risk_flags.json").write_text(
        json.dumps(manual_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (root / "data" / "manual" / "thesis_flags.csv").write_text(thesis_text, encoding="utf-8")
    (root / "data" / "manual" / "holdings.csv").write_text(
        "symbol,asset_type,quantity,avg_cost,last_update\n",
        encoding="utf-8",
    )


def _make_configs() -> dict:
    return {
        "app": {
            "runtime": {"log_level": "INFO", "cache_format": "csv", "data_provider": "efinance", "max_retry": 1, "retry_sleep_seconds": 0.0},
            "schedule": {"monthly_invest_day_rule": "first_trading_day", "weekly_risk_check_rule": "last_trading_day_of_week"},
        },
        "portfolio": {
            "portfolio": {"monthly_budget": 10000.0},
            "asset_allocation": {"etf_total_weight": 0.8, "stock_total_weight": 0.2},
            "etf_pool": [{"symbol": "510300", "name": "ETF_A", "target_weight": 0.8}],
            "stock_pool": [{"symbol": "600519", "name": "STOCK_A", "target_weight": 0.2}],
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
                "start_date": "2024-01-01",
                "end_date": "2024-02-29",
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
    }


def test_manual_flag_effective_from_fixed() -> None:
    root = _temp_root()
    try:
        _write_manual_files(
            root,
            {
                "manual_risk_flags": {
                    "symbols": {
                        "600519": {
                            "asset_type": "stock",
                            "effective_from": "2025-01-01",
                            "manual_pause_buy": True,
                            "manual_force_review": False,
                            "thesis_broken": False,
                        }
                    }
                }
            },
        )
        manager = ManualRiskFlagManager(root / "config" / "manual_risk_flags.yaml", root / "data" / "manual" / "thesis_flags.csv")
        assert "600519" not in manager.load_active_flags("2024-12-31")
        assert "600519" in manager.load_active_flags("2025-01-01")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_risk_merger_priority_fixed() -> None:
    merger = RiskDecisionMerger(_make_configs()["risk"])
    price_signal = RiskSignal(symbol="600519", asset_type="stock", status="YELLOW", reasons=["价格 YELLOW"], pause_buy=True, manual_review=True)
    flag = ManualRiskFlag(symbol="600519", asset_type="stock", effective_from="2024-01-01", manual_pause_buy=True, manual_force_review=True, thesis_broken=True)
    merged = merger.merge(price_signal, flag)
    assert merged.final_reason_codes[0] == "thesis_broken"
    assert merged.final_priority_level == 1
    assert merged.final_pause_buy is True
    assert merged.final_force_review is True


def test_signal_engine_manual_pause_blocks_buy_fixed() -> None:
    root = _temp_root()
    try:
        _write_manual_files(
            root,
            {
                "manual_risk_flags": {
                    "symbols": {
                        "600519": {
                            "asset_type": "stock",
                            "effective_from": "2024-01-01",
                            "manual_pause_buy": True,
                            "manual_force_review": False,
                            "thesis_broken": False,
                            "note": "暂停新增",
                        }
                    }
                }
            },
        )
        configs = _make_configs()
        histories = {
            "510300": pd.DataFrame({"date": pd.bdate_range("2024-01-01", periods=5), "close": [10, 10.2, 10.1, 10.3, 10.4]}),
            "600519": pd.DataFrame({"date": pd.bdate_range("2024-01-01", periods=5), "close": [100, 101, 102, 103, 104]}),
        }
        target_table = build_target_table(configs["portfolio"])
        portfolio = PortfolioState(holdings=[Holding(symbol="600519", asset_type="stock", quantity=100, avg_cost=100.0)])
        engine = SignalEngine(configs, root)
        payload = engine.generate_monthly_recommendation("2024-01-05", histories, portfolio, target_table)
        suggestion = next(item for item in payload["recommendation"].suggestions if item.symbol == "600519")
        assert suggestion.pause_buy is True
        assert suggestion.manual_pause_buy is True
        assert suggestion.final_human_readable_action == "暂停新增，等待人工解除"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_backtest_manual_logic_pauses_new_buys_fixed() -> None:
    root = _temp_root()
    try:
        _write_manual_files(
            root,
            {
                "manual_risk_flags": {
                    "symbols": {
                        "510300": {
                            "asset_type": "etf",
                            "effective_from": "2024-01-01",
                            "manual_pause_buy": True,
                            "manual_force_review": False,
                            "thesis_broken": False,
                            "note": "ETF 暂停新增",
                        }
                    }
                }
            },
        )
        configs = _make_configs()
        target_table = build_target_table(configs["portfolio"])
        dates = pd.bdate_range("2024-01-01", "2024-02-29")
        histories = {
            "510300": pd.DataFrame({"date": dates, "close": [10 + i * 0.01 for i in range(len(dates))]}),
            "600519": pd.DataFrame({"date": dates, "close": [100 + i * 0.1 for i in range(len(dates))]}),
        }
        engine = MVPBacktestEngine(configs, root)
        result = engine.run(histories, target_table)
        paused_recommendations = result.recommendation_records.loc[result.recommendation_records["symbol"] == "510300"]
        assert not paused_recommendations.empty
        assert bool(paused_recommendations["pause_buy"].all()) is True
        assert bool((paused_recommendations["recommended_amount"] == 0).all()) is True
        if result.trades.empty:
            buy_trades = pd.DataFrame()
        else:
            buy_trades = result.trades.loc[(result.trades["symbol"] == "510300") & (result.trades["action"] == "BUY")]
        assert buy_trades.empty
        assert "SELL" not in set(result.trades.get("action", pd.Series(dtype=str)).tolist())
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_validate_manual_flags_detects_errors_fixed() -> None:
    root = _temp_root()
    try:
        _write_manual_files(
            root,
            {
                "manual_risk_flags": {
                    "symbols": {
                        "999999": {
                            "asset_type": "stock",
                            "effective_from": "bad-date",
                            "manual_pause_buy": "maybe",
                            "manual_force_review": False,
                            "thesis_broken": False,
                        }
                    }
                }
            },
        )
        manager = ManualRiskFlagManager(root / "config" / "manual_risk_flags.yaml", root / "data" / "manual" / "thesis_flags.csv")
        target_table = pd.DataFrame([{"symbol": "600519", "asset_type": "stock"}])
        result = manager.validate(target_table)
        messages = set(result["issues"]["message"].tolist())
        assert "symbol 不在当前资产池内" in messages
        assert "effective_from 日期格式非法" in messages
        assert "manual_pause_buy 不是合法布尔值" in messages
    finally:
        shutil.rmtree(root, ignore_errors=True)
