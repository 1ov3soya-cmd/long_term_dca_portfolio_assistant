from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.portfolio import PortfolioState
from src.risk_monitor import RiskMonitor
from src.utils.schemas import Holding


def test_risk_monitor_detects_etf_and_stock_redline() -> None:
    risk_cfg = {
        "risk": {"moving_average_window": 3},
        "etf": {
            "yellow_drawdown_from_high": 0.15,
            "red_drawdown_from_high": 0.25,
            "weakness_days": 2,
        },
        "stock": {
            "yellow_drawdown_from_cost": 0.12,
            "red_drawdown_from_cost": 0.20,
        },
        "portfolio": {"red_max_drawdown": 0.2},
    }
    histories = {
        "510300": pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=5, freq="B"),
                "close": [100, 105, 103, 85, 75],
            }
        ),
        "600519": pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=5, freq="B"),
                "close": [100, 98, 95, 85, 75],
            }
        ),
    }
    target_table = pd.DataFrame(
        [
            {"symbol": "510300", "asset_type": "etf"},
            {"symbol": "600519", "asset_type": "stock"},
        ]
    )
    portfolio = PortfolioState(holdings=[Holding(symbol="600519", asset_type="stock", quantity=100, avg_cost=100.0)])
    monitor = RiskMonitor(risk_cfg)

    result = monitor.evaluate_assets(histories, portfolio, target_table, "2024-01-05")
    assert result["510300"].status == "RED"
    assert result["600519"].status == "RED"
