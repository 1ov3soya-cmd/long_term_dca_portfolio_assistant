from pathlib import Path
import sys
import shutil
import tempfile

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest_engine import MVPBacktestEngine
from src.portfolio import build_target_table


def test_backtest_engine_runs_with_demo_like_data() -> None:
    temp_root = Path(tempfile.mkdtemp(dir=PROJECT_ROOT))
    try:
    configs = {
        "app": {"runtime": {"log_level": "INFO"}},
        "portfolio": {
            "portfolio": {"monthly_budget": 10000.0},
            "asset_allocation": {"etf_total_weight": 0.8, "stock_total_weight": 0.2},
            "etf_pool": [
                {"symbol": "510300", "name": "沪深300ETF", "target_weight": 0.3},
                {"symbol": "510500", "name": "中证500ETF", "target_weight": 0.2},
                {"symbol": "515180", "name": "红利ETF", "target_weight": 0.2},
                {"symbol": "518880", "name": "黄金ETF", "target_weight": 0.1},
            ],
            "stock_pool": [
                {"symbol": "600519", "name": "贵州茅台", "target_weight": 0.04},
                {"symbol": "000858", "name": "五粮液", "target_weight": 0.04},
                {"symbol": "600036", "name": "招商银行", "target_weight": 0.04},
                {"symbol": "000333", "name": "美的集团", "target_weight": 0.04},
                {"symbol": "601318", "name": "中国平安", "target_weight": 0.04},
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
            },
            "transaction_cost": {
                "etf": {"buy_commission": 0.0003, "slippage": 0.001},
                "stock": {"buy_commission": 0.0003, "slippage": 0.002},
            },
            "trading_rules": {"min_trade_lot": 100},
        },
        "universe": {
            "universe": {"benchmark_symbol": "510300"},
            "manual_flags": {"thesis_flag_file": "data/manual/thesis_flags.csv"},
        },
    }

    target_table = build_target_table(configs["portfolio"])
    dates = pd.bdate_range("2024-01-01", "2024-03-31")
    histories = {}
    for i, symbol in enumerate(target_table["symbol"].tolist()):
        base = 10 + i * 5
        histories[symbol] = pd.DataFrame(
            {
                "date": dates,
                "symbol": symbol,
                "asset_type": target_table.loc[target_table["symbol"] == symbol, "asset_type"].iloc[0],
                "close": [base + j * 0.02 for j in range(len(dates))],
            }
        )

        thesis_file = temp_root / "data" / "manual" / "thesis_flags.csv"
        thesis_file.parent.mkdir(parents=True, exist_ok=True)
        thesis_file.write_text("symbol,thesis_broken,reason,last_update\n", encoding="utf-8")
        configs["universe"]["manual_flags"]["thesis_flag_file"] = str(thesis_file.relative_to(temp_root))

        engine = MVPBacktestEngine(configs, temp_root)
        result = engine.run(histories, target_table)

        assert not result.equity_curve.empty
        assert "final_unit_nav" in result.metrics
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
