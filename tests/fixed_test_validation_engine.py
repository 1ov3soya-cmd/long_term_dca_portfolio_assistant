from pathlib import Path
import shutil
import sys
import uuid

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.validation_engine import ValidationEngine
from src.utils.runtime_models import ExtendedBacktestResult, MarketDataBundle

TMP_ROOT = PROJECT_ROOT / ".pytest_tmp"
TMP_ROOT.mkdir(parents=True, exist_ok=True)


def _make_configs() -> dict:
    return {
        "app": {
            "runtime": {"log_level": "INFO"},
            "schedule": {
                "monthly_invest_day_rule": "first_trading_day",
                "weekly_risk_check_rule": "last_trading_day_of_week",
            },
        },
        "portfolio": {
            "asset_allocation": {"etf_total_weight": 0.8, "stock_total_weight": 0.2},
        },
        "backtest": {
            "backtest": {
                "start_date": "2024-01-01",
                "end_date": "2024-02-29",
                "monthly_budget": 10000.0,
            },
            "transaction_cost": {
                "etf": {"buy_commission": 0.0003, "slippage": 0.001},
                "stock": {"buy_commission": 0.0003, "slippage": 0.002, "sell_stamp_tax": 0.001},
            },
            "trading_rules": {"min_trade_lot": 100},
        },
    }


def _make_target_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"symbol": "510300", "asset_type": "etf", "target_weight": 0.30},
            {"symbol": "600519", "asset_type": "stock", "target_weight": 0.04},
        ]
    )


def _make_bundle() -> MarketDataBundle:
    etf_history = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-03", "2024-01-02", "2024-01-02"]),
            "symbol": ["510300", "510300", "510300"],
            "asset_type": ["etf", "etf", "etf"],
            "open": [10.2, None, 10.0],
            "high": [10.3, 10.2, 10.1],
            "low": [10.0, 9.9, 9.8],
            "close": [10.1, 10.0, 10.0],
            "volume": [1000, None, 1200],
            "amount": [10000, None, 12000],
        }
    )
    stock_history = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-02-01"]),
            "symbol": ["600519", "600519", "600519"],
            "asset_type": ["stock", "stock", "stock"],
            "open": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
            "close": [100.5, 101.5, 102.5],
            "volume": [500, 600, 700],
            "amount": [50000, 60000, 70000],
        }
    )
    diagnostics = pd.DataFrame(
        [
            {
                "symbol": "510300",
                "asset_type": "etf",
                "provider": "efinance",
                "source_api": "stock.get_quote_history",
                "adjustment_mode": "forward",
                "fallback_used": False,
                "cache_hit": True,
                "latest_update": "2026-03-31 12:00:00",
                "raw_columns": "日期,开盘,收盘",
                "standardized_columns": "date,open,close",
                "note": "",
            },
            {
                "symbol": "600519",
                "asset_type": "stock",
                "provider": "efinance",
                "source_api": "stock.get_quote_history",
                "adjustment_mode": "forward",
                "fallback_used": False,
                "cache_hit": False,
                "latest_update": "2026-03-31 12:00:00",
                "raw_columns": "日期,开盘,收盘",
                "standardized_columns": "date,open,close",
                "note": "",
            },
        ]
    )
    return MarketDataBundle(
        histories={"510300": etf_history, "600519": stock_history},
        diagnostics=diagnostics,
        calendar=[
            pd.Timestamp("2024-01-02"),
            pd.Timestamp("2024-01-03"),
            pd.Timestamp("2024-01-04"),
            pd.Timestamp("2024-01-05"),
            pd.Timestamp("2024-02-01"),
        ],
        metadata={
            "data_mode": "real",
            "provider": "efinance",
            "source_api": "stock.get_quote_history",
            "adjustment_mode": "forward",
            "latest_data_date": "2024-02-01",
            "data_updated_at": "2026-03-31 12:00:00",
        },
    )


