from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.allocator import DCAAllocator
from src.utils.schemas import RiskSignal


def test_allocator_respects_bucket_budget_and_pause_buy() -> None:
    allocator = DCAAllocator(
        {
            "asset_allocation": {
                "etf_total_weight": 0.8,
                "stock_total_weight": 0.2,
            }
        }
    )
    target_table = pd.DataFrame(
        [
            {"symbol": "510300", "asset_type": "etf", "target_weight": 0.3},
            {"symbol": "510500", "asset_type": "etf", "target_weight": 0.2},
            {"symbol": "600519", "asset_type": "stock", "target_weight": 0.04},
        ]
    )
    current_table = pd.DataFrame(
        [
            {"symbol": "510300", "asset_type": "etf", "current_weight": 0.1},
            {"symbol": "510500", "asset_type": "etf", "current_weight": 0.15},
            {"symbol": "600519", "asset_type": "stock", "current_weight": 0.01},
        ]
    )
    risk_map = {
        "510300": RiskSignal(symbol="510300", asset_type="etf", status="GREEN"),
        "510500": RiskSignal(symbol="510500", asset_type="etf", status="YELLOW", pause_buy=True, manual_review=True),
        "600519": RiskSignal(symbol="600519", asset_type="stock", status="GREEN"),
    }

    suggestions = allocator.allocate(target_table, current_table, risk_map, monthly_budget=10000.0)
    frame = pd.DataFrame([item.to_dict() for item in suggestions])

    assert round(frame.loc[frame["asset_type"] == "etf", "recommended_amount"].sum(), 2) == 8000.0
    assert round(frame.loc[frame["asset_type"] == "stock", "recommended_amount"].sum(), 2) == 2000.0
    assert frame.loc[frame["symbol"] == "510500", "recommended_amount"].iloc[0] == 0.0