def test_validate_data_outputs_structure_and_diagnostics_fixed() -> None:
    temp_root = TMP_ROOT / f"validation_{uuid.uuid4().hex}"
    temp_root.mkdir(parents=True, exist_ok=True)
    try:
        engine = ValidationEngine(_make_configs(), temp_root)
        result = engine.validate_data(
            data_bundle=_make_bundle(),
            target_table=_make_target_table(),
            start_date="2024-01-01",
            end_date="2024-02-29",
        )

        summary = result["summary"]
        assert result["paths"]["markdown"].exists()
        assert result["paths"]["csv"].exists()
        assert result["paths"]["json"].exists()
        assert {"symbol", "source_api", "duplicate_dates", "non_increasing_dates", "volume_missing_rows", "amount_missing_rows"}.issubset(summary.columns)

        etf_row = summary.loc[summary["symbol"] == "510300"].iloc[0]
        assert etf_row["duplicate_dates"] == 1
        assert bool(etf_row["non_increasing_dates"]) is True
        assert etf_row["price_missing_rows"] == 1
        assert etf_row["volume_missing_rows"] == 1
        assert etf_row["amount_missing_rows"] == 1
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_validate_backtest_checks_weight_deviation_and_no_auto_sell_fixed() -> None:
    temp_root = TMP_ROOT / f"validation_{uuid.uuid4().hex}"
    temp_root.mkdir(parents=True, exist_ok=True)
    try:
        engine = ValidationEngine(_make_configs(), temp_root)
        bundle = _make_bundle()
        target_table = _make_target_table()
        result = ExtendedBacktestResult(
            equity_curve=pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-01-02", "2024-01-05", "2024-02-01"]),
                    "portfolio_value": [10000.0, 10100.0, 10200.0],
                    "cumulative_contribution": [10000.0, 10000.0, 20000.0],
                    "unit_nav": [1.0, 1.01, 1.02],
                }
            ),
            trades=pd.DataFrame(columns=["date", "symbol", "asset_type", "status"]),
            monthly_records=pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-01-02", "2024-02-01"]),
                    "month": ["2024-01", "2024-02"],
                    "actual_trade_day": ["2024-01-02", "2024-02-01"],
                    "monthly_budget": [10000.0, 10000.0],
                    "invested_amount": [8000.0, 7600.0],
                }
            ),
            risk_records=pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-01-05", "2024-02-01", "2024-02-01"]),
                    "symbol": ["600519", "600519", "600519"],
                    "asset_type": ["stock", "stock", "stock"],
                    "status": ["YELLOW", "YELLOW", "YELLOW"],
                    "reasons": ["test", "test", "test"],
                    "check_type": ["weekly_risk_check", "monthly_invest_review", "weekly_risk_check"],
                }
            ),
            metrics={"final_unit_nav": 1.02},
            unfilled_orders=pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-02-01", "2024-02-01", "2024-01-02"]),
                    "symbol": ["600519", "510300", "600519"],
                    "asset_type": ["stock", "etf", "stock"],
                    "recommended_amount": [400.0, 300.0, 200.0],
                    "reason": ["paused_by_risk_rule", "below_min_trade_lot", "missing_market_data_on_trade_day"],
                }
            ),
            recommendation_records=pd.DataFrame(),
            portfolio_snapshots=pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-02-01", "2024-02-01"]),
                    "symbol": ["510300", "600519"],
                    "asset_type": ["etf", "stock"],
                    "current_weight": [0.30, 0.05],
                    "target_weight": [0.30, 0.04],
                    "weight_gap": [0.00, -0.01],
                    "market_value": [3000.0, 500.0],
                    "total_value": [10000.0, 10000.0],
                    "cash": [6500.0, 6500.0],
                }
            ),
            metadata={"actual_weekly_risk_days": ["2024-01-05"]},
        )

        output = engine.validate_backtest(result, bundle, target_table)
        assert output["paths"]["markdown"].exists()
        assert output["paths"]["csv"].exists()
        assert bool(output["monthly_check"]["matched"].all()) is True
        assert bool(output["weekly_check"]["matched"].all()) is True

        redline_row = output["redline_stats"].loc[output["redline_stats"]["symbol"] == "600519"].iloc[0]
        assert bool(redline_row["auto_add_violation"]) is False

        unfilled_categories = set(output["unfilled_summary"]["category"].tolist())
        assert {"红线暂停", "资金不足整手", "标的在当期不可用"}.issubset(unfilled_categories)

        weight_row = output["weight_deviation"].loc[output["weight_deviation"]["symbol"] == "600519"].iloc[0]
        assert bool(weight_row["stock_limit_exceeded"]) is True
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
